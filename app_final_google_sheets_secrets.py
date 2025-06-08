import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import datetime
import io

# Apply visual theme
st.markdown("""
<style>
    body {
        background-color: #0e1117;
        color: #ffffff;
    }
    h1, h2, h3, h4 {
        color: #61dafb;
    }
    .stApp {
        font-family: 'Segoe UI', sans-serif;
        padding: 1rem;
    }
    .stButton>button {
        background-color: #00b4d8;
        color: white;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }
    .stDownloadButton>button {
        background-color: #0077b6;
        color: white;
        border-radius: 8px;
        height: 3em;
    }
    .stSelectbox>div>div {
        background-color: #1a1a1a !important;
        color: white !important;
    }
    .css-1d391kg, .css-18ni7ap, .css-1v3fvcr {
        background-color: #1a1a1a;
    }
</style>
""", unsafe_allow_html=True)

# Google Sheets Auth
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_key("1DFQst-DQMplGeI6OxfpSM1K_48rDJpT48Yy8Ur79d8g").sheet1

# Session State Initialization
for key in ["logged_in", "username", "uploaded_files", "upload_history"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "files" in key or "history" in key else False if key == "logged_in" else ""

# Auth Functions
def get_users():
    try:
        return {row["username"]: row["password_hash"] for row in sheet.get_all_records()}
    except:
        return {}

def add_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    sheet.append_row([username, hashed])

def delete_user(username):
    data = sheet.get_all_records()
    sheet.clear()
    sheet.append_row(["username", "password_hash"])
    for row in data:
        if row["username"] != username:
            sheet.append_row([row["username"], row["password_hash"]])

def reset_password(username, new_password):
    data = sheet.get_all_records()
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    sheet.clear()
    sheet.append_row(["username", "password_hash"])
    for row in data:
        sheet.append_row([username, hashed] if row["username"] == username else [row["username"], row["password_hash"]])

# Sidebar Admin Panel
if st.session_state.logged_in:
    st.sidebar.success(f"Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.username == "admin":
        st.sidebar.title("⚙️ Admin Panel")
        users = get_users()

        st.sidebar.markdown("### 🔐 Reset Password")
        user_to_reset = st.sidebar.selectbox("Select user", list(users.keys()))
        new_pw = st.sidebar.text_input("New Password", type="password")
        if st.sidebar.button("Reset"):
            reset_password(user_to_reset, new_pw)
            st.sidebar.success(f"{user_to_reset}'s password reset.")

        st.sidebar.markdown("### 🗑️ Delete User")
        user_to_delete = st.sidebar.selectbox("Delete user", [u for u in users if u != "admin"])
        if st.sidebar.button("Delete"):
            delete_user(user_to_delete)
            st.sidebar.success(f"{user_to_delete} deleted.")

        st.sidebar.markdown("### 📋 Upload History")
        if st.session_state.upload_history:
            history_df = pd.DataFrame(st.session_state.upload_history, columns=["Username", "File", "Time"])
            st.sidebar.dataframe(history_df)

# Login/Signup
if not st.session_state.logged_in:
    st.title("🔐 Secure Data Analyzer")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            users = get_users()
            if username in users and bcrypt.checkpw(password.encode(), users[username].encode()):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials.")

    with signup_tab:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Register"):
            users = get_users()
            if new_user in users:
                st.warning("Username exists.")
            elif not new_user or not new_pass:
                st.warning("Please fill both fields.")
            else:
                add_user(new_user, new_pass)
                st.success("Account created. Please log in.")
                st.rerun()

# Main CSV App
if st.session_state.logged_in:
    st.title("📊 Upload & Analyze CSV")
    uploaded_file = st.file_uploader("Upload your CSV file", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.uploaded_files.append((uploaded_file.name, df))
        st.session_state.upload_history.append((st.session_state.username, uploaded_file.name, timestamp))

        st.markdown(f"### Preview of `{uploaded_file.name}`")
        st.dataframe(df)

        st.subheader("🔍 Filter / Search Table")
        filter_col = st.selectbox("Column to filter", df.columns)
        if df[filter_col].dtype == "object":
            keyword = st.text_input("Search keyword")
            if keyword:
                df = df[df[filter_col].str.contains(keyword, case=False, na=False)]
        else:
            min_val = float(df[filter_col].min())
            max_val = float(df[filter_col].max())
            range_val = st.slider("Select range", min_val, max_val, (min_val, max_val))
            df = df[df[filter_col].between(*range_val)]

        st.dataframe(df)

        st.subheader("📈 Create a Chart")
        chart_type = st.selectbox("Choose chart", ["Scatter", "Line", "Histogram", "Box", "Heatmap", "Pie"])
        num_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        fig, ax = plt.subplots()

        if chart_type == "Scatter" and len(num_cols) >= 2:
            x = st.selectbox("X-axis", num_cols)
            y = st.selectbox("Y-axis", num_cols, index=1)
            sns.scatterplot(data=df, x=x, y=y, ax=ax)
        elif chart_type == "Line" and len(num_cols) >= 2:
            x = st.selectbox("X-axis", num_cols)
            y = st.selectbox("Y-axis", num_cols, index=1)
            sns.lineplot(data=df, x=x, y=y, ax=ax)
        elif chart_type == "Histogram" and num_cols:
            col = st.selectbox("Column", num_cols)
            sns.histplot(df[col], kde=True, ax=ax)
        elif chart_type == "Box" and num_cols:
            col = st.selectbox("Column", num_cols)
            sns.boxplot(y=df[col], ax=ax)
        elif chart_type == "Heatmap" and len(num_cols) >= 2:
            sns.heatmap(df[num_cols].corr(), annot=True, cmap="coolwarm", ax=ax)
        elif chart_type == "Pie" and cat_cols:
            col = st.selectbox("Category column", cat_cols)
            pie_data = df[col].value_counts()
            plt.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%")
            plt.axis("equal")

        st.pyplot(fig)

        def fig_to_png(fig):
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            return buf

        st.download_button("📥 Download Plot as PNG", data=fig_to_png(fig),
                           file_name="plot.png", mime="image/png")

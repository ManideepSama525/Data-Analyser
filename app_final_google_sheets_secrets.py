import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import datetime
import io

# Apply custom visual theme
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


# Google Sheets auth
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_key("1DFQst-DQMplGeI6OxfpSM1K_48rDJpT48Yy8Ur79d8g").sheet1

# Session defaults
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []
if "upload_history" not in st.session_state:
    st.session_state.upload_history = []

# Auth functions
def get_users():
    try:
        data = sheet.get_all_records()
        return {row["username"]: row["password_hash"] for row in data}
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
        if row["username"] == username:
            sheet.append_row([username, hashed])
        else:
            sheet.append_row([row["username"], row["password_hash"]])

def admin_controls():
    st.subheader("🖻 Admin Panel")
    users = get_users()
    st.dataframe(pd.DataFrame(users.items(), columns=["Username", "Hashed Password"]))

    st.markdown("### 🔐 Reset Password")
    user_to_reset = st.selectbox("Reset user", list(users.keys()), key="reset_user")
    new_pw = st.text_input("New password", type="password")
    if st.button("Reset Password"):
        reset_password(user_to_reset, new_pw)
        st.success(f"Password for {user_to_reset} reset.")

    st.markdown("### 🗑️ Delete User")
    user_to_delete = st.selectbox("Delete user", [u for u in users.keys() if u != "admin"], key="delete_user")
    if st.button("Delete User"):
        delete_user(user_to_delete)
        st.success(f"User {user_to_delete} deleted.")

    st.markdown("### 📋 Upload History by User")
    if st.session_state.upload_history:
        st.dataframe(pd.DataFrame(st.session_state.upload_history, columns=["Username", "Filename", "Timestamp"]))

# Login & signup UI
st.title("🔐 Secure Data Analyzer")
tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

with tab_login:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        users = get_users()
        if username in users and bcrypt.checkpw(password.encode(), users[username].encode()):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password.")

with tab_signup:
    new_user = st.text_input("New Username")
    new_pass = st.text_input("New Password", type="password")
    if st.button("Sign Up"):
        users = get_users()
        if new_user in users:
            st.warning("Username already exists.")
        elif not new_user.strip() or not new_pass.strip():
            st.warning("Fields cannot be empty.")
        else:
            add_user(new_user, new_pass)
            st.success("Account created. Please log in.")
            st.rerun()

# Main app
if st.session_state.logged_in:
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.username == "admin":
        admin_controls()

    st.title("📊 Upload & Analyze CSV")
    uploaded_file = st.file_uploader("Upload CSV File", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.session_state.uploaded_files.append((uploaded_file.name, df))
        st.session_state.upload_history.append((st.session_state.username, uploaded_file.name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        st.markdown(f"### Uploaded: `{uploaded_file.name}`")
        st.dataframe(df)

        st.subheader("🔎 Filter Data")
        filter_col = st.selectbox("Column to filter", df.columns)
        if df[filter_col].dtype == "object":
            search_text = st.text_input("Contains text:")
            if search_text:
                df = df[df[filter_col].str.contains(search_text, case=False, na=False)]
        else:
            min_val = float(df[filter_col].min())
            max_val = float(df[filter_col].max())
            selected = st.slider("Select range", min_val, max_val, (min_val, max_val))
            df = df[df[filter_col].between(*selected)]
        st.dataframe(df)

        st.subheader("📈 Visualization")
        chart = st.selectbox("Choose chart type", ["Scatter", "Line", "Histogram", "Box", "Heatmap", "Pie"])
        num_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()

        fig, ax = plt.subplots()
        if chart == "Scatter" and len(num_cols) >= 2:
            x = st.selectbox("X-axis", num_cols)
            y = st.selectbox("Y-axis", num_cols, index=1)
            sns.scatterplot(data=df, x=x, y=y, ax=ax)
        elif chart == "Line" and len(num_cols) >= 2:
            x = st.selectbox("X-axis", num_cols)
            y = st.selectbox("Y-axis", num_cols, index=1)
            sns.lineplot(data=df, x=x, y=y, ax=ax)
        elif chart == "Histogram" and num_cols:
            col = st.selectbox("Column", num_cols)
            sns.histplot(df[col], ax=ax)
        elif chart == "Box" and num_cols:
            col = st.selectbox("Column", num_cols)
            sns.boxplot(y=df[col], ax=ax)
        elif chart == "Heatmap" and len(num_cols) >= 2:
            sns.heatmap(df[num_cols].corr(), annot=True, ax=ax, cmap="coolwarm")
        elif chart == "Pie" and cat_cols:
            col = st.selectbox("Column", cat_cols)
            pie_data = df[col].value_counts()
            plt.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%")
            plt.axis("equal")

        st.pyplot(fig)

        def fig_to_png_bytes(fig):
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            return buf

        st.download_button("📥 Download Plot as PNG", data=fig_to_png_bytes(fig), file_name="plot.png", mime="image/png")

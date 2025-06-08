import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import bcrypt

# -------------------------------
# Theme Toggle (Dark/Light)
# -------------------------------
if "theme" not in st.session_state:
    st.session_state.theme = "Light"
theme = st.sidebar.radio("🌓 Theme", ["Light", "Dark"], index=0 if st.session_state.theme == "Light" else 1)
st.session_state.theme = theme
if theme == "Dark":
    st.markdown("<style>body { background-color: #0e1117; color: white; }</style>", unsafe_allow_html=True)

# -------------------------------
# Google Sheets Auth
# -------------------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_key("1DFQst-DQMplGeI6OxfpSM1K_48rDJpT48Yy8Ur79d8g").sheet1

# -------------------------------
# Session Initialization
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}

# -------------------------------
# Auth Helpers
# -------------------------------
def get_users():
    return {row['username']: row['password_hash'] for row in sheet.get_all_records()}

def verify_user(username, password):
    users = get_users()
    if username in users:
        return bcrypt.checkpw(password.encode(), users[username].encode())
    return False

def add_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    sheet.append_row([username, hashed])

# -------------------------------
# Login / Signup
# -------------------------------
if not st.session_state.logged_in:
    st.title("🔐 Login to Data Analyzer")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if verify_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Welcome, {username}!")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")

    with signup_tab:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Sign Up"):
            users = get_users()
            if new_user in users:
                st.warning("Username already exists.")
            elif new_user.strip() == "" or new_pass.strip() == "":
                st.warning("Fields cannot be empty.")
            else:
                add_user(new_user, new_pass)
                st.success("Account created. Please log in.")

else:
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()

    st.title("📊 Data Analyzer")

    # -------------------------------
    # CSV Upload
    # -------------------------------
    uploaded_file = st.file_uploader("Upload CSV File", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.session_state.uploaded_files[uploaded_file.name] = df

    if st.session_state.uploaded_files:
        file_list = list(st.session_state.uploaded_files.keys())
        selected_file = st.selectbox("Choose file to work with:", file_list)
        df = st.session_state.uploaded_files[selected_file]

        # -------------------------------
        # Filter Data
        # -------------------------------
        st.subheader("🔎 Search & Filter")
        filter_column = st.selectbox("Select column to filter", df.columns)
        if df[filter_column].dtype == "object":
            search_text = st.text_input("Search for text:")
            if search_text:
                df = df[df[filter_column].str.contains(search_text, case=False, na=False)]
        else:
            min_val = float(df[filter_column].min())
            max_val = float(df[filter_column].max())
            range_vals = st.slider("Select range", min_val, max_val, (min_val, max_val))
            df = df[(df[filter_column] >= range_vals[0]) & (df[filter_column] <= range_vals[1])]

        st.write("📋 Filtered Data:")
        st.dataframe(df, use_container_width=True)

        # -------------------------------
        # Summary
        # -------------------------------
        with st.expander("📈 Summary Statistics"):
            st.write(df.describe())
        with st.expander("📃 Column Info"):
            st.write(df.dtypes)

        # -------------------------------
        # Download
        # -------------------------------
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Filtered CSV", csv, "filtered_data.csv", "text/csv")

        # -------------------------------
        # Upload History
        # -------------------------------
        st.subheader("📁 Uploaded Files")
        for name in file_list:
            with st.expander(f"{name}"):
                st.write(st.session_state.uploaded_files[name])
                st.download_button(
                    label=f"Download {name}",
                    data=st.session_state.uploaded_files[name].to_csv(index=False).encode("utf-8"),
                    file_name=name,
                    mime="text/csv",
                    key=f"download_{name}"
                )

        # -------------------------------
        # Visualization
        # -------------------------------
        st.subheader("📊 Visualization")
        plot_type = st.selectbox("Select plot type", ["Scatter", "Line", "Histogram", "Box", "Heatmap", "Pie Chart"])
        num_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object']).columns.tolist()

        fig, ax = plt.subplots(figsize=(8, 5))

        if plot_type == "Scatter" and len(num_cols) >= 2:
            x = st.selectbox("X-axis", num_cols)
            y = st.selectbox("Y-axis", num_cols, index=1 if len(num_cols) > 1 else 0)
            sns.scatterplot(data=df, x=x, y=y, ax=ax)
        elif plot_type == "Line" and len(num_cols) >= 2:
            x = st.selectbox("X-axis", num_cols)
            y = st.selectbox("Y-axis", num_cols, index=1 if len(num_cols) > 1 else 0)
            sns.lineplot(data=df, x=x, y=y, ax=ax)
        elif plot_type == "Histogram" and num_cols:
            col = st.selectbox("Select numeric column", num_cols)
            sns.histplot(df[col], bins=30, kde=True, ax=ax)
        elif plot_type == "Box" and num_cols:
            col = st.selectbox("Select numeric column", num_cols)
            sns.boxplot(y=df[col], ax=ax)
        elif plot_type == "Heatmap" and len(num_cols) >= 2:
            sns.heatmap(df[num_cols].corr(), annot=True, cmap="coolwarm", ax=ax)
        elif plot_type == "Pie Chart" and cat_cols:
            col = st.selectbox("Select categorical column", cat_cols)
            pie_data = df[col].value_counts()
            plt.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%", startangle=140)
            plt.axis("equal")

        st.pyplot(fig)

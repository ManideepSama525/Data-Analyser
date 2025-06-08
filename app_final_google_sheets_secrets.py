import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import bcrypt
import gspread
import io
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image

# -------------------------
# Google Sheets Auth Setup
# -------------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_key("1DFQst-DQMplGeI6OxfpSM1K_48rDJpT48Yy8Ur79d8g").sheet1

# -------------------------
# Session State Init
# -------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "upload_history" not in st.session_state:
    st.session_state.upload_history = []
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

# -------------------------
# Theme Toggle
# -------------------------
with st.sidebar:
    st.radio("\U0001F315 Theme", ["Light", "Dark"], key="theme")

# -------------------------
# Auth Functions
# -------------------------
def get_users():
    data = sheet.get_all_records()
    return {row['username']: row['password_hash'] for row in data}

def add_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    sheet.append_row([username, hashed])

def delete_user(username):
    all_data = sheet.get_all_values()
    for i, row in enumerate(all_data):
        if row[0] == username:
            sheet.delete_row(i + 1)
            break

def reset_password(username, new_password):
    all_data = sheet.get_all_values()
    for i, row in enumerate(all_data):
        if row[0] == username:
            hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            sheet.update_cell(i + 1, 2, hashed)
            break

def validate_login(username, password):
    users = get_users()
    if username in users:
        return bcrypt.checkpw(password.encode(), users[username].encode())
    return False

# -------------------------
# Login Form
# -------------------------
def login():
    tab1, tab2 = st.tabs(["\U0001F512 Login", "\U0001F4BE Sign Up"])
    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if validate_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Sign Up"):
            add_user(new_username, new_password)
            st.success("User created. Please login.")

# -------------------------
# CSV Analyzer
# -------------------------
def csv_analyzer():
    st.title("\U0001F4C8 Data Analyzer")

    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)

        st.session_state.upload_history.append({
            "filename": uploaded_file.name,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "uploaded_by": st.session_state.username
        })

        st.subheader("CSV Data")
        filter_text = st.text_input("Search in table")
        if filter_text:
            filtered_df = df[df.apply(lambda row: row.astype(str).str.contains(filter_text, case=False).any(), axis=1)]
        else:
            filtered_df = df
        st.dataframe(filtered_df, use_container_width=True)

        st.subheader("Summary")
        st.write(df.describe())

        st.subheader("Plot Data")
        columns = df.select_dtypes(include='number').columns.tolist()
        if len(columns) >= 1:
            chart_type = st.selectbox("Chart type", ["Histogram", "Line", "Scatter"])
            x = st.selectbox("X-axis", columns)
            y = st.selectbox("Y-axis", columns)

            fig, ax = plt.subplots()
            if chart_type == "Histogram":
                sns.histplot(df[x], ax=ax)
            elif chart_type == "Line":
                sns.lineplot(x=df[x], y=df[y], ax=ax)
            elif chart_type == "Scatter":
                sns.scatterplot(x=df[x], y=df[y], ax=ax)

            st.pyplot(fig)

            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            st.download_button("Download Plot", buf.getvalue(), file_name="plot.png")

    if st.session_state.upload_history:
        st.sidebar.subheader("Upload History")
        history_df = pd.DataFrame(st.session_state.upload_history)
        st.sidebar.dataframe(history_df, height=200)

# -------------------------
# Admin Control Panel
# -------------------------
def admin_controls():
    st.subheader("\U0001F4BB Admin Panel")
    users = get_users()
    df_users = pd.DataFrame(users.items(), columns=["Username", "Hashed Password"])
    st.dataframe(df_users)

    st.markdown("### Delete User")
    user_to_delete = st.selectbox("Select user to delete", list(users.keys()))
    if st.button("Delete User"):
        if user_to_delete != "admin":
            delete_user(user_to_delete)
            st.success(f"Deleted user: {user_to_delete}")
            st.rerun()
        else:
            st.warning("Cannot delete admin user")

    st.markdown("### Reset User Password")
    user_to_reset = st.selectbox("Select user to reset password", list(users.keys()), key="reset")
    new_pass = st.text_input("Enter new password", key="new_pass")
    if st.button("Reset Password"):
        if user_to_reset:
            reset_password(user_to_reset, new_pass)
            st.success(f"Password reset for {user_to_reset}")

    if st.session_state.upload_history:
        st.markdown("### Uploads By User")
        history_df = pd.DataFrame(st.session_state.upload_history)
        st.dataframe(history_df)

# -------------------------
# App Entry Point
# -------------------------
if not st.session_state.logged_in:
    login()
else:
    if st.session_state.username == "admin":
        admin_controls()
    csv_analyzer()

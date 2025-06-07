import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt
import pandas as pd

# -------------------------------
# Google Sheets Setup
# -------------------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "streamlit-user-auth-bafb09360eed.json"  # Make sure this file is in the same directory
SHEET_NAME = "user_database"

# Authorize and connect to the sheet
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# -------------------------------
# Helper Functions
# -------------------------------
def get_users():
    try:
        data = sheet.get_all_records()
        return {row['username']: row['password_hash'] for row in data}
    except:
        return {}

def add_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    sheet.append_row([username, hashed])

def verify_user(username, password):
    users = get_users()
    if username in users:
        return bcrypt.checkpw(password.encode(), users[username].encode())
    return False

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="Google Sheets Login", layout="centered")
st.title("🔐 Google Sheets Login System")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔓 Login", "🆕 Sign Up"])

    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if verify_user(username, password):
                st.success(f"Welcome, {username}!")
                st.session_state.logged_in = True
                st.session_state.username = username
            else:
                st.error("Invalid credentials.")

    with tab2:
        new_user = st.text_input("New Username", key="signup_user")
        new_pass = st.text_input("New Password", type="password", key="signup_pass")
        if st.button("Create Account"):
            users = get_users()
            if new_user in users:
                st.warning("Username already exists.")
            elif new_user.strip() == "" or new_pass.strip() == "":
                st.warning("Fields cannot be empty.")
            else:
                add_user(new_user, new_pass)
                st.success("Account created! Please log in.")

else:
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()

    st.header("🎉 Welcome to the Protected Area!")
    st.write("You can now add your CSV upload and analysis features here.")

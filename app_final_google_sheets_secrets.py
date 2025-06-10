# Streamlit App with Google Sheets Auth, Hugging Face Summarizer, CSV Upload, and PPT Export

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import tempfile
import os
import requests
from io import BytesIO
from pptx import Presentation
from pptx.util import Inches
import gspread
from google.oauth2.service_account import Credentials
import bcrypt
import datetime

# --- Page Config ---
st.set_page_config(page_title="Data Analyzer", layout="wide", initial_sidebar_state="expanded")

# --- Theme Switcher ---
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
mode = st.sidebar.radio("Theme Mode", ["dark", "light"], index=0 if st.session_state.theme == "dark" else 1)
if mode != st.session_state.theme:
    st.session_state.theme = mode
    st.rerun()

st.markdown(
    f"""
    <style>
    html, body, [class*="css"]  {{
        background-color: {'#0e1117' if st.session_state.theme == 'dark' else 'white'};
        color: {'white' if st.session_state.theme == 'dark' else 'black'};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_sheets"], scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open("user_database")

try:
    auth_sheet = spreadsheet.worksheet("users")
except gspread.exceptions.WorksheetNotFound:
    auth_sheet = spreadsheet.add_worksheet(title="users", rows=100, cols=2)
    auth_sheet.append_row(["username", "password"])

# --- Auth Functions ---
@st.cache_data
def get_users():
    return auth_sheet.get_all_records()

def find_user(username):
    users = get_users()
    for user in users:
        if user['username'] == username:
            return user
    return None

def authenticate(username, password):
    user = find_user(username)
    if user and bcrypt.checkpw(password.encode(), user['password'].encode()):
        return True
    return False

# --- Auth UI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()

# --- Main App ---
st.sidebar.success(f"Logged in as: {st.session_state.username}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.experimental_rerun()

st.title("📊 Data Analyzer")

uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        df = pd.read_csv(uploaded_file)
        st.header(f"Dataset: {uploaded_file.name}")
        st.dataframe(df)

        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) >= 2:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Scatter Plot")
                fig, ax = plt.subplots()
                sns.scatterplot(data=df, x=numeric_cols[0], y=numeric_cols[1], ax=ax)
                st.pyplot(fig)

            with col2:
                st.subheader("Line Plot")
                fig2 = px.line(df[numeric_cols])
                st.plotly_chart(fig2)

        st.subheader("📄 AI Text Summary")
        try:
            hf_token = st.secrets["streamlit-summarizer"]["token"]
            api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
            headers = {"Authorization": f"Bearer {hf_token}"}

            text_input = st.text_area("Enter text to summarize")
            if st.button(f"Summarize {uploaded_file.name}") and text_input:
                with st.spinner("Summarizing..."):
                    response = requests.post(api_url, headers=headers, json={"inputs": text_input})
                    summary = response.json()[0]['summary_text']
                    st.success("Summary:")
                    st.write(summary)
        except Exception as e:
            st.error("Hugging Face token not found in secrets. Please add it to .streamlit/secrets.toml with section [streamlit-summarizer]")

        st.subheader("📤 Export to PPT")
        if st.button(f"Export {uploaded_file.name} to PPT"):
            try:
                ppt = Presentation()
                slide_layout = ppt.slide_layouts[5]
                slide = ppt.slides.add_slide(slide_layout)
                title = slide.shapes.title
                title.text = f"Dataset Overview: {uploaded_file.name}"

                if len(numeric_cols) > 0:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                        fig, ax = plt.subplots()
                        sns.histplot(df[numeric_cols[0]], ax=ax)
                        fig.savefig(tmpfile.name)
                        slide.shapes.add_picture(tmpfile.name, Inches(1), Inches(1.5), height=Inches(4))
                        os.unlink(tmpfile.name)

                ppt_bytes = BytesIO()
                ppt.save(ppt_bytes)
                ppt_bytes.seek(0)
                st.download_button("Download PPT", ppt_bytes, file_name="presentation.pptx")

            except Exception as e:
                st.error(f"Failed to export PPT: {e}")

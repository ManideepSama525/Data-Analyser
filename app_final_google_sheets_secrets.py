import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches
import io
import datetime
import requests

# ------------------------------ #
# 🎨 Visual Theme (unchanged)
# ------------------------------ #
st.markdown("""...""", unsafe_allow_html=True)  # (Your existing CSS)

# ------------------------------ #
# 🔐 Google Sheets Auth (unchanged)
# ------------------------------ #
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_sheets"], SCOPE)
    client = gspread.authorize(creds)
    workbook = client.open_by_key("1DFQst-DQMplGeI6OxfpSM1K_48rDJpT48Yy8Ur79d8g")
    user_sheet = workbook.sheet1
    try:
        upload_sheet = workbook.worksheet("upload_history")
    except:
        upload_sheet = workbook.add_worksheet(title="upload_history", rows="1000", cols="3")
        upload_sheet.append_row(["username", "filename", "timestamp"])
except Exception as e:
    st.error(f"Failed to connect to Google Sheets: {e}")
    st.stop()

# ------------------------------ #
# 🔄 Session State Initialization (unchanged)
# ------------------------------ #
def initialize_session_state():
    for key, val in {"logged_in": False, "username": "", "uploaded_data": {}}.items():
        if key not in st.session_state:
            st.session_state[key] = val

initialize_session_state()

# ------------------------------ #
# 🔧 Utility Functions (simplified versions)
# ------------------------------ #
def get_users():
    try:
        return {r["username"]: r["password_hash"] for r in user_sheet.get_all_records()}
    except Exception:
        return {}

def add_user(u, p): ...
def delete_user(u): ...
def reset_password(u, p): ...
def log_upload(u, fn, ct): ...
def fetch_upload_history(): ...
def fig_to_bytes(fig): ...
def generate_ppt(df, chart_images): ...
def clear_session(): ...

# ------------------------------ #
# 🧠 New: AI Summary via Hugging Face
# ------------------------------ #
def generate_summary(text, max_length=130):
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
            headers={"Authorization": f"Bearer {st.secrets['hf']['token']}"},
            json={
                "inputs": text,
                "parameters": {"max_length": max_length, "min_length": 30, "do_sample": False}
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()[0]["summary_text"]
    except Exception as e:
        return f"AI summary failed: {e}"

# ------------------------------ #
# 👤 Login / Register Block (same)
# ------------------------------ #
if not st.session_state.logged_in:
    st.title("🔐 Secure Data Analyzer")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
    # same login and signup logic...
    st.stop()

# ------------------------------ #
# 🛠 Admin Panel (same with download & session clear)
# ------------------------------ #
if st.session_state.logged_in:
    st.sidebar.title("⚙️ Admin Panel")
    st.sidebar.write(f"Logged in as: `{st.session_state.username}`")
    if st.sidebar.button("Logout"):
        clear_session()
        st.rerun()
    if st.session_state.username == "admin":
        # admin features unchanged...

# ------------------------------ #
# 📊 Main CSV Interface (enhanced)
# ------------------------------ #
if st.session_state.logged_in:
    st.title("📊 Upload & Analyze CSV")
    uploaded = st.file_uploader("Upload CSV", type="csv")
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            log_upload(st.session_state.username, uploaded.name, uploaded.getvalue())

            st.subheader("📄 Data Preview")
            st.dataframe(df)

            st.subheader("🔍 Filter Data")
            # same filtering logic...

            st.subheader("📈 Chart Builder")
            # same chart selection and plotting...
            st.pyplot(fig)
            img_bytes = fig_to_bytes(fig)
            st.download_button("📥 Download Plot as PNG", data=img_bytes, file_name="plot.png", mime="image/png")

            if st.button("📤 Download PPT Report"):
                pptx_buf = generate_ppt(df, chart_images)
                if pptx_buf:
                    st.download_button("📥 Download PowerPoint", data=pptx_buf, file_name="report.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

            # 🧠 New Summary Section
            st.subheader("🧠 Auto Summary Insights")
            text_for_summary = df.describe(include='all').to_string()
            with st.spinner("Generating AI summary..."):
                summary = generate_summary(text_for_summary)
            st.success("Summary generated!")
            st.write(summary)

        except Exception as e:
            st.error(f"Error processing CSV: {e}")

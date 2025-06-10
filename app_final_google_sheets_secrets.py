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
import os

# ------------------------------ #
# 🎨 Visual Theme
# ------------------------------ #
st.markdown("""
    <style>
    .css-1v0mbdj {padding: 2rem 1rem;}
    .stButton>button {color: white; background: #007bff;}
    </style>
""", unsafe_allow_html=True)

# ------------------------------ #
# 🔐 Google Sheets Auth
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
# 🔄 Session State Initialization
# ------------------------------ #
def initialize_session_state():
    for key, val in {"logged_in": False, "username": "", "uploaded_data": {}}.items():
        if key not in st.session_state:
            st.session_state[key] = val

initialize_session_state()

# ------------------------------ #
# 🔧 Utility Functions
# ------------------------------ #
def get_users():
    try:
        return {r["username"]: r["password_hash"] for r in user_sheet.get_all_records()}
    except Exception:
        return {}

def add_user(u, p):
    hashed = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    user_sheet.append_row([u, hashed])

def delete_user(u):
    records = user_sheet.get_all_records()
    user_sheet.clear()
    user_sheet.append_row(["username", "password_hash"])
    for r in records:
        if r["username"] != u:
            user_sheet.append_row([r["username"], r["password_hash"]])

def reset_password(u, p):
    records = user_sheet.get_all_records()
    user_sheet.clear()
    user_sheet.append_row(["username", "password_hash"])
    for r in records:
        if r["username"] == u:
            hashed = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
            user_sheet.append_row([u, hashed])
        else:
            user_sheet.append_row([r["username"], r["password_hash"]])

def log_upload(u, fn, ct):
    ts = datetime.datetime.now().isoformat()
    upload_sheet.append_row([u, fn, ts])
    if not os.path.exists("user_uploads"):
        os.makedirs("user_uploads")
    with open(f"user_uploads/{u}_{fn}", "wb") as f:
        f.write(ct)

def fetch_upload_history():
    return pd.DataFrame(upload_sheet.get_all_records())

def fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf.read()

def generate_ppt(df, chart_images):
    prs = Presentation()
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = "Data Analysis Report"
    title_slide.placeholders[1].text = f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d')}"

    desc_slide = prs.slides.add_slide(prs.slide_layouts[1])
    desc_slide.shapes.title.text = "Summary Statistics"
    desc_slide.placeholders[1].text = df.describe(include='all').to_string()

    for img in chart_images:
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = "Chart"
        slide.shapes.add_picture(io.BytesIO(img), Inches(1, 1.5), Inches(1), height=Inches(4.5))

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf

def clear_session():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.uploaded_data = {}

# ------------------------------ #
# 🧠 Hugging Face Summarization
# ------------------------------ #
def generate_summary(text, max_length=130):
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
            headers={"Authorization": f"Bearer {st.secrets['hf']['token']}"},
            json={"inputs": text, "parameters": {"max_length": max_length, "min_length": 30, "do_sample": False}},
            timeout=60
        )
        response.raise_for_status()
        return response.json()[0]["summary_text"]
    except Exception as e:
        return f"AI summary failed: {e}"

# ------------------------------ #
# 👤 Login / Sign Up
# ------------------------------ #
if not st.session_state.logged_in:
    st.title("🔐 Secure Data Analyzer")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        user = st.text_input("Username", key="login_user")
        passwd = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            users = get_users()
            if user in users and bcrypt.checkpw(passwd.encode(), users[user].encode()):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

    with signup_tab:
        new_user = st.text_input("New Username", key="new_user")
        new_pass = st.text_input("New Password", type="password", key="new_pass")
        if st.button("Sign Up"):
            users = get_users()
            if new_user in users:
                st.error("Username already exists.")
            else:
                add_user(new_user, new_pass)
                st.success("Account created! Please log in.")

    st.stop()

# ------------------------------ #
# 🛠 Admin Panel
# ------------------------------ #
if st.session_state.logged_in:
    st.sidebar.title("⚙️ Admin Panel")
    st.sidebar.write(f"Logged in as: `{st.session_state.username}`")
    if st.sidebar.button("Logout"):
        clear_session()
        st.rerun()

    if st.session_state.username == "admin":
        st.sidebar.subheader("👤 User Management")
        all_users = list(get_users().keys())
        target_user = st.sidebar.selectbox("Select user", [u for u in all_users if u != "admin"])
        new_password = st.sidebar.text_input("New Password", type="password")
        if st.sidebar.button("Reset Password"):
            reset_password(target_user, new_password)
            st.sidebar.success("Password reset")

        if st.sidebar.button("Delete User"):
            delete_user(target_user)
            st.sidebar.success("User deleted")

        st.sidebar.subheader("📁 Download Uploads")
        history = fetch_upload_history()
        for _, row in history.iterrows():
            file_path = f"user_uploads/{row['username']}_{row['filename']}"
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    st.sidebar.download_button(f"⬇️ {row['filename']} ({row['username']})", data=f, file_name=row['filename'])

# ------------------------------ #
# 📊 CSV Upload & Analysis
# ------------------------------ #
st.title("📊 Upload & Analyze CSV")
uploaded = st.file_uploader("Upload CSV", type="csv")
if uploaded:
    try:
        df = pd.read_csv(uploaded)
        log_upload(st.session_state.username, uploaded.name, uploaded.getvalue())

        st.subheader("📄 Data Preview")
        st.dataframe(df)

        st.subheader("🔍 Filter Data")
        search = st.text_input("Search").lower()
        if search:
            df = df[df.apply(lambda row: row.astype(str).str.lower().str.contains(search).any(), axis=1)]
            st.dataframe(df)

        st.subheader("📈 All Charts")
        chart_images = []
        numeric_cols = df.select_dtypes(include="number").columns
        text_cols = df.select_dtypes(include="object").columns

        if len(numeric_cols) >= 2:
            fig, ax = plt.subplots()
            sns.scatterplot(data=df, x=numeric_cols[0], y=numeric_cols[1], ax=ax)
            st.pyplot(fig)
            chart_images.append(fig_to_bytes(fig))

            fig, ax = plt.subplots()
            sns.lineplot(data=df, x=numeric_cols[0], y=numeric_cols[1], ax=ax)
            st.pyplot(fig)
            chart_images.append(fig_to_bytes(fig))

            fig, ax = plt.subplots()
            sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="coolwarm", ax=ax)
            st.pyplot(fig)
            chart_images.append(fig_to_bytes(fig))

        if len(numeric_cols) >= 1:
            fig, ax = plt.subplots()
            sns.histplot(df[numeric_cols[0]], kde=True, ax=ax)
            st.pyplot(fig)
            chart_images.append(fig_to_bytes(fig))

            fig, ax = plt.subplots()
            sns.boxplot(y=df[numeric_cols[0]], ax=ax)
            st.pyplot(fig)
            chart_images.append(fig_to_bytes(fig))

        if len(text_cols) >= 1:
            fig, ax = plt.subplots()
            df[text_cols[0]].value_counts().plot.pie(autopct='%1.1f%%', ax=ax)
            ax.set_ylabel("")
            st.pyplot(fig)
            chart_images.append(fig_to_bytes(fig))

        st.download_button("📥 Download Plot as PNG", data=chart_images[0], file_name="plot.png", mime="image/png")

        if st.button("📤 Download PPT Report"):
            pptx_buf = generate_ppt(df, chart_images)
            st.download_button("📥 Download PowerPoint", data=pptx_buf, file_name="report.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

        st.subheader("🧠 Auto Summary Insights")
        text_for_summary = df.describe(include='all').to_string()
        with st.spinner("Generating AI summary..."):
            summary = generate_summary(text_for_summary)
        st.success("Summary generated!")
        st.write(summary)

    except Exception as e:
        st.error(f"Error processing CSV: {e}")

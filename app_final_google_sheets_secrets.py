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
    defaults = {
        "logged_in": False,
        "username": "",
        "uploaded_data": {},
    }
    for key, val in defaults.items():
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
    delete_user(u)
    add_user(u, p)

def log_upload(u, fn, ct):
    upload_sheet.append_row([u, fn, str(datetime.datetime.now())])

def fetch_upload_history():
    return upload_sheet.get_all_records()

def fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf.read()

def generate_ppt(df, chart_images):
    ppt = Presentation()
    title_slide_layout = ppt.slide_layouts[0]
    slide = ppt.slides.add_slide(title_slide_layout)
    slide.shapes.title.text = "CSV Data Analysis Report"
    slide.placeholders[1].text = f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    for chart_name, img in chart_images.items():
        slide = ppt.slides.add_slide(ppt.slide_layouts[5])
        slide.shapes.title.text = chart_name
        image_stream = io.BytesIO(img)
        slide.shapes.add_picture(image_stream, Inches(1), Inches(1.5), width=Inches(8))

    ppt_buf = io.BytesIO()
    ppt.save(ppt_buf)
    ppt_buf.seek(0)
    return ppt_buf

def clear_session():
    st.session_state.clear()
    st.rerun()

# ------------------------------ #
# 🧠 AI Summary via Hugging Face
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
# 👤 Login / Register
# ------------------------------ #
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
                st.error("Invalid credentials")

    with signup_tab:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Sign Up"):
            if new_user and new_pass:
                users = get_users()
                if new_user in users:
                    st.error("Username already exists")
                else:
                    add_user(new_user, new_pass)
                    st.success("Account created. Please log in.")
            else:
                st.error("Enter all fields")

    st.stop()

# ------------------------------ #
# 🛠 Admin Panel
# ------------------------------ #
if st.session_state.logged_in:
    st.sidebar.title("⚙️ Admin Panel")
    st.sidebar.write(f"Logged in as: `{st.session_state.username}`")
    if st.sidebar.button("Logout"):
        clear_session()
    if st.session_state.username == "admin":
        st.sidebar.subheader("User Controls")
        if st.sidebar.button("Reset Test User Password"):
            reset_password("test", "test")
            st.sidebar.success("Reset test password")
        if st.sidebar.button("Delete Test User"):
            delete_user("test")
            st.sidebar.success("Test user deleted")

        st.sidebar.subheader("Uploaded Files")
        history = fetch_upload_history()
        df_hist = pd.DataFrame(history)
        st.sidebar.dataframe(df_hist)

# ------------------------------ #
# 📊 Main CSV Interface
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
            search_col = st.selectbox("Select column to search/filter", df.columns)
            search_term = st.text_input("Enter search keyword")
            if search_term:
                df = df[df[search_col].astype(str).str.contains(search_term, case=False)]
                st.dataframe(df)

            st.subheader("📈 Chart Builder")
            chart_types = ["Scatter", "Line", "Histogram", "Box", "Heatmap", "Pie"]
            selected_charts = st.multiselect("Select charts to view in app (all charts will be in PPT)", chart_types)

            chart_images = {}

            for chart in chart_types:
                fig = plt.figure()
                if chart == "Scatter" and df.select_dtypes(include='number').shape[1] >= 2:
                    cols = df.select_dtypes(include='number').columns[:2]
                    sns.scatterplot(data=df, x=cols[0], y=cols[1])
                elif chart == "Line" and df.select_dtypes(include='number').shape[1] >= 2:
                    cols = df.select_dtypes(include='number').columns[:2]
                    sns.lineplot(data=df, x=cols[0], y=cols[1])
                elif chart == "Histogram":
                    df.select_dtypes(include='number').hist()
                elif chart == "Box":
                    sns.boxplot(data=df.select_dtypes(include='number'))
                elif chart == "Heatmap":
                    sns.heatmap(df.corr(), annot=True, fmt=".2f")
                elif chart == "Pie":
                    col = df.select_dtypes(include='object').columns[0]
                    df[col].value_counts().plot.pie(autopct="%1.1f%%")

                if chart in selected_charts:
                    st.pyplot(fig)
                chart_images[chart] = fig_to_bytes(fig)

            st.download_button("📥 Download Plot Report (PPT)", data=generate_ppt(df, chart_images), file_name="report.pptx")

            st.subheader("🧠 AI Summary Insights")
            text_for_summary = df.describe(include='all').to_string()
            with st.spinner("Generating summary..."):
                summary = generate_summary(text_for_summary)
            st.success("Summary ready")
            st.write(summary)

        except Exception as e:
            st.error(f"Error processing CSV: {e}")

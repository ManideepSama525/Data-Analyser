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
import os
import datetime

# -----------------------------------
# 🎨 Custom Theme
# -----------------------------------
st.markdown("""
<style>
    body { background-color: #0e1117; color: #ffffff; }
    h1, h2, h3, h4 { color: #61dafb; }
    .stApp { font-family: 'Segoe UI', sans-serif; padding: 1rem; }
    .stButton>button, .stDownloadButton>button {
        background-color: #00b4d8; color: white; border-radius: 8px;
        height: 3em; font-weight: bold;
    }
    .stSelectbox>div>div { background-color: #1a1a1a !important; color: white !important; }
    .css-1d391kg, .css-18ni7ap, .css-1v3fvcr { background-color: #1a1a1a; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------
# 🔐 Google Sheets Auth
# -----------------------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)

# Sheets
workbook = client.open_by_key("1DFQst-DQMplGeI6OxfpSM1K_48rDJpT48Yy8Ur79d8g")
sheet = workbook.sheet1
try:
    upload_sheet = workbook.worksheet("upload_history")
except:
    upload_sheet = workbook.add_worksheet(title="upload_history", rows="1000", cols="3")
    upload_sheet.append_row(["username", "filename", "timestamp"])

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# -----------------------
# 🔐 Auth & Admin Helpers
# -----------------------
def get_users():
    return {row["username"]: row["password_hash"] for row in sheet.get_all_records()}

def add_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    sheet.append_row([username, hashed])

def delete_user(username):
    users = sheet.get_all_records()
    sheet.clear()
    sheet.append_row(["username", "password_hash"])
    for row in users:
        if row["username"] != username:
            sheet.append_row([row["username"], row["password_hash"]])

def reset_password(username, new_password):
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    users = sheet.get_all_records()
    sheet.clear()
    sheet.append_row(["username", "password_hash"])
    for row in users:
        if row["username"] == username:
            sheet.append_row([username, hashed])
        else:
            sheet.append_row([row["username"], row["password_hash"]])

def log_upload(username, filename, df):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    upload_sheet.append_row([username, filename, timestamp])
    os.makedirs("uploads", exist_ok=True)
    df.to_csv(f"uploads/{username}_{filename}", index=False)

def fetch_upload_history():
    return pd.DataFrame(upload_sheet.get_all_records())

def fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

def generate_ppt_from_df(df, chart_img, chart_type):
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[0]).shapes.title.text = "CSV Data Report"

    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Summary Statistics"
    textbox = slide.placeholders[1]
    textbox.text = df.describe(include='all').round(2).to_string()

    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Data Sample"
    table = slide.shapes.add_table(min(11, len(df)+1), len(df.columns), Inches(0.5), Inches(1.5), Inches(9), Inches(4)).table
    for i, col in enumerate(df.columns):
        table.cell(0, i).text = str(col)
    for r in range(min(10, len(df))):
        for c in range(len(df.columns)):
            table.cell(r+1, c).text = str(df.iloc[r, c])

    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = f"{chart_type} Chart"
    slide.shapes.add_picture(chart_img, Inches(1), Inches(1.5), Inches(6), Inches(4))

    ppt_io = io.BytesIO()
    prs.save(ppt_io)
    ppt_io.seek(0)
    return ppt_io

# --------------------------
# 👤 Login / Signup Interface
# --------------------------
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
                st.warning("Fill all fields.")
            else:
                add_user(new_user, new_pass)
                st.success("Account created. Please log in.")
                st.rerun()

# --------------------------
# ⚙️ Admin Panel Sidebar
# --------------------------
if st.session_state.logged_in:
    st.sidebar.success(f"Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.username == "admin":
        st.sidebar.title("⚙️ Admin Panel")
        users = get_users()

        st.sidebar.markdown("### 🔐 Reset Password")
        user_to_reset = st.sidebar.selectbox("Reset user", list(users.keys()))
        new_pw = st.sidebar.text_input("New Password", type="password")
        if st.sidebar.button("Reset Password"):
            reset_password(user_to_reset, new_pw)
            st.sidebar.success("Password reset.")

        st.sidebar.markdown("### 🗑️ Delete User")
        user_to_delete = st.sidebar.selectbox("Delete user", [u for u in users if u != "admin"])
        if st.sidebar.button("Delete User"):
            delete_user(user_to_delete)
            st.sidebar.success("User deleted.")

        st.sidebar.markdown("### 📋 Upload History")
        history = fetch_upload_history()
        st.sidebar.dataframe(history)

        st.sidebar.markdown("### ⬇️ Download Uploaded CSVs")
        for fname in os.listdir("uploads"):
            with open(f"uploads/{fname}", "rb") as f:
                st.sidebar.download_button(f"Download {fname}", f, file_name=fname)

# --------------------------
# 📊 CSV Upload & Analysis
# --------------------------
if st.session_state.logged_in:
    st.title("📊 Upload & Analyze CSV")
    uploaded_file = st.file_uploader("Upload your CSV", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        log_upload(st.session_state.username, uploaded_file.name, df)

        st.subheader(f"📄 Preview: `{uploaded_file.name}`")
        st.dataframe(df)

        st.subheader("🔍 Filter Data")
        filter_col = st.selectbox("Column to filter", df.columns)
        if df[filter_col].dtype == "object":
            keyword = st.text_input("Search keyword")
            if keyword:
                df = df[df[filter_col].str.contains(keyword, case=False, na=False)]
        else:
            min_val = float(df[filter_col].min())
            max_val = float(df[filter_col].max())
            selected = st.slider("Select range", min_val, max_val, (min_val, max_val))
            df = df[df[filter_col].between(*selected)]

        st.dataframe(df)

        st.subheader("📈 Chart")
        chart_type = st.selectbox("Chart type", ["Scatter", "Line", "Histogram", "Box", "Heatmap", "Pie"])
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

        chart_buf = fig_to_png(fig)
        st.download_button("📥 Download Plot as PNG", data=chart_buf, file_name="plot.png", mime="image/png")

        ppt_buf = generate_ppt_from_df(df, chart_buf, chart_type)
        st.download_button("📥 Download PPT Report", data=ppt_buf,
                           file_name="report.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

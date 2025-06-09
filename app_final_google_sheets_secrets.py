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
import os

# ------------------------------ #
# 🎨 Visual Theme
# ------------------------------ #
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

# ------------------------------ #
# 🔐 Google Sheets Auth
# ------------------------------ #
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
workbook = client.open_by_key("1DFQst-DQMplGeI6OxfpSM1K_48rDJpT48Yy8Ur79d8g")
user_sheet = workbook.sheet1

try:
    upload_sheet = workbook.worksheet("upload_history")
except:
    upload_sheet = workbook.add_worksheet(title="upload_history", rows="1000", cols="3")
    upload_sheet.append_row(["username", "filename", "timestamp"])

# ------------------------------ #
# 🔄 Session State
# ------------------------------ #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = {}

# ------------------------------ #
# 🔧 Utility Functions
# ------------------------------ #
def get_users():
    return {row["username"]: row["password_hash"] for row in user_sheet.get_all_records()}

def add_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_sheet.append_row([username, hashed])

def delete_user(username):
    data = user_sheet.get_all_records()
    user_sheet.clear()
    user_sheet.append_row(["username", "password_hash"])
    for row in data:
        if row["username"] != username:
            user_sheet.append_row([row["username"], row["password_hash"]])

def reset_password(username, new_password):
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    data = user_sheet.get_all_records()
    user_sheet.clear()
    user_sheet.append_row(["username", "password_hash"])
    for row in data:
        if row["username"] == username:
            user_sheet.append_row([username, hashed])
        else:
            user_sheet.append_row([row["username"], row["password_hash"]])

def log_upload(username, filename, content):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    upload_sheet.append_row([username, filename, timestamp])
    if username not in st.session_state.uploaded_data:
        st.session_state.uploaded_data[username] = {}
    st.session_state.uploaded_data[username][filename] = content

def fetch_upload_history():
    return pd.DataFrame(upload_sheet.get_all_records())

def fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

def generate_ppt(df, chart_images):
    ppt = Presentation()
    ppt.slides.add_slide(ppt.slide_layouts[0]).shapes.title.text = "CSV Report"

    slide = ppt.slides.add_slide(ppt.slide_layouts[1])
    slide.shapes.title.text = "Data Summary"
    textbox = slide.placeholders[1]
    textbox.text = df.describe(include='all').round(2).to_string()

    sample = df.head(10)
    slide = ppt.slides.add_slide(ppt.slide_layouts[5])
    slide.shapes.title.text = "Sample Data"
    rows, cols = sample.shape
    table = slide.shapes.add_table(rows + 1, cols, Inches(0.5), Inches(1.5), Inches(9), Inches(4)).table
    for i, col in enumerate(sample.columns):
        table.cell(0, i).text = col
    for r in range(rows):
        for c in range(cols):
            table.cell(r + 1, c).text = str(sample.iloc[r, c])

    for name, img_bytes in chart_images:
        slide = ppt.slides.add_slide(ppt.slide_layouts[5])
        slide.shapes.title.text = name
        slide.shapes.add_picture(img_bytes, Inches(1), Inches(1.5), Inches(6), Inches(4))

    buf = io.BytesIO()
    ppt.save(buf)
    buf.seek(0)
    return buf

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
                st.success("Account created!")
                st.rerun()

# ------------------------------ #
# 🛠 Admin Panel
# ------------------------------ #
if st.session_state.logged_in:
    st.sidebar.title("⚙️ Admin Panel")
    st.sidebar.write(f"Logged in as: `{st.session_state.username}`")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.username == "admin":
        users = get_users()

        st.sidebar.markdown("### 🔐 Reset Password")
        user = st.sidebar.selectbox("Select user", list(users.keys()))
        new_pw = st.sidebar.text_input("New password", type="password")
        if st.sidebar.button("Reset Password"):
            reset_password(user, new_pw)
            st.sidebar.success("Password reset.")

        st.sidebar.markdown("### 🗑️ Delete User")
        del_user = st.sidebar.selectbox("Delete user", [u for u in users if u != "admin"])
        if st.sidebar.button("Delete User"):
            delete_user(del_user)
            st.sidebar.success("User deleted.")

        st.sidebar.markdown("### 📋 Upload History")
        history_df = fetch_upload_history()
        st.sidebar.dataframe(history_df)

        st.sidebar.markdown("### 📦 Download Uploaded CSVs")
        for user in st.session_state.uploaded_data:
            for filename, content in st.session_state.uploaded_data[user].items():
                st.sidebar.download_button(f"{user}: {filename}", data=content, file_name=filename)

# ------------------------------ #
# 📊 Main CSV Interface
# ------------------------------ #
if st.session_state.logged_in:
    st.title("📊 Upload & Analyze CSV")
    uploaded = st.file_uploader("Upload CSV", type="csv")
    if uploaded:
        df = pd.read_csv(uploaded)
        log_upload(st.session_state.username, uploaded.name, uploaded.getvalue())

        st.subheader("📄 Data Preview")
        st.dataframe(df)

        st.subheader("🔍 Filter Data")
        filter_col = st.selectbox("Column to filter", df.columns)
        if df[filter_col].dtype == "object":
            keyword = st.text_input("Search text")
            if keyword:
                df = df[df[filter_col].str.contains(keyword, case=False, na=False)]
        else:
            range_vals = st.slider("Select range", float(df[filter_col].min()), float(df[filter_col].max()),
                                   (float(df[filter_col].min()), float(df[filter_col].max())))
            df = df[df[filter_col].between(*range_vals)]

        st.dataframe(df)

        st.subheader("📈 Chart Builder")
        chart_type = st.selectbox("Chart type", ["Scatter", "Line", "Histogram", "Box", "Heatmap", "Pie"])
        num_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(include="object").columns.tolist()
        fig, ax = plt.subplots()
        chart_images = []

        if chart_type == "Scatter" and len(num_cols) >= 2:
            x = st.selectbox("X", num_cols)
            y = st.selectbox("Y", num_cols, index=1)
            sns.scatterplot(data=df, x=x, y=y, ax=ax)
        elif chart_type == "Line" and len(num_cols) >= 2:
            x = st.selectbox("X", num_cols)
            y = st.selectbox("Y", num_cols, index=1)
            sns.lineplot(data=df, x=x, y=y, ax=ax)
        elif chart_type == "Histogram" and num_cols:
            col = st.selectbox("Column", num_cols)
            sns.histplot(df[col], kde=True, ax=ax)
        elif chart_type == "Box" and num_cols:
            col = st.selectbox("Column", num_cols)
            sns.boxplot(y=df[col], ax=ax)
        elif chart_type == "Heatmap" and len(num_cols) >= 2:
            sns.heatmap(df[num_cols].corr(), annot=True, ax=ax, cmap="coolwarm")
        elif chart_type == "Pie" and cat_cols:
            col = st.selectbox("Column", cat_cols)
            pie_data = df[col].value_counts()
            plt.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%")
            plt.axis("equal")

        st.pyplot(fig)
        img_bytes = fig_to_bytes(fig)
        chart_images.append((chart_type, img_bytes))

        st.download_button("📥 Download Plot as PNG", data=img_bytes, file_name="plot.png", mime="image/png")

        if st.button("📤 Download PPT Report"):
            pptx_buf = generate_ppt(df, chart_images)
            st.download_button("📥 Download PowerPoint", data=pptx_buf, file_name="report.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

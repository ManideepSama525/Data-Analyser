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

# ---------------------- Theme ----------------------
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

# ---------------------- Google Sheets Auth ----------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
workbook = client.open_by_key("1DFQst-DQMplGeI6OxfpSM1K_48rDJpT48Yy8Ur79d8g")
sheet = workbook.sheet1
try:
    upload_sheet = workbook.worksheet("upload_history")
except:
    upload_sheet = workbook.add_worksheet(title="upload_history", rows="1000", cols="3")
    upload_sheet.append_row(["username", "filename", "timestamp"])

# ---------------------- Session ----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "upload_content" not in st.session_state:
    st.session_state.upload_content = []

# ---------------------- Auth Utilities ----------------------
def get_users():
    return {row["username"]: row["password_hash"] for row in sheet.get_all_records()}

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
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    data = sheet.get_all_records()
    sheet.clear()
    sheet.append_row(["username", "password_hash"])
    for row in data:
        if row["username"] == username:
            sheet.append_row([username, hashed])
        else:
            sheet.append_row([row["username"], row["password_hash"]])

def log_upload(username, filename):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    upload_sheet.append_row([username, filename, timestamp])

def fetch_upload_history():
    return pd.DataFrame(upload_sheet.get_all_records())

# ---------------------- Chart & PPT Utility ----------------------
def fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

def generate_ppt_from_df(df, chart_dict):
    prs = Presentation()

    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "CSV Data Report"
    slide.placeholders[1].text = "Generated via Streamlit"

    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Summary Statistics"
    textbox = slide.placeholders[1]
    textbox.text = df.describe(include='all').round(2).to_string()

    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Data Sample (first 10 rows)"
    table = slide.shapes.add_table(min(10, len(df)) + 1, len(df.columns), Inches(0.5), Inches(1.5), Inches(9), Inches(4)).table
    for i, col in enumerate(df.columns):
        table.cell(0, i).text = str(col)
    for r in range(min(10, len(df))):
        for c in range(len(df.columns)):
            table.cell(r + 1, c).text = str(df.iloc[r, c])

    for title, fig in chart_dict.items():
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = title
        image = fig_to_png(fig)
        slide.shapes.add_picture(image, Inches(1), Inches(1.5), Inches(6), Inches(4.5))

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out

# ---------------------- Login / Signup UI ----------------------
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
                st.warning("Please fill all fields.")
            else:
                add_user(new_user, new_pass)
                st.success("Account created. Please log in.")
                st.rerun()

# ---------------------- Admin Panel ----------------------
if st.session_state.logged_in:
    st.sidebar.success(f"Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.username == "admin":
        st.sidebar.title("⚙️ Admin Panel")
        users = get_users()

        st.sidebar.markdown("### 🔐 Reset Password")
        user_to_reset = st.sidebar.selectbox("Select user", list(users.keys()))
        new_pw = st.sidebar.text_input("New Password", type="password")
        if st.sidebar.button("Reset Password"):
            reset_password(user_to_reset, new_pw)
            st.sidebar.success("Password updated.")

        st.sidebar.markdown("### 🗑️ Delete User")
        user_to_delete = st.sidebar.selectbox("Delete user", [u for u in users if u != "admin"])
        if st.sidebar.button("Delete User"):
            delete_user(user_to_delete)
            st.sidebar.success("User deleted.")

        st.sidebar.markdown("### 📋 Upload History")
        history_df = fetch_upload_history()
        st.sidebar.dataframe(history_df)

        st.sidebar.markdown("### 🗂️ Download Uploaded CSVs")
        for username, filename, csv_bytes in st.session_state.upload_content:
            st.sidebar.download_button(
                label=f"⬇ {filename} ({username})",
                data=csv_bytes,
                file_name=f"{username}_{filename}",
                mime="text/csv"
            )

# ---------------------- Main App ----------------------
if st.session_state.logged_in:
    st.title("📊 Upload & Analyze CSV")
    uploaded_file = st.file_uploader("Upload your CSV file", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        log_upload(st.session_state.username, uploaded_file.name)
        csv_bytes = uploaded_file.getvalue()
        st.session_state.upload_content.append((st.session_state.username, uploaded_file.name, csv_bytes))

        st.subheader(f"📄 Preview: `{uploaded_file.name}`")
        st.dataframe(df)

        st.subheader("🔍 Filter / Search Table")
        filter_col = st.selectbox("Column to filter", df.columns)
        if df[filter_col].dtype == "object":
            keyword = st.text_input("Search keyword")
            if keyword:
                df = df[df[filter_col].str.contains(keyword, case=False, na=False)]
        else:
            min_val = float(df[filter_col].min())
            max_val = float(df[filter_col].max())
            range_val = st.slider("Select range", min_val, max_val, (min_val, max_val))
            df = df[df[filter_col].between(*range_val)]

        st.dataframe(df)

        st.subheader("📈 Visualizations")
        num_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        chart_dict = {}

        if len(num_cols) >= 2:
            fig, ax = plt.subplots()
            sns.scatterplot(data=df, x=num_cols[0], y=num_cols[1], ax=ax)
            st.pyplot(fig)
            chart_dict["Scatter Plot"] = fig

            fig, ax = plt.subplots()
            sns.lineplot(data=df, x=num_cols[0], y=num_cols[1], ax=ax)
            chart_dict["Line Chart"] = fig

            fig, ax = plt.subplots()
            sns.heatmap(df[num_cols].corr(), annot=True, cmap="coolwarm", ax=ax)
            chart_dict["Heatmap"] = fig

        for col in num_cols:
            fig, ax = plt.subplots()
            sns.histplot(df[col], kde=True, ax=ax)
            chart_dict[f"Histogram - {col}"] = fig

            fig, ax = plt.subplots()
            sns.boxplot(y=df[col], ax=ax)
            chart_dict[f"Box Plot - {col}"] = fig

        for col in cat_cols:
            fig, ax = plt.subplots()
            pie_data = df[col].value_counts()
            plt.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%")
            plt.axis("equal")
            chart_dict[f"Pie Chart - {col}"] = fig

        ppt_buf = generate_ppt_from_df(df, chart_dict)
        st.download_button("📥 Download PowerPoint", data=ppt_buf,
                           file_name="report.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

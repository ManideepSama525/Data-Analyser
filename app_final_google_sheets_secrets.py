# Streamlit App with Google Sheets Auth, Hugging Face Summarizer, CSV Upload, and Selectable Graphs with Full PPT Export

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
        cat_cols = df.select_dtypes(include=['object']).columns

        st.subheader("📈 Select Graphs to Display")
        available_charts = []
        if len(numeric_cols) >= 2:
            available_charts += ["Scatter Plot", "Line Plot"]
        if len(numeric_cols) >= 1:
            available_charts += ["Histogram", "Box Plot", "Heatmap"]
        if len(cat_cols) >= 1:
            available_charts += ["Pie Chart"]

        selected_charts = st.multiselect("Select the charts you want to view on screen", available_charts, default=available_charts[:2])

        st.subheader("📊 Selected Charts")
        fig_list = []

        if "Scatter Plot" in available_charts:
            fig1, ax1 = plt.subplots()
            sns.scatterplot(data=df, x=numeric_cols[0], y=numeric_cols[1], ax=ax1)
            ax1.set_title("Scatter Plot")
            if "Scatter Plot" in selected_charts:
                st.pyplot(fig1)
            fig_list.append(("Scatter Plot", fig1))

        if "Line Plot" in available_charts:
            fig2, ax2 = plt.subplots()
            df[numeric_cols].plot(ax=ax2)
            ax2.set_title("Line Plot")
            if "Line Plot" in selected_charts:
                st.pyplot(fig2)
            fig_list.append(("Line Plot", fig2))

        if "Histogram" in available_charts:
            fig3, ax3 = plt.subplots()
            df[numeric_cols].hist(ax=ax3)
            plt.tight_layout()
            if "Histogram" in selected_charts:
                st.pyplot(fig3)
            fig_list.append(("Histogram", fig3))

        if "Box Plot" in available_charts:
            fig4, ax4 = plt.subplots()
            sns.boxplot(data=df[numeric_cols], ax=ax4)
            ax4.set_title("Box Plot")
            if "Box Plot" in selected_charts:
                st.pyplot(fig4)
            fig_list.append(("Box Plot", fig4))

        if "Heatmap" in available_charts:
            fig5, ax5 = plt.subplots()
            sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="coolwarm", ax=ax5)
            ax5.set_title("Correlation Heatmap")
            if "Heatmap" in selected_charts:
                st.pyplot(fig5)
            fig_list.append(("Heatmap", fig5))

        if "Pie Chart" in available_charts:
            pie_data = df[cat_cols[0]].value_counts()
            fig6, ax6 = plt.subplots()
            ax6.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
            ax6.set_title(f"Pie Chart of {cat_cols[0]}")
            ax6.axis('equal')
            if "Pie Chart" in selected_charts:
                st.pyplot(fig6)
            fig_list.append(("Pie Chart", fig6))

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
                slide_layout = ppt.slide_layouts[0]
                slide = ppt.slides.add_slide(slide_layout)
                slide.shapes.title.text = "Data Analysis Report"
                slide.placeholders[1].text = f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

                table_slide = ppt.slides.add_slide(ppt.slide_layouts[5])
                table_slide.shapes.title.text = "Sample Data"
                table = table_slide.shapes.add_table(rows=min(len(df), 6)+1, cols=len(df.columns), left=Inches(0.5), top=Inches(1.2), width=Inches(9), height=Inches(2)).table
                for col_idx, col in enumerate(df.columns):
                    table.cell(0, col_idx).text = col
                for row_idx in range(min(len(df), 6)):
                    for col_idx, col in enumerate(df.columns):
                        table.cell(row_idx + 1, col_idx).text = str(df.iloc[row_idx, col_idx])

                for title, fig in fig_list:
                    graph_slide = ppt.slides.add_slide(ppt.slide_layouts[5])
                    graph_slide.shapes.title.text = title
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                        fig.savefig(tmpfile.name)
                        graph_slide.shapes.add_picture(tmpfile.name, Inches(1), Inches(1.5), height=Inches(4.5))
                        os.unlink(tmpfile.name)

                ppt_bytes = BytesIO()
                ppt.save(ppt_bytes)
                ppt_bytes.seek(0)
                st.download_button("Download PPT", ppt_bytes, file_name=f"{uploaded_file.name}_analysis.pptx")

            except Exception as e:
                st.error(f"Failed to export PPT: {e}")

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pptx import Presentation
from pptx.util import Inches
import io
import datetime
import base64
import requests
import json

# ==================== CONFIG ====================
st.set_page_config(page_title="Data Analyzer", layout="wide", initial_sidebar_state="expanded")
st.markdown("<style>footer{visibility:hidden;}</style>", unsafe_allow_html=True)

# ==================== GOOGLE SHEETS SETUP ====================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = dict(st.secrets["google_sheets"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

auth_sheet = client.open("user_database").worksheet("users")
history_sheet = client.open("user_database").worksheet("upload_history")

ADMIN_USERNAME = "admin"

# ==================== AUTH FUNCTIONS ====================
def get_users():
    return auth_sheet.get_all_records()

def find_user(username):
    users = get_users()
    for user in users:
        if user['username'] == username:
            return user
    return None

def add_user(username, password):
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    auth_sheet.append_row([username, hashed_pw])

def delete_user(username_to_delete):
    try:
        data = auth_sheet.get_all_values()
        headers = data[0]
        remaining = [row for row in data if row[0] != username_to_delete and row[0] != 'username']
        auth_sheet.clear()
        auth_sheet.append_row(headers)
        for row in remaining[1:]:
            auth_sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        return False

def authenticate(username, password):
    user = find_user(username)
    if user and bcrypt.checkpw(password.encode(), user['password'].encode()):
        return True
    return False

def save_upload_history(username, filename):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_sheet.append_row([username, filename, timestamp])

def get_upload_history():
    return history_sheet.get_all_records()

# ==================== SUMMARIZATION ====================
def summarize_csv(df, token):
    text = df.to_csv(index=False)
    payload = {"inputs": text}
    headers = {"Authorization": f"Bearer {token}"}
    api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    response = requests.post(api_url, headers=headers, json=payload)
    try:
        return response.json()[0]['summary_text']
    except:
        return "Summary could not be generated."

# ==================== CHART GENERATION ====================
def generate_charts(df):
    charts = {}
    numeric_df = df.select_dtypes(include=['number']).dropna(axis=1, how='all')

    if numeric_df.shape[1] < 1:
        return charts

    if numeric_df.shape[1] >= 2:
        fig1, ax1 = plt.subplots()
        sns.scatterplot(data=numeric_df, x=numeric_df.columns[0], y=numeric_df.columns[1], ax=ax1)
        ax1.set_title("Scatter Plot")
        charts["Scatter Plot"] = fig1

    fig2, ax2 = plt.subplots()
    numeric_df.plot(ax=ax2)
    ax2.set_title("Line Plot")
    charts["Line Plot"] = fig2

    fig3, ax3 = plt.subplots()
    numeric_df.hist(ax=ax3)
    plt.tight_layout()
    charts["Histogram"] = fig3

    fig4, ax4 = plt.subplots()
    sns.boxplot(data=numeric_df, ax=ax4)
    ax4.set_title("Box Plot")
    charts["Box Plot"] = fig4

    fig5, ax5 = plt.subplots()
    sns.heatmap(numeric_df.corr(), annot=True, cmap="coolwarm", ax=ax5)
    ax5.set_title("Correlation Heatmap")
    charts["Heatmap"] = fig5

    cat_df = df.select_dtypes(include=['object'])
    if not cat_df.empty:
        col = cat_df.columns[0]
        pie_data = df[col].value_counts()
        fig6, ax6 = plt.subplots()
        ax6.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
        ax6.axis('equal')
        ax6.set_title(f"Pie Chart of {col}")
        charts["Pie Chart"] = fig6

    return charts

# ==================== PPT EXPORT ====================
def export_to_ppt(charts, summary):
    prs = Presentation()
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    slide.shapes.title.text = "Data Analysis Report"
    slide.placeholders[1].text = "Generated via Streamlit"

    if summary:
        bullet_slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(bullet_slide_layout)
        slide.shapes.title.text = "CSV Summary"
        content = slide.placeholders[1].text_frame
        for sentence in summary.split('.'):
            if sentence.strip():
                content.add_paragraph(sentence.strip())

    for title, fig in charts.items():
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = title
        img_stream = io.BytesIO()
        fig.savefig(img_stream, format='png')
        img_stream.seek(0)
        slide.shapes.add_picture(img_stream, Inches(1), Inches(1.5), width=Inches(8))

    ppt_stream = io.BytesIO()
    prs.save(ppt_stream)
    ppt_stream.seek(0)
    return ppt_stream

# ==================== MAIN APP ====================
def main():
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
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
        return

    st.sidebar.header("⚙️ Admin Panel")
    st.sidebar.markdown(f"Logged in as: <span style='color:lime'>{st.session_state.username}</span>", unsafe_allow_html=True)
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df)
            save_upload_history(st.session_state.username, uploaded_file.name)

            st.subheader("🔍 Filter Data")
            filter_col = st.selectbox("Select column to search/filter", df.columns)
            search_val = st.text_input("Enter search keyword")
            if search_val:
                filtered_df = df[df[filter_col].astype(str).str.contains(search_val, na=False)]
                st.dataframe(filtered_df)
            else:
                filtered_df = df

            st.subheader("📈 Chart Builder")
            all_charts = generate_charts(df)
            chart_options = list(all_charts.keys())
            selected_chart = st.selectbox("Select chart to view in app (all charts will be in PPT)", ["None"] + chart_options)
            if selected_chart != "None" and selected_chart in all_charts:
                st.pyplot(all_charts[selected_chart])
            charts_for_ppt = all_charts

            token = "hf_manideep"
            summary = summarize_csv(df, token)

            if st.button("Export to PPT"):
                ppt_stream = export_to_ppt(charts_for_ppt, summary)
                st.download_button("Download PPT", ppt_stream, file_name="data_analysis_report.pptx")

        except Exception as e:
            st.error(f"Error processing CSV: {e}")

    if st.session_state.username == ADMIN_USERNAME:
        st.subheader("🧑‍💻 Delete a User")
        users = get_users()
        usernames = [u['username'] for u in users if u['username'] != ADMIN_USERNAME]
        user_to_delete = st.selectbox("Select a user to delete", usernames)
        if st.button("Delete User"):
            if delete_user(user_to_delete):
                st.success(f"User '{user_to_delete}' deleted.")

        st.subheader("📁 Upload History (Admin Only)")
        history = get_upload_history()
        st.dataframe(pd.DataFrame(history))

main()

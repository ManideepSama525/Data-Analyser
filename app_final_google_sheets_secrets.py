import streamlit as st
import gspread
from google.oauth2client.service_account import ServiceAccountCredentials
import bcrypt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pptx import Presentation
from pptx.util import Inches
import io
import datetime
import requests
import tempfile
import os

# ===== PAGE CONFIG =====
st.set_page_config(page_title="Data Analyzer", layout="wide")
st.markdown("<style>footer{visibility:hidden;}</style>", unsafe_allow_html=True)

# ===== GOOGLE SHEETS AUTH =====
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

auth_sheet = client.open("streamlit_user_auth").worksheet("users")
history_sheet = client.open("streamlit_user_auth").worksheet("upload_history")
ADMIN_USERNAME = "manideep"

# ===== AUTH FUNCTIONS =====
def get_users():
    return auth_sheet.get_all_records()

def find_user(username):
    return next((u for u in get_users() if u['username'] == username), None)

def authenticate(username, password):
    user = find_user(username)
    return user and bcrypt.checkpw(password.encode(), user['password'].encode())

def save_upload_history(username, filename):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_sheet.append_row([username, filename, timestamp])

def get_upload_history():
    return history_sheet.get_all_records()

# ===== SUMMARIZATION =====
def summarize_text(text, token):
    api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(api_url, headers=headers, json={"inputs": text})
    try:
        return response.json()[0]['summary_text']
    except:
        return "Summary could not be generated."

# ===== MAIN =====
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

    uploaded_file = st.file_uploader("📤 Upload CSV", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        save_upload_history(st.session_state.username, uploaded_file.name)

        st.dataframe(df)
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        cat_cols = df.select_dtypes(include='object').columns.tolist()

        available_charts = []
        if len(numeric_cols) >= 2:
            available_charts += ["Scatter Plot", "Line Plot"]
        if len(numeric_cols) >= 1:
            available_charts += ["Histogram", "Box Plot", "Heatmap"]
        if len(cat_cols) >= 1:
            available_charts += ["Pie Chart"]

        selected_charts = st.multiselect("📈 Select charts to display", available_charts, default=available_charts[:2])

        if len(numeric_cols) >= 2:
            x_axis = st.selectbox("X-axis", numeric_cols, key="x")
            y_axis = st.selectbox("Y-axis", numeric_cols, key="y")

        fig_list = []
        if "Scatter Plot" in available_charts:
            fig, ax = plt.subplots()
            sns.scatterplot(data=df, x=x_axis, y=y_axis, ax=ax)
            ax.set_title("Scatter Plot")
            if "Scatter Plot" in selected_charts:
                st.pyplot(fig)
            fig_list.append(("Scatter Plot", fig))

        if "Line Plot" in available_charts:
            fig, ax = plt.subplots()
            df[[x_axis, y_axis]].plot(ax=ax)
            ax.set_title("Line Plot")
            if "Line Plot" in selected_charts:
                st.pyplot(fig)
            fig_list.append(("Line Plot", fig))

        if "Histogram" in available_charts:
            fig, ax = plt.subplots()
            df[numeric_cols].hist(ax=ax)
            plt.tight_layout()
            if "Histogram" in selected_charts:
                st.pyplot(fig)
            fig_list.append(("Histogram", fig))

        if "Box Plot" in available_charts:
            fig, ax = plt.subplots()
            sns.boxplot(data=df[numeric_cols], ax=ax)
            ax.set_title("Box Plot")
            if "Box Plot" in selected_charts:
                st.pyplot(fig)
            fig_list.append(("Box Plot", fig))

        if "Heatmap" in available_charts:
            fig, ax = plt.subplots()
            sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="coolwarm", ax=ax)
            ax.set_title("Correlation Heatmap")
            if "Heatmap" in selected_charts:
                st.pyplot(fig)
            fig_list.append(("Heatmap", fig))

        if "Pie Chart" in available_charts:
            pie_data = df[cat_cols[0]].value_counts()
            fig, ax = plt.subplots()
            ax.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            ax.set_title(f"Pie Chart of {cat_cols[0]}")
            if "Pie Chart" in selected_charts:
                st.pyplot(fig)
            fig_list.append(("Pie Chart", fig))

        st.subheader("📝 AI Text Summary")
        default_summary_text = df.head(15).to_string(index=False)
        text_input = st.text_area("Enter text to summarize", value=default_summary_text)
        summary = None
        if st.button("Summarize"):
            with st.spinner("Summarizing..."):
                summary = summarize_text(text_input, st.secrets["streamlit-summarizer"]["token"])
                st.success("Summary:")
                st.write(summary)

        if st.button("Export to PPT"):
            ppt = Presentation()
            slide = ppt.slides.add_slide(ppt.slide_layouts[0])
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

            if summary:
                summary_slide = ppt.slides.add_slide(ppt.slide_layouts[1])
                summary_slide.shapes.title.text = "Summary"
                summary_slide.placeholders[1].text = summary

            for title, fig in fig_list:
                graph_slide = ppt.slides.add_slide(ppt.slide_layouts[5])
                graph_slide.shapes.title.text = title
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                    fig.savefig(tmpfile.name)
                    graph_slide.shapes.add_picture(tmpfile.name, Inches(1), Inches(1.5), height=Inches(4.5))
                    os.unlink(tmpfile.name)

            ppt_bytes = io.BytesIO()
            ppt.save(ppt_bytes)
            ppt_bytes.seek(0)
            st.download_button("Download PPT", ppt_bytes, file_name=f"{uploaded_file.name}_analysis.pptx")

    if st.session_state.username == ADMIN_USERNAME:
        st.subheader("📁 Upload History")
        history = get_upload_history()
        st.dataframe(pd.DataFrame(history))

main()

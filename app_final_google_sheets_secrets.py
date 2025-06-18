import streamlit as st

# 🚀 Must be the very first Streamlit command!
st.set_page_config(
    page_title="Data Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
import requests
import json

st.markdown("<style>footer{visibility:hidden;}</style>", unsafe_allow_html=True)
st.title("📊 Data Analyzer")

try:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["google_sheets"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    auth_sheet = client.open("user_database").worksheet("users")
    history_sheet = client.open("user_database").worksheet("upload_history")
except Exception as e:
    st.error("Google Sheets credentials not found or invalid. Please check .streamlit/secrets.toml.")
    st.stop()

ADMIN_USERNAME = "admin"


def get_users():
    return auth_sheet.get_all_records()


def find_user(username):
    users = get_users()
    for user in users:
        if user["username"] == username:
            return user
    return None


def add_user(username, password):
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    auth_sheet.append_row([username, hashed_pw])


def delete_user(username_to_delete):
    try:
        data = auth_sheet.get_all_values()
        headers = data[0]
        remaining = [row for row in data if row[0] != username_to_delete and row[0] != "username"]
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
    if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
        return True
    return False


def save_upload_history(username, filename):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_sheet.append_row([username, filename, timestamp])


def get_upload_history():
    return history_sheet.get_all_records()


def summarize_csv(df, token):
    text = df.to_csv(index=False)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": text}
    response = requests.post(
        "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
        headers=headers,
        json=payload
    )
    try:
        return response.json()[0]["summary_text"]
    except:
        return "Summary could not be generated."


def export_to_ppt(charts, summary, selected_charts):
    prs = Presentation()
    title_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_layout)
    slide.shapes.title.text = "Data Analysis Report"
    slide.placeholders[1].text = "Generated via Streamlit"

    if summary:
        bullet_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(bullet_layout)
        slide.shapes.title.text = "Summary"
        tf = slide.placeholders[1].text_frame
        for sentence in summary.split("."):
            sentence = sentence.strip()
            if sentence:
                tf.add_paragraph().text = sentence

    for title in selected_charts:
        if title in charts:
            fig = charts[title]
            slide = prs.slides.add_slide(prs.slide_layouts[5])
            slide.shapes.title.text = title
            img_stream = io.BytesIO()
            fig.savefig(img_stream, format="png")
            img_stream.seek(0)
            slide.shapes.add_picture(img_stream, Inches(1), Inches(1.5), width=Inches(8))

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


def generate_selected_charts(df, selected_charts, params):
    charts = {}
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if "Scatter Plot" in selected_charts:
        fig, ax = plt.subplots()
        sns.scatterplot(data=df, x=params["Scatter Plot"]["x"], y=params["Scatter Plot"]["y"], ax=ax)
        ax.set_title("Scatter Plot")
        charts["Scatter Plot"] = fig
        st.pyplot(fig)

    if "Line Plot" in selected_charts:
        fig, ax = plt.subplots()
        df.plot(x=params["Line Plot"]["x"], y=params["Line Plot"]["y"], ax=ax)
        ax.set_title("Line Plot")
        charts["Line Plot"] = fig
        st.pyplot(fig)

    if "Histogram" in selected_charts:
        fig, ax = plt.subplots()
        df[numeric_cols].hist(ax=ax)
        plt.tight_layout()
        charts["Histogram"] = fig
        st.pyplot(fig)

    if "Box Plot" in selected_charts:
        fig, ax = plt.subplots()
        sns.boxplot(data=df[numeric_cols], ax=ax)
        ax.set_title("Box Plot")
        charts["Box Plot"] = fig
        st.pyplot(fig)

    if "Violin Plot" in selected_charts:
        fig, ax = plt.subplots()
        sns.violinplot(data=df[numeric_cols], ax=ax, inner="box")
        ax.set_title("Violin Plot")
        charts["Violin Plot"] = fig
        st.pyplot(fig)

    if "Heatmap" in selected_charts:
        fig, ax = plt.subplots()
        sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="coolwarm", ax=ax)
        ax.set_title("Correlation Heatmap")
        charts["Heatmap"] = fig
        st.pyplot(fig)

    if "Pie Chart" in selected_charts:
        col = params["Pie Chart"]["col"]
        counts = df[col].value_counts()
        fig, ax = plt.subplots()
        ax.pie(counts, labels=counts.index, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        ax.set_title(f"Pie Chart of {col}")
        charts["Pie Chart"] = fig
        st.pyplot(fig)

    return charts


def main():
    st.success("Debug: Reached main")
    # Remaining app logic including login, chart builder, export, admin etc.

if __name__ == "__main__":
    main()

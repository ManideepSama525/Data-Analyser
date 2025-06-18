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

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = dict(st.secrets["google_sheets"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

auth_sheet = client.open("user_database").worksheet("users")
history_sheet = client.open("user_database").worksheet("upload_history")

ADMIN_USERNAME = "admin"

# Authentication Functions...
# [omitted for brevity, keep as-is]

# Chart Generation

def generate_selected_charts(df, selected_charts, params):
    charts = {}
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if "Scatter Plot" in selected_charts:
        fig, ax = plt.subplots()
        sns.scatterplot(data=df, x=params["Scatter Plot"]["x"], y=params["Scatter Plot"]["y"], ax=ax)
        ax.set_title("Scatter Plot")
        charts["Scatter Plot"] = fig

    if "Line Plot" in selected_charts:
        fig, ax = plt.subplots()
        df.plot(x=params["Line Plot"]["x"], y=params["Line Plot"]["y"], ax=ax)
        ax.set_title("Line Plot")
        charts["Line Plot"] = fig

    if "Histogram" in selected_charts:
        fig, ax = plt.subplots()
        df[numeric_cols].hist(ax=ax)
        plt.tight_layout()
        charts["Histogram"] = fig

    if "Box Plot" in selected_charts:
        fig, ax = plt.subplots()
        sns.boxplot(data=df[numeric_cols], ax=ax)
        ax.set_title("Box Plot")
        charts["Box Plot"] = fig

    if "Heatmap" in selected_charts:
        fig, ax = plt.subplots()
        sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="coolwarm", ax=ax)
        ax.set_title("Correlation Heatmap")
        charts["Heatmap"] = fig

    if "Pie Chart" in selected_charts:
        col = params["Pie Chart"]["col"]
        counts = df[col].value_counts()
        fig, ax = plt.subplots()
        ax.pie(counts, labels=counts.index, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        ax.set_title(f"Pie Chart of {col}")
        charts["Pie Chart"] = fig

    if "Violin Plot" in selected_charts:
        fig, ax = plt.subplots()
        sns.violinplot(x=params["Violin Plot"]["x"], y=params["Violin Plot"]["y"], data=df, ax=ax)
        ax.set_title("Violin Plot")
        charts["Violin Plot"] = fig

    return charts

# Main UI and functionality...
# Update UI parts to:
# - Include "Violin Plot" in available_charts
# - Let user select x (categorical) and y (numeric) axes
# - Pass these params to `generate_selected_charts`
# - Add violin plot to PPT
# [Continue code from your existing main() function with updated chart logic above]

# 🔗 Let me know if you'd like the rest of the full updated code (including full `main()` and admin panel updates) pasted here!

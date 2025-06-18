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

# ... (same helper functions from before: get_users, authenticate, etc.)

# Chart generation

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
        sns.violinplot(data=df[numeric_cols], ax=ax)
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
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    if not st.session_state.logged_in:
        st.subheader("🔐 Welcome")
        auth_action = st.radio("Choose action", ["Login", "Sign Up"], horizontal=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if auth_action == "Login":
            if st.button("Login"):
                if authenticate(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        else:
            if st.button("Sign Up"):
                if find_user(username):
                    st.error("Username already exists.")
                elif not username or not password:
                    st.error("Provide both username and password.")
                else:
                    add_user(username, password)
                    st.success("✅ Account created! Please Log In.")
        return

    st.sidebar.header("⚙️ Admin Panel")
    st.sidebar.markdown(
        f"Logged in as: <span style='color:lime'>{st.session_state.username}</span>",
        unsafe_allow_html=True
    )
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    uploaded_file = st.file_uploader("📁 Upload CSV", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df)
        save_upload_history(st.session_state.username, uploaded_file.name)

        st.subheader("🔍 Filter Data")
        col = st.selectbox("Filter column", df.columns)
        val = st.text_input("Search keyword")
        filtered = df[df[col].astype(str).str.contains(val, na=False)] if val else df
        st.dataframe(filtered)

        st.subheader("📊 Chart Builder")
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(include="object").columns.tolist()

        available_charts = ["Scatter Plot", "Line Plot", "Histogram", "Box Plot", "Violin Plot", "Heatmap"]
        if cat_cols:
            available_charts.append("Pie Chart")

        selected = st.multiselect("Select charts to include", available_charts)
        chart_params = {}

        if "Scatter Plot" in selected:
            x = st.selectbox("Scatter X", numeric_cols, key="scatter_x")
            y = st.selectbox("Scatter Y", numeric_cols, key="scatter_y")
            chart_params["Scatter Plot"] = {"x": x, "y": y}

        if "Line Plot" in selected:
            x = st.selectbox("Line X", df.columns, key="line_x")
            y = st.multiselect("Line Y", numeric_cols, default=numeric_cols, key="line_y")
            chart_params["Line Plot"] = {"x": x, "y": y}

        if "Pie Chart" in selected:
            cat = st.selectbox("Pie column", cat_cols, key="pie_col")
            chart_params["Pie Chart"] = {"col": cat}

        if st.button("Export to PPT"):
            charts = generate_selected_charts(df, selected, chart_params)
            summary = summarize_csv(df, token="hf_manideep")
            ppt = export_to_ppt(charts, summary, selected)
            st.download_button("📥 Download PPT", data=ppt, file_name="data_analysis_report.pptx")

    if st.session_state.username == ADMIN_USERNAME:
        st.subheader("🧑‍💼 Admin: Manage Users / History")
        users = get_users()
        deletable = [u["username"] for u in users if u["username"] != ADMIN_USERNAME]
        to_del = st.selectbox("Delete User", deletable)
        if st.button("Delete"):
            if delete_user(to_del):
                st.success(f"User '{to_del}' deleted.")

        st.subheader("📜 Upload History")
        st.dataframe(pd.DataFrame(get_upload_history()))

if __name__ == "__main__":
    main()

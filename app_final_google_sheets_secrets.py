import streamlit as st
import bcrypt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import io
from pptx import Presentation
from pptx.util import Inches
from PIL import Image
import base64
import os

# ---------------------- Authentication Functions ----------------------
users_db = {}

def authenticate(username, password):
    if username in users_db:
        hashed = users_db[username]
        return bcrypt.checkpw(password.encode(), hashed)
    return False

def add_user(username, password):
    users_db[username] = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def find_user(username):
    return username in users_db

# ---------------------- Chart Plotting Functions ----------------------
def plot_chart(chart_type, df, x_col, y_col):
    fig, ax = plt.subplots()
    if chart_type == "Line":
        sns.lineplot(data=df, x=x_col, y=y_col, ax=ax)
    elif chart_type == "Bar":
        sns.barplot(data=df, x=x_col, y=y_col, ax=ax)
    elif chart_type == "Scatter":
        sns.scatterplot(data=df, x=x_col, y=y_col, ax=ax)
    elif chart_type == "Histogram":
        sns.histplot(data=df, x=x_col, ax=ax)
    elif chart_type == "Box":
        sns.boxplot(data=df, x=x_col, y=y_col, ax=ax)
    elif chart_type == "Violin":
        sns.violinplot(data=df, x=x_col, y=y_col, ax=ax)
    st.pyplot(fig)
    return fig

# ---------------------- PowerPoint Export Function ----------------------
def generate_ppt(charts):
    prs = Presentation()
    for chart in charts:
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        image_stream = io.BytesIO()
        chart.savefig(image_stream, format='png')
        image_stream.seek(0)
        slide.shapes.add_picture(image_stream, Inches(1), Inches(1), Inches(8), Inches(5))
    ppt_bytes = io.BytesIO()
    prs.save(ppt_bytes)
    ppt_bytes.seek(0)
    return ppt_bytes

# ---------------------- Main App ----------------------
def main():
    st.set_page_config(page_title="Data Analyzer", layout="wide")
    st.title("📊 Data Analyzer")

    # Debug check
    st.write("✅ Debug: Reached main")

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

    # App Content After Login
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.subheader("📄 Data Preview")
        st.dataframe(df)

        numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
        all_columns = df.columns.tolist()

        chart_type = st.selectbox("Choose a chart type", ["Line", "Bar", "Scatter", "Histogram", "Box", "Violin"])
        x_axis = st.selectbox("X-axis", all_columns)
        y_axis = st.selectbox("Y-axis", numeric_columns)

        if st.button("Generate Chart"):
            chart_fig = plot_chart(chart_type, df, x_axis, y_axis)
            st.session_state['last_chart'] = chart_fig

        if 'last_chart' in st.session_state:
            if st.button("Download as PowerPoint"):
                ppt_bytes = generate_ppt([st.session_state['last_chart']])
                st.download_button("📥 Download PPT", ppt_bytes, file_name="charts.pptx")

if __name__ == "__main__":
    main()

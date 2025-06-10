# Complete Streamlit App with Google Auth, Multi-CSV Upload, Light/Dark Mode, and Hugging Face Summarizer Integration

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
from streamlit_authenticator import Authenticate
import yaml
from yaml.loader import SafeLoader

# --- Setup page config ---
st.set_page_config(page_title="Data Analyzer", layout="wide", initial_sidebar_state="expanded")

# --- Light/Dark Mode Toggle ---
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

# --- User Authentication ---
with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, authentication_status, username = authenticator.login("Login", "sidebar")

if authentication_status:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.success(f"Logged in as: {name}")

    st.title("📊 Data Analyzer")

    uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)

    if uploaded_files:
        for uploaded_file in uploaded_files:
            df = pd.read_csv(uploaded_file)
            st.header(f"Dataset: {uploaded_file.name}")
            st.dataframe(df)

            # --- Plotting ---
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
            if len(numeric_cols) >= 2:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Scatter Plot")
                    fig, ax = plt.subplots()
                    sns.scatterplot(data=df, x=numeric_cols[0], y=numeric_cols[1], ax=ax)
                    st.pyplot(fig)

                with col2:
                    st.subheader("Line Plot")
                    fig2 = px.line(df[numeric_cols])
                    st.plotly_chart(fig2)

            # --- Text Summary (Hugging Face) ---
            st.subheader("📄 AI Text Summary")
            try:
                hf_token = st.secrets["streamlit-summarizer"]["token"]
                api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
                headers = {"Authorization": f"Bearer {hf_token}"}

                text_input = st.text_area("Enter text to summarize")
                if st.button("Summarize") and text_input:
                    with st.spinner("Summarizing..."):
                        response = requests.post(api_url, headers=headers, json={"inputs": text_input})
                        summary = response.json()[0]['summary_text']
                        st.success("Summary:")
                        st.write(summary)
            except Exception as e:
                st.error("Hugging Face token not found in secrets. Please add it to .streamlit/secrets.toml with section [streamlit-summarizer]")

            # --- Export to PPT ---
            st.subheader("📤 Export to PPT")
            if st.button("Export to PPT"):
                try:
                    ppt = Presentation()
                    slide_layout = ppt.slide_layouts[5]
                    slide = ppt.slides.add_slide(slide_layout)
                    title = slide.shapes.title
                    title.text = f"Dataset Overview: {uploaded_file.name}"

                    # Add a sample plot
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                        fig, ax = plt.subplots()
                        sns.histplot(df[numeric_cols[0]], ax=ax)
                        fig.savefig(tmpfile.name)
                        slide.shapes.add_picture(tmpfile.name, Inches(1), Inches(1.5), height=Inches(4))
                        os.unlink(tmpfile.name)

                    ppt_bytes = BytesIO()
                    ppt.save(ppt_bytes)
                    ppt_bytes.seek(0)
                    st.download_button("Download PPT", ppt_bytes, file_name="presentation.pptx")

                except Exception as e:
                    st.error(f"Failed to export PPT: {e}")

if authentication_status is False:
    st.error("Username or password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
else:
    st.error("Please log in to access the app.")


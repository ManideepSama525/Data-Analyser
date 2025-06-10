import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import datetime
import requests
import tempfile
import os
from pptx import Presentation
from pptx.util import Inches
from io import BytesIO

# Assume df, numeric_cols, cat_cols, and uploaded_file are already defined earlier in your app

st.subheader("📈 Select Graphs to Display")

available_charts = []
if len(numeric_cols) >= 2:
    available_charts += ["Scatter Plot", "Line Plot"]
if len(numeric_cols) >= 1:
    available_charts += ["Histogram", "Box Plot", "Heatmap"]
if len(cat_cols) >= 1:
    available_charts += ["Pie Chart"]

selected_charts = st.multiselect(
    "Select the charts you want to view on screen",
    available_charts,
    default=available_charts[:2]
)

# Axes selectors for scatter and line plot
if len(numeric_cols) >= 2:
    x_axis = st.selectbox("Select X-axis", numeric_cols, key=f"x_{uploaded_file.name}")
    y_axis = st.selectbox("Select Y-axis", numeric_cols, key=f"y_{uploaded_file.name}")

st.subheader("📊 Selected Charts")
fig_list = []

if "Scatter Plot" in available_charts:
    fig1, ax1 = plt.subplots(figsize=(6, 4))
    sns.scatterplot(data=df, x=x_axis, y=y_axis, ax=ax1)
    ax1.set_title("Scatter Plot")
    if "Scatter Plot" in selected_charts:
        st.pyplot(fig1)
    fig_list.append(("Scatter Plot", fig1))

if "Line Plot" in available_charts:
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    df[[x_axis, y_axis]].plot(ax=ax2)
    ax2.set_title("Line Plot")
    if "Line Plot" in selected_charts:
        st.pyplot(fig2)
    fig_list.append(("Line Plot", fig2))

if "Histogram" in available_charts:
    fig3, ax3 = plt.subplots(figsize=(6, 4))
    df[numeric_cols].hist(ax=ax3)
    plt.tight_layout()
    if "Histogram" in selected_charts:
        st.pyplot(fig3)
    fig_list.append(("Histogram", fig3))

if "Box Plot" in available_charts:
    fig4, ax4 = plt.subplots(figsize=(6, 4))
    sns.boxplot(data=df[numeric_cols], ax=ax4)
    ax4.set_title("Box Plot")
    if "Box Plot" in selected_charts:
        st.pyplot(fig4)
    fig_list.append(("Box Plot", fig4))

if "Heatmap" in available_charts:
    fig5, ax5 = plt.subplots(figsize=(6, 4))
    sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="coolwarm", ax=ax5)
    ax5.set_title("Correlation Heatmap")
    if "Heatmap" in selected_charts:
        st.pyplot(fig5)
    fig_list.append(("Heatmap", fig5))

if "Pie Chart" in available_charts:
    pie_data = df[cat_cols[0]].value_counts()
    fig6, ax6 = plt.subplots(figsize=(6, 4))
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

    default_summary_text = df.head(15).to_string(index=False)
    text_input = st.text_area("Enter text to summarize", value=default_summary_text)

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
        table = table_slide.shapes.add_table(
            rows=min(len(df), 6)+1,
            cols=len(df.columns),
            left=Inches(0.5),
            top=Inches(1.2),
            width=Inches(9),
            height=Inches(2)
        ).table
        for col_idx, col in enumerate(df.columns):
            table.cell(0, col_idx).text = col
        for row_idx in range(min(len(df), 6)):
            for col_idx, col in enumerate(df.columns):
                table.cell(row_idx + 1, col_idx).text = str(df.iloc[row_idx, col_idx])

        if 'summary' in locals():
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

        ppt_bytes = BytesIO()
        ppt.save(ppt_bytes)
        ppt_bytes.seek(0)
        st.download_button("Download PPT", ppt_bytes, file_name=f"{uploaded_file.name}_analysis.pptx")

    except Exception as e:
        st.error(f"Failed to export PPT: {e}")

import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import bcrypt
import time

# -------------------------------
# 🔐 User Database (hashed)
# -------------------------------
users = {
    "admin": bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
    "alice": bcrypt.hashpw("alicepwd".encode(), bcrypt.gensalt()).decode(),
    "bob": bcrypt.hashpw("bobsecure".encode(), bcrypt.gensalt()).decode(),
}

# ----------------------------------
# Streamlit Page Config
# ----------------------------------
st.set_page_config(page_title="Data Analyzer", layout="wide")

# Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Sidebar reset button
st.sidebar.button("🔁 Reset App", on_click=lambda: st.session_state.clear())

# ----------------------------------
# Login Logic
# ----------------------------------
def verify_user(username, password):
    if username in users:
        hashed = users[username].encode()
        return bcrypt.checkpw(password.encode(), hashed)
    return False

if not st.session_state.logged_in:
    st.title("🔐 Secure Login to Data Analyzer")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if verify_user(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Welcome, {username}! Logging you in...")
            time.sleep(1)
            st.experimental_rerun()
        else:
            st.error("Invalid username or password.")

# ----------------------------------
# Main App (after login)
# ----------------------------------
else:
    st.sidebar.success(f"✅ Logged in as {st.session_state.username}")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()

    st.title("📊 Data Analyzer")
    st.markdown("Upload one or more CSV files to explore and visualize your data.")
    uploaded_files = st.file_uploader("Choose CSV files", type="csv", accept_multiple_files=True)

    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.header(f"📁 {uploaded_file.name}")
            df = pd.read_csv(uploaded_file)

            if st.checkbox("🔍 Show Raw Data", key=f"raw_{uploaded_file.name}"):
                st.dataframe(df, use_container_width=True)

            if st.checkbox("📈 Show Summary Statistics", key=f"summary_{uploaded_file.name}"):
                st.write(df.describe(include='all'))

            with st.expander("📌 Data Info"):
                info = pd.DataFrame({
                    'Data Type': df.dtypes,
                    'Missing Values': df.isnull().sum(),
                    'Unique Values': df.nunique()
                })
                st.dataframe(info)

            st.subheader("🔍 Filter Data")
            filter_col = st.selectbox("Select column to filter", df.columns, key=f"filter_{uploaded_file.name}")
            unique_vals = df[filter_col].dropna().unique()
            selected_vals = st.multiselect("Select values", unique_vals, key=f"values_{uploaded_file.name}")
            if selected_vals:
                df = df[df[filter_col].isin(selected_vals)]
                st.success(f"Filtered to {len(df)} rows.")
                st.dataframe(df, use_container_width=True)

            st.subheader("📊 Visualization")
            plot_type = st.selectbox(
                "Select plot type",
                ["Scatter", "Line", "Histogram", "Box", "Heatmap", "Pie Chart"],
                key=f"plot_{uploaded_file.name}"
            )
            num_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            cat_cols = df.select_dtypes(include=['object']).columns.tolist()

            fig, ax = plt.subplots(figsize=(8, 5))

            if plot_type == "Scatter" and len(num_cols) >= 2:
                x = st.selectbox("X-axis", num_cols, key=f"scatter_x_{uploaded_file.name}")
                y = st.selectbox("Y-axis", num_cols, key=f"scatter_y_{uploaded_file.name}")
                sns.scatterplot(data=df, x=x, y=y, ax=ax)
            elif plot_type == "Line" and len(num_cols) >= 2:
                x = st.selectbox("X-axis", num_cols, key=f"line_x_{uploaded_file.name}")
                y = st.selectbox("Y-axis", num_cols, key=f"line_y_{uploaded_file.name}")
                sns.lineplot(data=df, x=x, y=y, ax=ax)
            elif plot_type == "Histogram" and num_cols:
                col = st.selectbox("Select column", num_cols, key=f"hist_col_{uploaded_file.name}")
                sns.histplot(df[col], bins=30, kde=True, ax=ax)
            elif plot_type == "Box" and num_cols:
                col = st.selectbox("Select column", num_cols, key=f"box_col_{uploaded_file.name}")
                sns.boxplot(y=df[col], ax=ax)
            elif plot_type == "Heatmap" and len(num_cols) >= 2:
                sns.heatmap(df[num_cols].corr(), annot=True, cmap="coolwarm", ax=ax)
            elif plot_type == "Pie Chart" and cat_cols:
                col = st.selectbox("Select column", cat_cols, key=f"pie_col_{uploaded_file.name}")
                pie_data = df[col].value_counts()
                plt.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%", startangle=140)
                plt.axis("equal")

            st.pyplot(fig)

            # Download filtered data
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Filtered Data", csv, f"filtered_{uploaded_file.name}", "text/csv")

    st.sidebar.title("ℹ About")
    st.sidebar.info("This app uses Streamlit, Pandas, Seaborn, and Matplotlib to analyze and visualize CSV data.")


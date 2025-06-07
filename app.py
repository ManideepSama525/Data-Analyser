import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import bcrypt
import time
import json
import os

#Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# -------------------------------
# 🔐 Persistent User Storage
# -------------------------------
USER_FILE = "users.json"
SETTINGS_FILE = "settings.json"

# Load users from file
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return {}

# Save users to file
def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

# Load settings from file
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"allow_signup": True}

# Save settings to file
def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

users = load_users()
settings = load_settings()

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
# Authentication Logic
# ----------------------------------
def verify_user(username, password):
    if username in users:
        hashed = users[username].encode()
        return bcrypt.checkpw(password.encode(), hashed)
    return False

# ----------------------------------
# Login / Signup Interface
# ----------------------------------
if not st.session_state.logged_in:
    st.title("🔐 Secure Access to Data Analyzer")

    tab1, tab2 = st.tabs(["🔓 Login", "🆕 Sign Up"])

    # --- Login Tab ---
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            if verify_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Welcome, {username}! Logging you in...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid username or password.")

    # --- Sign Up Tab ---
    with tab2:
        if settings.get("allow_signup", True):
            new_user = st.text_input("New Username", key="signup_user")
            new_pass = st.text_input("New Password", type="password", key="signup_pass")

            if st.button("Create Account"):
                if new_user in users:
                    st.warning("Username already exists. Please choose a different one.")
                elif new_user.strip() == "" or new_pass.strip() == "":
                    st.warning("Username and password cannot be empty.")
                else:
                    hashed_pw = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                    users[new_user] = hashed_pw
                    save_users(users)
                    st.success("Account created! You can now log in.")
        else:
            st.warning("🛑 Signup is currently disabled by the admin.")

# ----------------------------------
# Main App (after login)
# ----------------------------------
else:
    st.sidebar.success(f"✅ Logged in as {st.session_state.username}")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()

    # ---------------------
    # 🛠 Admin Panel
    # ---------------------
    if st.session_state.username == "admin":
        st.sidebar.title("🛠 Admin Panel")

        # Toggle signup
        allow_signup = settings.get("allow_signup", True)
        signup_toggle = st.sidebar.checkbox("✅ Allow User Signup", value=allow_signup)
        if signup_toggle != allow_signup:
            settings["allow_signup"] = signup_toggle
            save_settings(settings)
            st.sidebar.success("Signup setting updated.")

        # View all users
        if st.sidebar.checkbox("👥 View All Users"):
            st.sidebar.subheader("Registered Users")
            st.sidebar.json(list(users.keys()))

        # Delete user
        if st.sidebar.checkbox("🗑 Delete a User"):
            user_list = [u for u in users if u != "admin"]
            user_to_delete = st.sidebar.selectbox("Select User", user_list)
            if st.sidebar.button("Delete Selected User"):
                if user_to_delete in users:
                    del users[user_to_delete]
                    save_users(users)
                    st.sidebar.success(f"User '{user_to_delete}' deleted.")
                    st.experimental_rerun()

    # ---------------------
    # 📊 Main Data Analyzer
    # ---------------------
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


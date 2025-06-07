import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt
import pandas as pd
import json
import seaborn as sns
import matplotlib.pyplot as plt

# -------------------------------
# Google Sheets Setup via st.secrets
# -------------------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_key("1DFQst-DQMplGel6OxfpSM1K_48rDJpT48Y8Ur79d8g").sheet1

# -------------------------------
# Helper Functions
# -------------------------------
def get_users():
    try:
        data = sheet.get_all_records()
        return {row['username']: row['password_hash'] for row in data}
    except:
        return {}

def add_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    sheet.append_row([username, hashed])

def verify_user(username, password):
    users = get_users()
    if username in users:
        return bcrypt.checkpw(password.encode(), users[username].encode())
    return False

def delete_user(username):
    users = sheet.get_all_records()
    for i, user in enumerate(users, start=2):  # Row 1 is header
        if user['username'] == username:
            sheet.delete_row(i)
            return True
    return False

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="Data Analyzer", layout="wide")
st.title("🔐 Secure Data Analyzer")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔓 Login", "🆕 Sign Up"])

    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if verify_user(username, password):
                st.success(f"Welcome, {username}!")
                st.session_state.logged_in = True
                st.session_state.username = username
            else:
                st.error("Invalid credentials.")

    with tab2:
        new_user = st.text_input("New Username", key="signup_user")
        new_pass = st.text_input("New Password", type="password", key="signup_pass")
        if st.button("Create Account"):
            users = get_users()
            if new_user in users:
                st.warning("Username already exists.")
            elif new_user.strip() == "" or new_pass.strip() == "":
                st.warning("Fields cannot be empty.")
            else:
                add_user(new_user, new_pass)
                st.success("Account created! Please log in.")

else:
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.success("You have been logged out. Please click 'Reset App' or refresh the page.")

    st.header("🎉 Welcome to the Protected Area!")
    st.write("You can now upload CSV files and analyze your data.")

    # -------------------------------
    # CSV Upload and Analysis
    # -------------------------------
    st.subheader("📁 Upload and Analyze CSV")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("📄 Preview of Data:")
        st.dataframe(df, use_container_width=True)

        st.write("📊 Summary Statistics:")
        st.write(df.describe(include='all'))

        with st.expander("📌 Data Info"):
            info = pd.DataFrame({
                'Data Type': df.dtypes,
                'Missing Values': df.isnull().sum(),
                'Unique Values': df.nunique()
            })
            st.dataframe(info)

        st.subheader("📊 Visualization")
        plot_type = st.selectbox("Choose Plot Type", ["Scatter", "Line", "Histogram", "Box", "Heatmap", "Pie Chart"])
        num_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object']).columns.tolist()

        fig, ax = plt.subplots(figsize=(8, 5))

        if plot_type == "Scatter" and len(num_cols) >= 2:
            x = st.selectbox("X-axis", num_cols, key="scatter_x")
            y = st.selectbox("Y-axis", num_cols, key="scatter_y")
            sns.scatterplot(data=df, x=x, y=y, ax=ax)
        elif plot_type == "Line" and len(num_cols) >= 2:
            x = st.selectbox("X-axis", num_cols, key="line_x")
            y = st.selectbox("Y-axis", num_cols, key="line_y")
            sns.lineplot(data=df, x=x, y=y, ax=ax)
        elif plot_type == "Histogram" and num_cols:
            col = st.selectbox("Select column", num_cols, key="hist_col")
            sns.histplot(df[col], bins=30, kde=True, ax=ax)
        elif plot_type == "Box" and num_cols:
            col = st.selectbox("Select column", num_cols, key="box_col")
            sns.boxplot(y=df[col], ax=ax)
        elif plot_type == "Heatmap" and len(num_cols) >= 2:
            sns.heatmap(df[num_cols].corr(), annot=True, cmap="coolwarm", ax=ax)
        elif plot_type == "Pie Chart" and cat_cols:
            col = st.selectbox("Select column", cat_cols, key="pie_col")
            pie_data = df[col].value_counts()
            plt.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%", startangle=140)
            plt.axis("equal")

        st.pyplot(fig)

        # Download CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, "analyzed_data.csv", "text/csv")

    # Admin-only features
    if st.session_state.username == "admin":
        st.sidebar.title("🛠 Admin Panel")
        if st.sidebar.checkbox("👥 View All Users"):
            users = get_users()
            st.sidebar.write("Registered Users:")
            st.sidebar.json(list(users.keys()))

        users = get_users()
        user_list = [u for u in users if u != "admin"]
        if st.sidebar.checkbox("🗑 Delete a User"):
            user_to_delete = st.sidebar.selectbox("Select user", user_list)
            if st.sidebar.button("Confirm Delete"):
                if delete_user(user_to_delete):
                    st.sidebar.success(f"Deleted user: {user_to_delete}")
                else:
                    st.sidebar.error("User not found or could not delete.")

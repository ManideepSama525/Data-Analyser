import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import bcrypt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pptx import Presentation
from pptx.util import Inches
import io
import datetime
import requests
import time

# ==================== CONFIG ====================
st.set_page_config(page_title="Data Analyzer", layout="wide", initial_sidebar_state="expanded")
st.markdown("<style>footer{visibility:hidden;}</style>", unsafe_allow_html=True)

# ==================== GOOGLE SHEETS SETUP ====================
# Note: Ensure the following setup in Google Sheets:
# 1. Create a spreadsheet named exactly "user_database".
# 2. Share it with the service account email: streamlit-user-auth@streamlit-user-auth.iam.gserviceaccount.com (Editor access).
# 3. Create two worksheets: "users" (columns: username, password) and "upload_history" (columns: username, filename, timestamp).
# 4. Add an admin user manually to the "users" worksheet:
#    - Run: import bcrypt; hashed = bcrypt.hashpw("your_password".encode(), bcrypt.gensalt()).decode()
#    - Add row: username: manideep, password: <hashed_password>

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def connect_to_google_sheets(max_retries=3, delay=2):
    for attempt in range(max_retries):
        try:
            # Step 1: Create credentials
            creds = Credentials.from_service_account_info(st.secrets["google_sheets"], scopes=scope)
            # Step 2: Authorize the client
            client = gspread.authorize(creds)
            # Step 3: Open the spreadsheet (updated to user_database)
            spreadsheet = client.open("user_database")
            # Step 4: Access the worksheets
            auth_sheet = spreadsheet.worksheet("users")
            history_sheet = spreadsheet.worksheet("upload_history")
            return auth_sheet, history_sheet
        except gspread.exceptions.SpreadsheetNotFound as e:
            st.error(f"Spreadsheet 'user_database' not found. Please create it and share it with the service account.")
            st.stop()
        except gspread.exceptions.WorksheetNotFound as e:
            st.error(f"Worksheet not found: {e}. Ensure 'users' and 'upload_history' worksheets exist in the spreadsheet.")
            st.stop()
        except gspread.exceptions.APIError as e:
            st.error(f"Google Sheets API error: {e}")
            if attempt < max_retries - 1:
                st.warning(f"Retrying... ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                st.error("Max retries reached. Please check your Google Sheets setup.")
                st.stop()
        except Exception as e:
            st.error(f"Failed to connect to Google Sheets: {e}")
            if attempt < max_retries - 1:
                st.warning(f"Retrying... ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                st.error("Max retries reached. Unable to connect to Google Sheets.")
                st.stop()

auth_sheet, history_sheet = connect_to_google_sheets()

ADMIN_USERNAME = "manideep"

# ==================== AUTH FUNCTIONS ====================
@st.cache_data
def get_users():
    try:
        return auth_sheet.get_all_records()
    except gspread.exceptions.APIError as e:
        st.error(f"Failed to fetch users: {e}")
        return []

def find_user(username):
    users = get_users()
    for user in users:
        if user['username'] == username:
            return user
    return None

def add_user(username, password):
    try:
        if not username or not password:
            raise ValueError("Username and password cannot be empty")
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        auth_sheet.append_row([username, hashed_pw])
        return True
    except gspread.exceptions.APIError as e:
        st.error(f"Failed to add user: {e}")
        return False
    except ValueError as e:
        st.error(str(e))
        return False

def authenticate(username, password):
    user = find_user(username)
    if user and bcrypt.checkpw(password.encode(), user['password'].encode()):
        return True
    return False

def save_upload_history(username, filename):
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_sheet.append_row([username, filename, timestamp])
    except gspread.exceptions.APIError as e:
        st.warning(f"Failed to save upload history: {e}")

@st.cache_data
def get_upload_history():
    try:
        return history_sheet.get_all_records()
    except gspread.exceptions.APIError as e:
        st.error(f"Failed to fetch upload history: {e}")
        return []

# ==================== SUMMARIZATION ====================
def summarize_csv(df, token):
    text = df.to_csv(index=False)
    payload = {"inputs": text}
    headers = {"Authorization": f"Bearer {token}"}
    api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()[0]['summary_text']
    except (requests.RequestException, KeyError, IndexError) as e:
        st.warning(f"Summary could not be generated: {e}")
        return "Summary could not be generated."

# ==================== CHART GENERATION ====================
def generate_charts(df):
    charts = {}
    numeric_df = df.select_dtypes(include=['number']).dropna(axis=1, how='all')

    if numeric_df.shape[1] < 1:
        st.warning("No numeric columns found for chart generation.")
        return charts

    # Scatter plot
    if numeric_df.shape[1] >= 2:
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        sns.scatterplot(data=numeric_df, x=numeric_df.columns[0], y=numeric_df.columns[1], ax=ax1)
        ax1.set_title("Scatter Plot")
        ax1.set_xlabel(numeric_df.columns[0])
        ax1.set_ylabel(numeric_df.columns[1])
        charts["Scatter Plot"] = fig1

    # Line plot
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    numeric_df.plot(ax=ax2)
    ax2.set_title("Line Plot")
    charts["Line Plot"] = fig2

    # Histogram
    fig3, ax3 = plt.subplots(figsize=(6, 4))
    numeric_df.hist(ax=ax3)
    plt.tight_layout()
    charts["Histogram"] = fig3

    # Box plot
    fig4, ax4 = plt.subplots(figsize=(6, 4))
    sns.boxplot(data=numeric_df, ax=ax4)
    ax4.set_title("Box Plot")
    charts["Box Plot"] = fig4

    # Heatmap
    fig5, ax5 = plt.subplots(figsize=(6, 4))
    sns.heatmap(numeric_df.corr(), annot=True, cmap="coolwarm", ax=ax5)
    ax5.set_title("Correlation Heatmap")
    charts["Heatmap"] = fig5

    # Pie chart
    cat_df = df.select_dtypes(include=['object'])
    if not cat_df.empty:
        col = cat_df.columns[0]
        pie_data = df[col].value_counts()
        fig6, ax6 = plt.subplots(figsize=(6, 4))
        ax6.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
        ax6.axis('equal')
        ax6.set_title(f"Pie Chart of {col}")
        charts["Pie Chart"] = fig6

    return charts

# ==================== PPT EXPORT ====================
def export_to_ppt(charts, summary):
    prs = Presentation()
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    slide.shapes.title.text = "Data Analysis Report"
    slide.placeholders[1].text = f"Generated via Streamlit on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    if summary and summary != "Summary could not be generated.":
        bullet_slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(bullet_slide_layout)
        slide.shapes.title.text = "CSV Summary"
        content = slide.placeholders[1].text_frame
        content.text = summary

    for title, fig in charts.items():
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = title
        img_stream = io.BytesIO()
        fig.savefig(img_stream, format='png', bbox_inches='tight', dpi=150)
        img_stream.seek(0)
        slide.shapes.add_picture(img_stream, Inches(1), Inches(1.5), width=Inches(8))
        plt.close(fig)

    ppt_stream = io.BytesIO()
    prs.save(ppt_stream)
    ppt_stream.seek(0)
    return ppt_stream

# ==================== MAIN APP ====================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    if not st.session_state.logged_in:
        st.title("🔐 Login or Signup")
        tab1, tab2 = st.tabs(["Login", "Signup"])
        with tab1:
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                if authenticate(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        with tab2:
            new_username = st.text_input("New Username", key="signup_username")
            new_password = st.text_input("New Password", type="password", key="signup_password")
            if st.button("Signup"):
                if find_user(new_username):
                    st.error("Username already exists")
                elif add_user(new_username, new_password):
                    st.success("User created! Please login.")
        return

    st.sidebar.header("⚙️ Admin Panel")
    st.sidebar.markdown(f"Logged in as: <span style='color:lime'>{st.session_state.username}</span>", unsafe_allow_html=True)
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.subheader("📊 Uploaded Data")
            st.dataframe(df, use_container_width=True)
            st.write("Column types:", df.dtypes)

            save_upload_history(st.session_state.username, uploaded_file.name)

            st.subheader("🔍 Filter Data")
            filter_col = st.selectbox("Select column to search/filter", df.columns)
            search_val = st.text_input("Enter search keyword")
            if search_val:
                filtered_df = df[df[filter_col].astype(str).str.contains(search_val, case=False, na=False)]
                st.dataframe(filtered_df, use_container_width=True)
            else:
                filtered_df = df

            st.subheader("📈 Chart Builder")
            all_charts = generate_charts(df)
            chart_options = list(all_charts.keys())
            selected_charts = st.multiselect(
                "Select charts to view in app (all charts will be in PPT)",
                chart_options,
                default=chart_options[:2] if chart_options else []
            )

            if selected_charts:
                cols = st.columns(2)
                for i, chart in enumerate(selected_charts):
                    with cols[i % 2]:
                        st.pyplot(all_charts[chart])

            try:
                token = st.secrets["hugging_face"]["token"]
                summary = summarize_csv(df, token)
                if summary and summary != "Summary could not be generated.":
                    st.subheader("📝 CSV Summary")
                    st.write(summary)
            except KeyError:
                st.error("Hugging Face token not found in secrets. Please add it to secrets.toml.")
                summary = None

            if st.button("Export to PPT"):
                if not all_charts and not summary:
                    st.warning("No charts or summary to export.")
                else:
                    ppt_stream = export_to_ppt(all_charts, summary)
                    st.download_button(
                        "Download PPT",
                        ppt_stream,
                        file_name="data_analysis_report.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )

        except pd.errors.ParserError:
            st.error("Invalid CSV format. Please upload a valid CSV file.")
        except Exception as e:
            st.error(f"Error processing CSV: {e}")

    if st.session_state.username == ADMIN_USERNAME:
        st.subheader("📁 Upload History")
        history = get_upload_history()
        if history:
            st.dataframe(pd.DataFrame(history), use_container_width=True)
        else:
            st.info("No upload history available.")

if __name__ == "__main__":
    main()

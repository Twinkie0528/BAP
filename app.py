"""
Central Planning Platform (CPP) - Main Application
=================================================

This is the main entry point for the Streamlit application.
Run with: streamlit run app.py

Author: CPP Development Team
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="Төсвийн Автоматжуулалтын Платформ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom font styling - Montserrat
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Montserrat', sans-serif;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Montserrat', sans-serif;
    font-weight: 600;
}

.stButton button {
    font-family: 'Montserrat', sans-serif;
}

.stTextInput input, .stSelectbox select, .stTextArea textarea {
    font-family: 'Montserrat', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# Import our modules
from config import APP_NAME, APP_VERSION, BudgetType, FileStatus
from database import init_db, check_database_connection, seed_demo_users, User, BudgetFile, BudgetItem
from modules.excel_handler import (
    process_uploaded_file,
    validate_dataframe,
    get_file_preview,
    dataframe_to_budget_items
)
from modules.services import (
    create_budget_file,
    create_budget_items_bulk,
    get_budget_files_by_status,
    get_workflow_status_counts,
    get_budget_summary_by_channel
)
# JWT Authentication
from modules.jwt_auth import (
    init_jwt_session,
    is_authenticated,
    get_current_user_from_token,
    login_with_jwt,
    logout_jwt,
    authenticate_user_jwt,
    register_user,
    validate_email_domain,
    ALLOWED_EMAIL_DOMAINS
)
# Legacy auth (for backward compatibility)
from modules.auth import init_session_state, require_auth, logout_user, get_current_user


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

@st.cache_resource
def initialize_database():
    """Initialize database and seed demo users (runs once)."""
    init_db()
    seed_demo_users()
    return True


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""
    
    # Initialize database
    initialize_database()
    
    # Initialize session states
    init_session_state()
    init_jwt_session()
    
    # Check if user is authenticated (JWT)
    jwt_user = get_current_user_from_token()
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50?text=BAP+Logo", width=150)
        st.title(APP_NAME)
        st.caption(f"Version {APP_VERSION}")
        
        st.divider()
        
        # Check database connection
        if check_database_connection():
            st.success("🟢 Database Connected")
        else:
            st.error("🔴 Database Error")
        
        st.divider()
        
        # User info (if logged in with JWT)
        if jwt_user:
            st.write(f"👤 **{jwt_user.get('full_name') or jwt_user.get('username')}**")
            st.caption(f"📧 {jwt_user.get('email', '')}")
            role_display = jwt_user.get('role', 'unknown').title()
            role_emoji = {"Admin": "👑", "Manager": "👔", "Planner": "📋"}.get(role_display, "👤")
            st.caption(f"{role_emoji} {role_display}")
            
            if st.button("🚪 Гарах", width='stretch'):
                logout_jwt()
                st.rerun()
        else:
            st.info("🔐 Нэвтрээгүй байна")
    
    # Main content
    show_home_page(jwt_user)


# =============================================================================
# HOME PAGE
# =============================================================================

def show_home_page(jwt_user=None):
    """Display the home page with login/register or dashboard."""
    
    # If not authenticated, show login/register
    if not jwt_user:
        show_auth_page()
        return
    
    # User is authenticated - show main content
    st.title("📊 Төсвийн Автоматжуулалтын Платформ (BAP)")
    st.markdown(f"**Тавтай морил, {jwt_user.get('full_name', jwt_user.get('username'))}!** 👋")
    
    st.divider()
    
    # Workflow status cards
    st.header("📈 Одоогийн Байдал")
    
    try:
        status_counts = get_workflow_status_counts()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            count = status_counts.get('pending_approval', 0)
            st.metric("⏳ Хүлээгдэж байгаа", count)
        with col2:
            count = status_counts.get('approved_for_print', 0)
            st.metric("✅ Батлагдсан", count)
        with col3:
            count = status_counts.get('signing', 0)
            st.metric("🖨️ Гарын үсэг зурах", count)
        with col4:
            count = status_counts.get('finalized', 0)
            st.metric("🎯 Эцэслэсэн", count)
            
    except Exception as e:
        st.info("Өгөгдөл хараахан байхгүй байна. Төсвийн файл хуулж эхлээрэй!")
    
    st.divider()
    
    # Quick Actions
    st.header("🚀 Хурдан үйлдлүүд")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.page_link("pages/2_📤_Upload.py", label="📤 Төсөв оруулах", icon="📤")
        st.caption("Шинэ төсвийн файлуудыг оруулж ажлын урсгалыг эхлүүлэх")
        
    with col2:
        st.page_link("pages/1_🔄_Workflow.py", label="🔄 Ажлын урсгал удирдах", icon="🔄")
        st.caption("Хянах, батлах, эцэслэх")
        
    with col3:
        st.page_link("pages/3_📊_Dashboard.py", label="📊 Самбар харах", icon="📊")
        st.caption("Эцэслэсэн төсвүүдийг шинжилгээтэйгээр харах")
    
    # Show admin link if admin
    if jwt_user.get('role', '').lower() == 'admin':
        st.divider()
        st.header("👑 Админ")
        st.page_link("pages/4_⚙️_Admin.py", label="⚙️ Хэрэглэгч удирдах", icon="⚙️")
        st.caption("Хэрэглэгчийн эрх, role удирдах")


# =============================================================================
# AUTHENTICATION PAGE (Login + Register)
# =============================================================================

def show_auth_page():
    """Show login and registration forms."""
    
    st.title("🔐 BAP - Нэвтрэх систем")
    st.markdown("**Төсвийн Автоматжуулалтын Платформ**")
    
    st.divider()
    
    # Two tabs: Login and Register
    tab_login, tab_register = st.tabs(["🔑 Нэвтрэх", "📝 Бүртгүүлэх"])
    
    # =========================================================================
    # LOGIN TAB
    # =========================================================================
    with tab_login:
        st.subheader("Нэвтрэх")
        
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input(
                "📧 Email",
                placeholder="username@unitel.mn",
                help="Unitel-ийн email хаягаа оруулна уу"
            )
            password = st.text_input(
                "🔑 Нууц үг",
                type="password",
                placeholder="••••••••"
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                login_submitted = st.form_submit_button("🔓 Нэвтрэх", type="primary", width='stretch')
            
            if login_submitted:
                if not email or not password:
                    st.error("Email болон нууц үг оруулна уу")
                else:
                    user = authenticate_user_jwt(email, password)
                    
                    if user:
                        login_with_jwt(user)
                        st.success(f"✅ Тавтай морил, {user.full_name or user.username}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Email эсвэл нууц үг буруу байна")
        
        st.divider()
        
        # Demo credentials info
        with st.expander("ℹ️ Туршилтын эрхүүд"):
            st.markdown("""
            **Admin эрх:**
            - `admin1@unitel.mn` / `Admin123!`
            - `admin2@unitel.mn` / `Admin123!`
            - `admin3@unitel.mn` / `Admin123!`
            
            **Хуучин туршилт:**
            - `admin` / `admin123`
            - `manager` / `manager123`
            - `planner` / `planner123`
            """)
    
    # =========================================================================
    # REGISTER TAB
    # =========================================================================
    with tab_register:
        st.subheader("Шинээр бүртгүүлэх")
        
        st.info(f"⚠️ Зөвхөн **@{', @'.join(ALLOWED_EMAIL_DOMAINS)}** email бүртгүүлэх боломжтой!")
        
        with st.form("register_form", clear_on_submit=True):
            reg_full_name = st.text_input(
                "👤 Нэр",
                placeholder="Таны бүтэн нэр",
                help="Жишээ: Болдбаатар Батсүх"
            )
            reg_email = st.text_input(
                "📧 Email",
                placeholder="username@unitel.mn",
                help="Unitel-ийн email хаягаа оруулна уу"
            )
            reg_password = st.text_input(
                "🔑 Нууц үг",
                type="password",
                placeholder="Хамгийн багадаа 6 тэмдэгт",
                help="Хамгийн багадаа 6 тэмдэгт"
            )
            reg_password_confirm = st.text_input(
                "🔑 Нууц үг давтах",
                type="password",
                placeholder="Нууц үгээ давтан оруулна уу"
            )
            
            register_submitted = st.form_submit_button("📝 Бүртгүүлэх", type="primary", width='stretch')
            
            if register_submitted:
                # Validate inputs
                if not reg_full_name or not reg_email or not reg_password:
                    st.error("Бүх талбарыг бөглөнө үү")
                elif reg_password != reg_password_confirm:
                    st.error("Нууц үг таарахгүй байна")
                elif len(reg_password) < 6:
                    st.error("Нууц үг хамгийн багадаа 6 тэмдэгт байх ёстой")
                else:
                    # Attempt registration
                    success, message = register_user(reg_email, reg_password, reg_full_name)
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.info("👆 'Нэвтрэх' tab дээр дарж нэвтэрнэ үү")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")
        
        st.divider()
        
        st.markdown("""
        **📋 Бүртгүүлсний дараа:**
        - Та автоматаар **Planner** эрхтэй болно
        - **Admin** хэрэглэгч таны эрхийг **Manager** эсвэл **Admin** болгож өөрчилж болно
        """)


# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == "__main__":
    main()

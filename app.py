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

# Import our modules
from config import APP_NAME, APP_VERSION, ChannelType, FileStatus
from database.connection import init_db, check_database_connection, seed_demo_users
from database.models import User, BudgetFile, BudgetItem
from modules.excel_handler import (
    process_uploaded_file,
    validate_dataframe,
    get_file_preview,
    detect_channel_from_filename,
    dataframe_to_budget_items
)
from modules.services import (
    create_budget_file,
    create_budget_items_bulk,
    get_budget_files_by_status,
    get_workflow_status_counts,
    get_budget_summary_by_channel
)
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
    
    # Initialize session state
    init_session_state()
    
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
        
        # User info (if logged in)
        if st.session_state.get('authenticated'):
            user = get_current_user()
            st.write(f"👤 **{user.full_name or user.username}**")
            st.caption(f"Role: {user.role.value.title()}")
            if st.button("Logout"):
                logout_user()
                st.rerun()
        else:
            st.warning("Not logged in")
            if st.button("Login"):
                st.session_state['show_login'] = True
                st.rerun()
    
    # Main content
    show_home_page()


# =============================================================================
# HOME PAGE
# =============================================================================

def show_home_page():
    """Display the home page with workflow status."""
    
    # Check if login dialog should be shown
    if st.session_state.get('show_login', False):
        show_login_form()
        return
    
    st.title("📊 Төсвийн Автоматжуулалтын Платформ (BAP)")
    st.markdown("**Excel дээр суурилсан төсвийн төлөвлөлтийг 4 үе шаттай ажлын урсгалд шилжүүлэх.**")
    
    st.divider()
    
    # 4-Stage Workflow Explanation
    st.header("🔄 4 Үе Шаттай Ажлын Урсгал")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Хэрхэн ажилладаг:
        
        **1-р үе шат: 📤 БАТЛАХ ХҮЛЭЭЛТ (Хуулах)**
        - Төлөвлөгч Excel/CSV төсвийн файл хуулна
        - Өгөгдөл мэдээллийн санд хадгалагдана
        - ⚠️ **Үндсэн самбар дээр хараахан харагдахгүй**
        
        **2-р үе шат: ✅ ХЭВЛЭХЭД БЭЛЭН (Менежерийн хянан шалгах)**
        - Менежер хүлээгдэж буй файлыг хянана
        - Менежер "Батлах" товчийг дарна
        - Төлөвлөгч PDF хураангуй үүсгэж болно
        
        **3-р үе шат: 🖨️ ГАРЫН ҮСЭГ ЗУРАХ (Шууд процесс)**
        - Төлөвлөгч системээс үүссэн PDF-г татаж авна
        - Төлөвлөгч үүнийг хэвлэж гарын үсэг/тамга авна
        - Төлөвлөгч гарын үсэгтэй баримтыг скан хийнэ
        
        **4-р үе шат: 🎯 ЭЦЭСЛЭСЭН (Архивлах)**
        - Төлөвлөгч гарын үсэгтэй сканыг хуулна (дискэнд хадгалагдана, ӨС-д биш)
        - Хэрэглэгч "Эцэслэх" товчийг дарна
        - ✅ **ОДОО өгөгдөл Үндсэн Шинжилгээний Самбар дээр гарч ирнэ**
        """)
    
    with col2:
        st.info("""
        **Гол дүрмүүд:**
        
        ✅ Зөвхөн ЭЦЭСЛЭСЭН өгөгдөл самбар дээр харагдана
        
        ✅ Мөрийн түвшний аюулгүй байдал: Хэрэглэгчид зөвхөн өөрийнхөө мөрийг засаж болно
        
        ✅ Гарын үсэгтэй баримтууд дискэнд хадгалагдана (мэдээллийн санд биш)
        
        ✅ Дагаж мөрдөх бүрэн аудитын мөр
        """)
    
    st.divider()
    
    # Workflow status cards (if user is logged in)
    if st.session_state.get('authenticated'):
        st.header("📈 Одоогийн Байдал")
        
        try:
            status_counts = get_workflow_status_counts()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                count = status_counts.get('pending_approval', 0)
                st.metric("⏳ Батлах хүлээлт", count)
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
        st.page_link("pages/2_📤_Upload.py", label="📤 Төсвийн файл хуулах", icon="📤")
        st.caption("Шинэ төсвийн файлуудыг хуулж ажлын урсгалыг эхлүүлэх")
        
    with col2:
        st.page_link("pages/1_🔄_Workflow.py", label="🔄 Ажлын урсгал удирдах", icon="🔄")
        st.caption("Хянах, батлах, эцэслэх")
        
    with col3:
        st.page_link("pages/3_📊_Dashboard.py", label="📊 Самбар харах", icon="📊")
        st.caption("Эцэслэсэн төсвүүдийг шинжилгээтэйгээр харах")


def show_login_form():
    """Show login form."""
    
    st.title("🔐 Нэвтрэх")
    
    with st.form("login_form"):
        username = st.text_input("Хэрэглэгчийн нэр")
        password = st.text_input("Нууц үг", type="password")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("Нэвтрэх", type="primary")
        
        with col2:
            cancel = st.form_submit_button("Цуцлах")
        
        if submitted:
            from modules.auth import authenticate_user, login_user
            user = authenticate_user(username, password)
            
            if user:
                login_user(user)
                st.success(f"Тавтай морил, {user.full_name or user.username}!")
                del st.session_state['show_login']
                st.rerun()
            else:
                st.error("❌ Хэрэглэгчийн нэр эсвэл нууц үг буруу байна")
        
        if cancel:
            del st.session_state['show_login']
            st.rerun()
    
    st.divider()
    st.info("""
    **Туршилтын эрх:**
    - `admin` / `admin123` (Админ)
    - `manager` / `manager123` (Менежер)
    - `planner` / `planner123` (Төлөвлөгч)
    """)


# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == "__main__":
    main()

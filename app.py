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
    page_title="Central Planning Platform",
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


# =============================================================================
# HOME PAGE
# =============================================================================

def show_home_page():
    """Display the home page with workflow status."""
    
    # Check if login dialog should be shown
    if st.session_state.get('show_login', False):
        show_login_form()
        return
    
    st.title("📊 Budget Automation Platform (BAP)")
    st.markdown("**Transform your Excel-based budget planning into a streamlined 4-stage workflow.**")
    
    st.divider()
    
    # 4-Stage Workflow Explanation
    st.header("🔄 The 4-Stage Workflow")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### How It Works:
        
        **Stage 1: 📤 PENDING_APPROVAL (Upload)**
        - Planner uploads Excel/CSV budget file
        - Data is saved to database
        - ⚠️ **NOT visible on Main Dashboard yet**
        
        **Stage 2: ✅ APPROVED_FOR_PRINT (Manager Review)**
        - Manager reviews the pending file
        - Manager clicks "Approve" button
        - Planner can now generate a PDF summary
        
        **Stage 3: 🖨️ SIGNING (Offline Process)**
        - Planner downloads the system-generated PDF
        - Planner prints it and gets physical signatures/stamps
        - Planner scans the signed document
        
        **Stage 4: 🎯 FINALIZED (Archiving)**
        - Planner uploads the signed scan (stored on disk, not in DB)
        - User clicks "Finalize" button
        - ✅ **NOW data appears on the Main Analytics Dashboard**
        """)
    
    with col2:
        st.info("""
        **Key Rules:**
        
        ✅ Only FINALIZED data is visible on dashboard
        
        ✅ Row-level security: Users can only edit their own rows
        
        ✅ Signed documents stored on disk (not in database)
        
        ✅ Complete audit trail for compliance
        """)
    
    st.divider()
    
    # Workflow status cards (if user is logged in)
    if st.session_state.get('authenticated'):
        st.header("📈 Current Status")
        
        try:
            status_counts = get_workflow_status_counts()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                count = status_counts.get('pending_approval', 0)
                st.metric("⏳ Pending Approval", count)
            with col2:
                count = status_counts.get('approved_for_print', 0)
                st.metric("✅ Approved", count)
            with col3:
                count = status_counts.get('signing', 0)
                st.metric("🖨️ Signing", count)
            with col4:
                count = status_counts.get('finalized', 0)
                st.metric("🎯 Finalized", count)
                
        except Exception as e:
            st.info("No data yet. Start by uploading a budget file!")
        
        st.divider()
    
    # Quick Actions
    st.header("🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.page_link("pages/2_📤_Upload.py", label="📤 Upload Budget File", icon="📤")
        st.caption("Upload new budget files to start the workflow")
        
    with col2:
        st.page_link("pages/1_🔄_Workflow.py", label="🔄 Manage Workflow", icon="🔄")
        st.caption("Review, approve, and finalize budgets")
        
    with col3:
        st.page_link("pages/3_📊_Dashboard.py", label="📊 View Dashboard", icon="📊")
        st.caption("View finalized budgets with analytics")


def show_login_form():
    """Show login form."""
    
    st.title("🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("Login", type="primary")
        
        with col2:
            cancel = st.form_submit_button("Cancel")
        
        if submitted:
            from modules.auth import authenticate_user, login_user
            user = authenticate_user(username, password)
            
            if user:
                login_user(user)
                st.success(f"Welcome, {user.full_name or user.username}!")
                del st.session_state['show_login']
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
        
        if cancel:
            del st.session_state['show_login']
            st.rerun()
    
    st.divider()
    st.info("""
    **Demo Credentials:**
    - `admin` / `admin123` (Admin)
    - `manager` / `manager123` (Manager)
    - `planner` / `planner123` (Planner)
    """)


# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == "__main__":
    main()

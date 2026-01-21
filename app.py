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
        st.image("https://via.placeholder.com/150x50?text=CPP+Logo", width=150)
        st.title(APP_NAME)
        st.caption(f"Version {APP_VERSION}")
        
        st.divider()
        
        # Check database connection
        if check_database_connection():
            st.success("🟢 Database Connected")
        else:
            st.error("🔴 Database Error")
        
        st.divider()
        
        # Navigation
        page = st.selectbox(
            "Navigate to:",
            ["🏠 Home", "📤 Upload File", "🔧 Test Components", "📊 Dashboard Preview"]
        )
        
        # User info (if logged in)
        if st.session_state.get('authenticated'):
            st.divider()
            user = get_current_user()
            st.write(f"👤 **{user.full_name or user.username}**")
            st.caption(f"Role: {user.role.value.title()}")
            if st.button("Logout"):
                logout_user()
                st.rerun()
    
    # Main content based on navigation
    if page == "🏠 Home":
        show_home_page()
    elif page == "📤 Upload File":
        show_upload_page()
    elif page == "🔧 Test Components":
        show_test_page()
    elif page == "📊 Dashboard Preview":
        show_dashboard_preview()


# =============================================================================
# HOME PAGE
# =============================================================================

def show_home_page():
    """Display the home page with workflow status."""
    
    st.title("📊 Central Planning Platform")
    st.markdown("Transform your Excel-based budget planning into a streamlined workflow.")
    
    # Workflow status cards
    st.subheader("📈 Workflow Overview")
    
    try:
        status_counts = get_workflow_status_counts()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("📝 Draft", status_counts.get('draft', 0))
        with col2:
            st.metric("⏳ Pending", status_counts.get('pending', 0))
        with col3:
            st.metric("✅ Approved", status_counts.get('approved', 0))
        with col4:
            st.metric("❌ Rejected", status_counts.get('rejected', 0))
        with col5:
            st.metric("📊 Published", status_counts.get('published', 0))
            
    except Exception as e:
        st.info("No data yet. Start by uploading a budget file!")
    
    # Quick actions
    st.divider()
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("**📤 Upload**\nUpload new budget files")
        
    with col2:
        st.warning("**📋 Review**\nReview pending submissions")
        
    with col3:
        st.success("**📊 Dashboard**\nView budget analytics")
    
    # Workflow explanation
    st.divider()
    st.subheader("📋 Workflow Process")
    
    st.markdown("""
    ```
    1. UPLOAD     →  Planner uploads Excel file
    2. DRAFT      →  File saved, can be edited
    3. SUBMIT     →  Planner submits for review
    4. PENDING    →  Manager reviews submission
    5. APPROVE    →  Manager approves OR
    6. REJECT     →  Manager rejects with comments
    7. PUBLISH    →  Approved files go to dashboard
    ```
    """)


# =============================================================================
# UPLOAD PAGE
# =============================================================================

def show_upload_page():
    """File upload page with preview and processing."""
    
    st.title("📤 Upload Budget File")
    
    # Channel selection
    col1, col2 = st.columns([1, 2])
    
    with col1:
        channel_options = [ch.value for ch in ChannelType]
        selected_channel = st.selectbox(
            "Select Channel Type",
            channel_options,
            help="Select the marketing channel for this budget file"
        )
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose Excel or CSV file",
        type=['xlsx', 'xls', 'csv'],
        help="Upload your budget planning file"
    )
    
    if uploaded_file:
        # Auto-detect channel from filename
        detected = detect_channel_from_filename(uploaded_file.name)
        if detected and detected != selected_channel:
            st.info(f"💡 Detected channel from filename: **{detected}**")
        
        st.divider()
        st.subheader("📋 File Preview")
        
        # Show preview
        preview_df, _ = get_file_preview(uploaded_file, max_rows=10)
        if not preview_df.empty:
            st.dataframe(preview_df, use_container_width=True)
        
        # Process button
        st.divider()
        if st.button("🔄 Process File", type="primary"):
            with st.spinner("Processing file..."):
                # Process the file
                df, metadata, errors = process_uploaded_file(
                    uploaded_file,
                    selected_channel
                )
                
                if df is not None:
                    st.success(f"✅ Successfully processed {metadata['row_count']} rows!")
                    
                    # Show metadata
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Rows", metadata['row_count'])
                    with col2:
                        total = metadata['total_amount']
                        st.metric("Total Budget", f"₮{total:,.0f}" if total else "N/A")
                    with col3:
                        st.metric("Header Row", metadata['header_row'])
                    
                    # Show validation issues
                    validation_issues = validate_dataframe(df)
                    if validation_issues:
                        st.warning("⚠️ Validation Notes:")
                        for issue in validation_issues:
                            st.write(f"  • {issue}")
                    
                    # Show processed data
                    st.subheader("📊 Processed Data")
                    st.dataframe(df, use_container_width=True)
                    
                    # Store in session for saving
                    st.session_state['processed_df'] = df
                    st.session_state['processed_metadata'] = metadata
                    
                else:
                    st.error("❌ Failed to process file")
                    for error in errors:
                        st.write(f"  • {error}")
        
        # Save button (if data is processed)
        if 'processed_df' in st.session_state:
            st.divider()
            if st.button("💾 Save to Database", type="secondary"):
                # For demo, use a placeholder user ID
                st.info("💡 In production, this would use the logged-in user's ID")
                st.success("File would be saved here!")


# =============================================================================
# TEST PAGE
# =============================================================================

def show_test_page():
    """Page for testing individual components."""
    
    st.title("🔧 Component Testing")
    st.markdown("Test individual components of the platform.")
    
    # Test sections
    tab1, tab2, tab3 = st.tabs(["Database", "Column Mapping", "Authentication"])
    
    with tab1:
        st.subheader("Database Tests")
        
        if st.button("Test Database Connection"):
            if check_database_connection():
                st.success("✅ Database connection successful!")
            else:
                st.error("❌ Database connection failed!")
        
        if st.button("Show Table Info"):
            from database.connection import get_database_info
            info = get_database_info()
            st.json(info)
    
    with tab2:
        st.subheader("Column Mapping Test")
        
        st.markdown("Enter column names to see how they would be mapped:")
        
        test_columns = st.text_area(
            "Enter column names (one per line)",
            value="Төсвийн код\nКампанит ажил\nНийт дүн\nКомпани\nХугацаа"
        )
        
        if st.button("Test Mapping"):
            from mappings.column_maps import COMMON_COLUMN_MAP, TV_COLUMN_MAP
            
            columns = [c.strip() for c in test_columns.split('\n') if c.strip()]
            
            st.write("**Mapping Results:**")
            for col in columns:
                col_lower = col.lower().strip()
                mapped = None
                
                # Check common mappings
                for pattern, target in COMMON_COLUMN_MAP.items():
                    if pattern in col_lower or col_lower in pattern:
                        mapped = target
                        break
                
                # Check TV-specific if not found
                if not mapped:
                    for pattern, target in TV_COLUMN_MAP.items():
                        if pattern in col_lower or col_lower in pattern:
                            mapped = target
                            break
                
                if mapped:
                    st.write(f"  ✅ `{col}` → `{mapped}`")
                else:
                    st.write(f"  ⚠️ `{col}` → *(no mapping)*")
    
    with tab3:
        st.subheader("Authentication Test")
        
        st.markdown("""
        **Demo Credentials:**
        - `admin` / `admin123` (Admin)
        - `manager` / `manager123` (Manager)
        - `planner` / `planner123` (Planner)
        """)
        
        with st.form("test_login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Test Login"):
                from modules.auth import authenticate_user
                user = authenticate_user(username, password)
                
                if user:
                    st.success(f"✅ Login successful! User: {user.full_name}, Role: {user.role.value}")
                else:
                    st.error("❌ Invalid credentials")


# =============================================================================
# DASHBOARD PREVIEW
# =============================================================================

def show_dashboard_preview():
    """Preview of the dashboard with sample data."""
    
    st.title("📊 Dashboard Preview")
    st.markdown("This shows what the dashboard will look like with real data.")
    
    # Sample data for preview
    st.info("💡 This is sample data. Real data will appear after files are published.")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Budget by Channel")
        
        sample_data = pd.DataFrame({
            'Channel': ['TV', 'OOH', 'FM', 'Digital', 'Print'],
            'Budget': [500000000, 300000000, 150000000, 200000000, 100000000]
        })
        
        st.bar_chart(sample_data.set_index('Channel'))
    
    with col2:
        st.subheader("Monthly Trend")
        
        trend_data = pd.DataFrame({
            'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'Budget': [200000000, 250000000, 180000000, 300000000, 280000000, 320000000]
        })
        
        st.line_chart(trend_data.set_index('Month'))
    
    # Summary metrics
    st.divider()
    st.subheader("📈 Summary Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Budget", "₮1.25B", "+12%")
    with col2:
        st.metric("Active Campaigns", "47", "+5")
    with col3:
        st.metric("Vendors", "23", "0")
    with col4:
        st.metric("Channels", "5", "0")


# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == "__main__":
    main()

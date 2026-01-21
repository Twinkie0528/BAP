"""
Budget File Upload Page
========================

Upload Excel/CSV budget files and process them.
Files start at Stage 1 (PENDING_APPROVAL) in the workflow.

Author: CPP Development Team
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Upload Budget",
    page_icon="📤",
    layout="wide"
)

# Import our modules
import sys
sys.path.append('..')
from config import ChannelType, FileStatus
from database.connection import get_session
from database.models import User, BudgetFile, BudgetItem
from modules.auth import init_session_state, get_current_user, require_auth
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
    check_duplicate_file
)


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    """Main upload page."""
    
    # Initialize session
    init_session_state()
    
    # Check authentication
    if not require_auth():
        st.stop()
    
    # Get current user
    user = get_current_user()
    if not user:
        st.error("User not found. Please log in again.")
        st.stop()
    
    # Page header
    st.title("📤 Upload Budget File")
    st.markdown(f"Welcome, **{user.full_name or user.username}**")
    st.info("📋 Files uploaded here will enter **Stage 1: PENDING_APPROVAL** and await manager review.")
    
    st.divider()
    
    # Upload form
    with st.form("upload_form", clear_on_submit=False):
        
        # Channel selection
        col1, col2 = st.columns([1, 2])
        
        with col1:
            channel_options = [ch.value for ch in ChannelType]
            selected_channel = st.selectbox(
                "Select Channel Type*",
                channel_options,
                help="Select the marketing channel for this budget file"
            )
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose Excel or CSV file*",
            type=['xlsx', 'xls', 'csv'],
            help="Upload your budget planning file"
        )
        
        # Show preview
        if uploaded_file:
            # Auto-detect channel from filename
            detected = detect_channel_from_filename(uploaded_file.name)
            if detected and detected != selected_channel:
                st.info(f"💡 Detected channel from filename: **{detected}**")
            
            st.subheader("📋 File Preview")
            
            # Show preview
            preview_df, _ = get_file_preview(uploaded_file, max_rows=10)
            if not preview_df.empty:
                st.dataframe(preview_df, use_container_width=True)
                st.caption(f"Preview of first rows. File will be fully processed on submit.")
        
        # Submit button
        submitted = st.form_submit_button("🚀 Process and Upload", type="primary")
    
    # Process form submission
    if submitted:
        if not uploaded_file:
            st.error("❌ Please select a file to upload")
            return
        
        process_and_save_file(uploaded_file, selected_channel, user)


# =============================================================================
# FILE PROCESSING
# =============================================================================

def process_and_save_file(uploaded_file, channel_type: str, user: User):
    """Process uploaded file and save to database."""
    
    with st.spinner("Processing file..."):
        
        # Process the file
        df, metadata, errors = process_uploaded_file(
            uploaded_file,
            channel_type
        )
        
        if df is None:
            st.error("❌ Failed to process file")
            for error in errors:
                st.error(f"  • {error}")
            return
        
        # Show processing results
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
            with st.expander("⚠️ Validation Notes (click to expand)"):
                for issue in validation_issues:
                    st.warning(f"  • {issue}")
        
        # Check for duplicates
        if metadata['file_hash']:
            existing = check_duplicate_file(metadata['file_hash'])
            if existing:
                st.error(f"❌ This file has already been uploaded (File ID: {existing.id})")
                st.warning("If you want to upload a modified version, please make a change to the file first.")
                return
        
        # Show processed data preview
        st.subheader("📊 Processed Data Preview")
        st.dataframe(df.head(20), use_container_width=True)
        
        if len(df) > 20:
            st.caption(f"Showing 20 of {len(df)} rows")
        
        st.divider()
        
        # Confirmation
        st.write("**Ready to save to database?**")
        st.info("💡 This will create a new budget file in **PENDING_APPROVAL** status. Managers will be able to review and approve it.")
        
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            if st.button("💾 Confirm & Save", type="primary"):
                save_to_database(df, metadata, channel_type, user)
        
        with col2:
            if st.button("❌ Cancel"):
                st.rerun()


def save_to_database(df: pd.DataFrame, metadata: dict, channel_type: str, user: User):
    """Save processed data to database."""
    
    with st.spinner("Saving to database..."):
        try:
            # Create BudgetFile record
            budget_file = create_budget_file(
                filename=metadata['filename'],
                channel_type=channel_type,
                uploader_id=user.id,
                row_count=metadata['row_count'],
                total_amount=metadata['total_amount'],
                file_hash=metadata['file_hash']
            )
            
            st.success(f"✅ Budget file created (ID: {budget_file.id})")
            
            # Convert DataFrame to BudgetItem dictionaries
            items = dataframe_to_budget_items(
                df,
                budget_file.id,
                channel_type,
                specialist_username=user.username  # Set specialist for row-level security
            )
            
            # Bulk insert items
            created_count = create_budget_items_bulk(items)
            
            st.success(f"✅ {created_count} budget items saved successfully!")
            
            # Show success message and next steps
            st.balloons()
            
            st.success("🎉 **Upload Complete!**")
            st.info(f"""
            **Next Steps:**
            1. ✅ Your file is now in **PENDING_APPROVAL** status
            2. 👔 A manager will review and approve your budget
            3. 🖨️ Once approved, you can generate a PDF for printing
            4. ✍️ Get physical signatures on the printed document
            5. 📤 Upload the signed scan to finalize
            6. 📊 After finalization, your budget will appear on the main dashboard
            """)
            
            # Link to workflow page
            st.page_link("pages/1_🔄_Workflow.py", label="➡️ Go to Workflow Page", icon="🔄")
            
            # Clear session state to allow new upload
            if st.button("Upload Another File"):
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Error saving to database: {str(e)}")
            import traceback
            with st.expander("Error details"):
                st.code(traceback.format_exc())


# =============================================================================
# RUN PAGE
# =============================================================================

if __name__ == "__main__":
    main()
else:
    main()

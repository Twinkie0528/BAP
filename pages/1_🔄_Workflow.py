"""
Budget Workflow Page - 4-Stage Process
======================================

Handles all 4 stages of the budget approval workflow:
Stage 1: PENDING_APPROVAL - Upload and awaiting manager review
Stage 2: APPROVED_FOR_PRINT - Generate PDF for printing
Stage 3: SIGNING - Upload signed document
Stage 4: FINALIZED - Complete (visible on dashboard)

Author: CPP Development Team
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="Budget Workflow",
    page_icon="🔄",
    layout="wide"
)

# Import our modules
import sys
sys.path.append('..')
from config import FileStatus, UserRole, ChannelType
from database.connection import get_session
from database.models import User, BudgetFile, BudgetItem
from modules.auth import init_session_state, get_current_user, require_auth
from modules.services import (
    get_files_pending_approval,
    get_files_approved_for_print,
    get_files_in_signing,
    update_budget_file_status,
    update_file_with_pdf,
    update_file_with_signed_document,
    get_budget_items_by_file
)
from modules.pdf_generator import generate_budget_pdf
from modules.file_storage import save_signed_document, ensure_storage_directories


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    """Main workflow page."""
    
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
    st.title("🔄 Budget Workflow Management")
    st.markdown(f"Welcome, **{user.full_name or user.username}** ({user.role.value})")
    
    # Ensure storage directories exist
    ensure_storage_directories()
    
    # Show different views based on role
    if user.role == UserRole.MANAGER:
        show_manager_view(user)
    elif user.role == UserRole.PLANNER:
        show_planner_view(user)
    elif user.role == UserRole.ADMIN:
        # Admins can see both views
        tab1, tab2 = st.tabs(["👔 Manager View", "👤 Planner View"])
        with tab1:
            show_manager_view(user)
        with tab2:
            show_planner_view(user)
    else:
        st.warning("Unknown role. Please contact administrator.")


# =============================================================================
# MANAGER VIEW - Stage 1: Approve files
# =============================================================================

def show_manager_view(user: User):
    """Show pending approvals for managers."""
    
    st.header("👔 Manager Dashboard - Pending Approvals")
    st.info("📋 **Stage 1: PENDING_APPROVAL** - Review and approve budget files")
    
    # Load pending files
    pending_files = get_files_pending_approval(limit=50)
    
    if not pending_files:
        st.success("✅ No files pending approval!")
        return
    
    st.write(f"**{len(pending_files)} file(s) awaiting your review:**")
    
    # Display each pending file
    for idx, file in enumerate(pending_files, 1):
        with st.expander(f"📄 {file.filename} - {file.channel_type.value} (ID: {file.id})", expanded=(idx == 1)):
            
            # File information
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Items", file.row_count)
            with col2:
                if file.total_amount:
                    st.metric("Total Budget", f"₮{float(file.total_amount):,.0f}")
                else:
                    st.metric("Total Budget", "N/A")
            with col3:
                uploader_name = file.uploader.full_name if file.uploader else "Unknown"
                st.write(f"**Uploaded by:** {uploader_name}")
                st.caption(f"Date: {file.uploaded_at.strftime('%Y-%m-%d %H:%M')}")
            
            # Show budget items
            st.subheader("📊 Budget Items Preview")
            items = get_budget_items_by_file(file.id)
            
            if items:
                items_data = []
                for item in items[:10]:  # Show first 10 items
                    items_data.append({
                        "Budget Code": item.budget_code,
                        "Campaign": item.campaign_name,
                        "Vendor": item.vendor or "N/A",
                        "Amount": f"₮{float(item.amount_planned):,.0f}" if item.amount_planned else "N/A",
                        "Start Date": item.start_date.strftime("%Y-%m-%d") if item.start_date else "N/A"
                    })
                
                df = pd.DataFrame(items_data)
                st.dataframe(df, use_container_width=True)
                
                if len(items) > 10:
                    st.caption(f"Showing 10 of {len(items)} items")
            else:
                st.warning("No items found in this file")
            
            # Action buttons
            st.divider()
            col1, col2, col3 = st.columns([1, 1, 3])
            
            with col1:
                if st.button(f"✅ Approve", key=f"approve_{file.id}", type="primary"):
                    result = update_budget_file_status(
                        file.id,
                        FileStatus.APPROVED_FOR_PRINT,
                        reviewer_id=user.id,
                        reviewer_comment="Approved by manager"
                    )
                    if result:
                        st.success(f"✅ File approved! Planner can now generate PDF.")
                        st.rerun()
                    else:
                        st.error("Failed to approve file")
            
            with col2:
                if st.button(f"❌ Reject", key=f"reject_{file.id}"):
                    st.session_state[f'show_reject_{file.id}'] = True
            
            # Rejection form
            if st.session_state.get(f'show_reject_{file.id}', False):
                with st.form(key=f"reject_form_{file.id}"):
                    reason = st.text_area("Rejection reason:", key=f"reason_{file.id}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Confirm Rejection"):
                            if reason.strip():
                                # For now, we move back to PENDING_APPROVAL with comment
                                # In a more complex system, you might have a REJECTED status
                                result = update_budget_file_status(
                                    file.id,
                                    FileStatus.PENDING_APPROVAL,
                                    reviewer_id=user.id,
                                    reviewer_comment=f"REJECTED: {reason}"
                                )
                                if result:
                                    st.error(f"❌ File rejected. Planner has been notified.")
                                    del st.session_state[f'show_reject_{file.id}']
                                    st.rerun()
                            else:
                                st.warning("Please provide a reason for rejection")
                    
                    with col2:
                        if st.form_submit_button("Cancel"):
                            del st.session_state[f'show_reject_{file.id}']
                            st.rerun()


# =============================================================================
# PLANNER VIEW - Stages 2 & 3
# =============================================================================

def show_planner_view(user: User):
    """Show workflow stages for planners."""
    
    st.header("👤 Planner Dashboard")
    
    # Create tabs for different stages
    tab1, tab2, tab3 = st.tabs([
        "⏳ Pending Approval",
        "🖨️ Ready for Print (Stage 2)",
        "✍️ Awaiting Signature (Stage 3)"
    ])
    
    with tab1:
        show_pending_files(user)
    
    with tab2:
        show_approved_files(user)
    
    with tab3:
        show_signing_files(user)


def show_pending_files(user: User):
    """Show files waiting for manager approval."""
    
    st.subheader("⏳ Files Awaiting Manager Approval")
    st.info("📋 **Stage 1: PENDING_APPROVAL** - Your files are being reviewed by managers")
    
    # Get user's pending files
    from modules.services import get_budget_files_by_uploader
    files = [f for f in get_budget_files_by_uploader(user.id) if f.status == FileStatus.PENDING_APPROVAL]
    
    if not files:
        st.success("✅ No files pending approval")
        return
    
    for file in files:
        with st.expander(f"📄 {file.filename} - Uploaded {file.uploaded_at.strftime('%Y-%m-%d')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Items", file.row_count)
            with col2:
                if file.total_amount:
                    st.metric("Total", f"₮{float(file.total_amount):,.0f}")
            
            if file.reviewer_comment and "REJECTED" in file.reviewer_comment:
                st.error(f"❌ Rejection reason: {file.reviewer_comment}")
                st.info("Please review the comments and upload a corrected file.")


def show_approved_files(user: User):
    """Show approved files ready for PDF generation (Stage 2)."""
    
    st.subheader("🖨️ Approved Files - Ready for Print")
    st.info("📋 **Stage 2: APPROVED_FOR_PRINT** - Generate PDF for printing and signatures")
    
    files = get_files_approved_for_print(user.id)
    
    if not files:
        st.success("✅ No files ready for printing")
        return
    
    for file in files:
        with st.expander(f"📄 {file.filename} (ID: {file.id})", expanded=True):
            
            # File info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Items", file.row_count)
            with col2:
                if file.total_amount:
                    st.metric("Total", f"₮{float(file.total_amount):,.0f}")
            with col3:
                st.write(f"**Approved:** {file.reviewed_at.strftime('%Y-%m-%d')}")
            
            if file.reviewer_comment:
                st.info(f"💬 Manager comment: {file.reviewer_comment}")
            
            st.divider()
            
            # PDF Generation
            if st.button(f"📄 Generate PDF for Printing", key=f"gen_pdf_{file.id}", type="primary"):
                with st.spinner("Generating PDF..."):
                    # Get budget items
                    items = get_budget_items_by_file(file.id)
                    
                    # Generate PDF
                    success, message, pdf_path = generate_budget_pdf(file, items)
                    
                    if success:
                        # Update database
                        update_file_with_pdf(file.id, pdf_path)
                        st.success("✅ PDF generated successfully!")
                        st.info("📝 Next steps:\n1. Download the PDF\n2. Print it\n3. Get physical signatures\n4. Scan the signed document\n5. Upload it back to the system")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
            
            # Show download button if PDF exists
            if file.pdf_file_path and os.path.exists(file.pdf_file_path):
                with open(file.pdf_file_path, "rb") as f:
                    pdf_data = f.read()
                
                st.download_button(
                    label="⬇️ Download Generated PDF",
                    data=pdf_data,
                    file_name=f"budget_approval_{file.id}.pdf",
                    mime="application/pdf",
                    key=f"download_{file.id}"
                )


def show_signing_files(user: User):
    """Show files awaiting signed document upload (Stage 3)."""
    
    st.subheader("✍️ Awaiting Signed Document")
    st.info("📋 **Stage 3: SIGNING** - Upload the scanned signed document to finalize")
    
    files = get_files_in_signing(user.id)
    
    if not files:
        st.success("✅ No files awaiting signature upload")
        return
    
    for file in files:
        with st.expander(f"📄 {file.filename} (ID: {file.id})", expanded=True):
            
            # File info
            st.write(f"**PDF Generated:** {file.pdf_generated_at.strftime('%Y-%m-%d %H:%M')}")
            st.write(f"**Items:** {file.row_count}")
            
            # Download PDF if needed
            if file.pdf_file_path and os.path.exists(file.pdf_file_path):
                with open(file.pdf_file_path, "rb") as f:
                    pdf_data = f.read()
                
                st.download_button(
                    label="⬇️ Re-download PDF",
                    data=pdf_data,
                    file_name=f"budget_approval_{file.id}.pdf",
                    mime="application/pdf",
                    key=f"redownload_{file.id}"
                )
            
            st.divider()
            st.write("**📤 Upload Signed Document:**")
            
            # Upload form
            uploaded_signed = st.file_uploader(
                "Choose scanned signed document (PDF, JPG, PNG)",
                type=['pdf', 'jpg', 'jpeg', 'png'],
                key=f"upload_signed_{file.id}"
            )
            
            if uploaded_signed:
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if st.button(f"✅ Finalize", key=f"finalize_{file.id}", type="primary"):
                        with st.spinner("Uploading and finalizing..."):
                            # Save signed document
                            success, file_path, message = save_signed_document(
                                uploaded_signed,
                                file.id,
                                user.username
                            )
                            
                            if success:
                                # Update database - move to FINALIZED
                                result = update_file_with_signed_document(file.id, file_path)
                                
                                if result:
                                    st.success("🎉 SUCCESS! Budget is now FINALIZED and visible on the dashboard!")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("Failed to update database")
                            else:
                                st.error(f"❌ {message}")
                
                with col2:
                    st.caption("This will move the budget to FINALIZED status and make it visible on the main dashboard.")


# =============================================================================
# RUN PAGE
# =============================================================================

if __name__ == "__main__":
    main()
else:
    main()

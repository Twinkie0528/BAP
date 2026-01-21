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
    page_title="Төсвийн ажлын урсгал",
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
        st.error("Хэрэглэгч олдсонгүй. Дахин нэвтэрнэ үү.")
        st.stop()
    
    # Page header
    st.title("🔄 Төсвийн ажлын урсгал удирдах")
    st.markdown(f"Тавтай морил, **{user.full_name or user.username}** ({user.role.value})")
    
    # Ensure storage directories exist
    ensure_storage_directories()
    
    # Show different views based on role
    if user.role == UserRole.MANAGER:
        show_manager_view(user)
    elif user.role == UserRole.PLANNER:
        show_planner_view(user)
    elif user.role == UserRole.ADMIN:
        # Admins can see both views
        tab1, tab2 = st.tabs(["👔 Менежерийн харах", "👤 Төлөвлөгчийн харах"])
        with tab1:
            show_manager_view(user)
        with tab2:
            show_planner_view(user)
    else:
        st.warning("Үүрэг тодорхойгүй байна. Админтай холбогдоно уу.")


# =============================================================================
# MANAGER VIEW - Stage 1: Approve files
# =============================================================================

def show_manager_view(user: User):
    """Show pending approvals for managers."""
    
    st.header("👔 Менежерийн самбар - Батлах хүлээлт")
    st.info("📋 **1-р үе шат: БАТЛАХ ХҮЛЭЭЛТ** - Төсвийн файлуудыг хянаж батлах")
    
    # Load pending files
    pending_files = get_files_pending_approval(limit=50)
    
    if not pending_files:
        st.success("✅ Батлах хүлээгдэж буй файл байхгүй байна!")
        return
    
    st.write(f"**Таны хянаж үзэх {len(pending_files)} файл байна:**")
    
    # Display each pending file
    for idx, file in enumerate(pending_files, 1):
        with st.expander(f"📄 {file.filename} - {file.channel_type.value} (ID: {file.id})", expanded=(idx == 1)):
            
            # File information
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Нийт зүйл", file.row_count)
            with col2:
                if file.total_amount:
                    st.metric("Нийт төсөв", f"₮{float(file.total_amount):,.0f}")
                else:
                    st.metric("Нийт төсөв", "N/A")
            with col3:
                uploader_name = file.uploader.full_name if file.uploader else "Unknown"
                st.write(f"**Хуулсан:** {uploader_name}")
                st.caption(f"Огноо: {file.uploaded_at.strftime('%Y-%m-%d %H:%M')}")
            
            # Show budget items
            st.subheader("📊 Төсвийн зүйлсийн урьдчилсан харагдац")
            items = get_budget_items_by_file(file.id)
            
            if items:
                items_data = []
                for item in items[:10]:  # Show first 10 items
                    items_data.append({
                        "Төсвийн код": item.budget_code,
                        "Кампанит ажил": item.campaign_name,
                        "Нийлүүлэгч": item.vendor or "N/A",
                        "Дүн": f"₮{float(item.amount_planned):,.0f}" if item.amount_planned else "N/A",
                        "Эхлэх огноо": item.start_date.strftime("%Y-%m-%d") if item.start_date else "N/A"
                    })
                
                df = pd.DataFrame(items_data)
                st.dataframe(df, use_container_width=True)
                
                if len(items) > 10:
                    st.caption(f"Харуулж байна 10 {len(items)}-ийн зүйл")
            else:
                st.warning("Энэ файлд зүйл олдсонгүй")
            
            # Action buttons
            st.divider()
            col1, col2, col3 = st.columns([1, 1, 3])
            
            with col1:
                if st.button(f"✅ Батлах", key=f"approve_{file.id}", type="primary"):
                    result = update_budget_file_status(
                        file.id,
                        FileStatus.APPROVED_FOR_PRINT,
                        reviewer_id=user.id,
                        reviewer_comment="Approved by manager"
                    )
                    if result:
                        st.success(f"✅ Файл батлагдлаа! Төлөвлөгч одоо PDF үүсгэж болно.")
                        st.rerun()
                    else:
                        st.error("Файл батлахад алдаа гарлаа")
            
            with col2:
                if st.button(f"❌ Татгалзах", key=f"reject_{file.id}"):
                    st.session_state[f'show_reject_{file.id}'] = True
            
            # Rejection form
            if st.session_state.get(f'show_reject_{file.id}', False):
                with st.form(key=f"reject_form_{file.id}"):
                    reason = st.text_area("Татгалзсан шалтгаан:", key=f"reason_{file.id}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Татгалзахыг баталгаажуулах"):
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
                                    st.error(f"❌ Файл татгалзагдлаа. Төлөвлөгчид мэдэгдсэн.")
                                    del st.session_state[f'show_reject_{file.id}']
                                    st.rerun()
                            else:
                                st.warning("Татгалзах шалтгааныг оруулна уу")
                    
                    with col2:
                        if st.form_submit_button("Цуцлах"):
                            del st.session_state[f'show_reject_{file.id}']
                            st.rerun()


# =============================================================================
# PLANNER VIEW - Stages 2 & 3
# =============================================================================

def show_planner_view(user: User):
    """Show workflow stages for planners."""
    
    st.header("👤 Төлөвлөгчийн самбар")
    
    # Create tabs for different stages
    tab1, tab2, tab3 = st.tabs([
        "⏳ Батлах хүлээлт",
        "🖨️ Хэвлэхэд бэлэн",
        "✍️ Гарын үсэг хүлээж байна"
    ])
    
    with tab1:
        show_pending_files(user)
    
    with tab2:
        show_approved_files(user)
    
    with tab3:
        show_signing_files(user)


def show_pending_files(user: User):
    """Show files waiting for manager approval."""
    
    st.subheader("⏳ Менежерийн батлал хүлээж буй файлууд")
    st.info("📋 **1-р үе шат: БАТЛАХ ХҮЛЭЭЛТ** - Таны файлуудыг менежерүүд хянаж байна")
    
    # Get user's pending files
    from modules.services import get_budget_files_by_uploader
    files = [f for f in get_budget_files_by_uploader(user.id) if f.status == FileStatus.PENDING_APPROVAL]
    
    if not files:
        st.success("✅ Батлал хүлээж буй файл байхгүй")
        return
    
    for file in files:
        with st.expander(f"📄 {file.filename} - Хуулсан {file.uploaded_at.strftime('%Y-%m-%d')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Зүйлүүд", file.row_count)
            with col2:
                if file.total_amount:
                    st.metric("Нийт", f"₮{float(file.total_amount):,.0f}")
            
            if file.reviewer_comment and "REJECTED" in file.reviewer_comment:
                st.error(f"❌ Татгалзсан шалтгаан: {file.reviewer_comment}")
                st.info("Тайлбаруудыг уншиж засварласан файл хуулна уу.")


def show_approved_files(user: User):
    """Show approved files ready for PDF generation (Stage 2)."""
    
    st.subheader("🖨️ Батлагдсан файлууд - Хэвлэхэд бэлэн")
    st.info("📋 **2-р үе шат: ХЭВЛЭХЭД БЭЛЭН** - Хэвлэх болон гарын үсэг зурахад зориулсан PDF үүсгэх")
    
    files = get_files_approved_for_print(user.id)
    
    if not files:
        st.success("✅ Хэвлэхэд бэлэн файл байхгүй")
        return
    
    for file in files:
        with st.expander(f"📄 {file.filename} (ID: {file.id})", expanded=True):
            
            # File info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Зүйлүүд", file.row_count)
            with col2:
                if file.total_amount:
                    st.metric("Нийт", f"₮{float(file.total_amount):,.0f}")
            with col3:
                st.write(f"**Батлагдсан:** {file.reviewed_at.strftime('%Y-%m-%d')}")
            
            if file.reviewer_comment:
                st.info(f"💬 Менежерийн тайлбар: {file.reviewer_comment}")
            
            st.divider()
            
            # PDF Generation
            if st.button(f"📄 Хэвлэхэд зориулсан PDF үүсгэх", key=f"gen_pdf_{file.id}", type="primary"):
                with st.spinner("PDF үүсгэж байна..."):
                    # Get budget items
                    items = get_budget_items_by_file(file.id)
                    
                    # Generate PDF
                    success, message, pdf_path = generate_budget_pdf(file, items)
                    
                    if success:
                        # Update database
                        update_file_with_pdf(file.id, pdf_path)
                        st.success("✅ PDF амжилттай үүсгэгдлээ!")
                        st.info("📝 Дараагийн алхмууд:\n1. PDF-г татаж авах\n2. Хэвлэх\n3. Гарын үсэг авах\n4. Гарын үсэгтэй баримтыг скан хийх\n5. Системд буцаан хуулах")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
            
            # Show download button if PDF exists
            if file.pdf_file_path and os.path.exists(file.pdf_file_path):
                with open(file.pdf_file_path, "rb") as f:
                    pdf_data = f.read()
                
                st.download_button(
                    label="⬇️ Үүссэн PDF-г татаж авах",
                    data=pdf_data,
                    file_name=f"budget_approval_{file.id}.pdf",
                    mime="application/pdf",
                    key=f"download_{file.id}"
                )


def show_signing_files(user: User):
    """Show files awaiting signed document upload (Stage 3)."""
    
    st.subheader("✍️ Гарын үсэгтэй баримт хүлээж байна")
    st.info("📋 **3-р үе шат: ГАРЫН ҮСЭГ** - Эцэслэхийн тулд скан хийсэн гарын үсэгтэй баримтыг хуулна уу")
    
    files = get_files_in_signing(user.id)
    
    if not files:
        st.success("✅ Гарын үсгийн хуулалт хүлээж буй файл байхгүй")
        return
    
    for file in files:
        with st.expander(f"📄 {file.filename} (ID: {file.id})", expanded=True):
            
            # File info
            st.write(f"**PDF үүсгэсэн:** {file.pdf_generated_at.strftime('%Y-%m-%d %H:%M')}")
            st.write(f"**Зүйлүүд:** {file.row_count}")
            
            # Download PDF if needed
            if file.pdf_file_path and os.path.exists(file.pdf_file_path):
                with open(file.pdf_file_path, "rb") as f:
                    pdf_data = f.read()
                
                st.download_button(
                    label="⬇️ PDF-г дахин татаж авах",
                    data=pdf_data,
                    file_name=f"budget_approval_{file.id}.pdf",
                    mime="application/pdf",
                    key=f"redownload_{file.id}"
                )
            
            st.divider()
            st.write("**📤 Гарын үсэгтэй баримт хуулах:**")
            
            # Upload form
            uploaded_signed = st.file_uploader(
                "Скан хийсэн гарын үсэгтэй баримт сонгох (PDF, JPG, PNG)",
                type=['pdf', 'jpg', 'jpeg', 'png'],
                key=f"upload_signed_{file.id}"
            )
            
            if uploaded_signed:
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if st.button(f"✅ Эцэслэх", key=f"finalize_{file.id}", type="primary"):
                        with st.spinner("Хуулж эцэслэж байна..."):
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
                                    st.success("🎉 АМЖИЛТТАЙ! Төсөв одоо ЭЦЭСЛЭГДЭЖ самбар дээр харагдаж байна!")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("Өгөгдлийн санд хадгалахад алдаа гарлаа")
                            else:
                                st.error(f"❌ {message}")
                
                with col2:
                    st.caption("Энэ нь төсвийг ЭЦЭСЛЭСЭН төлөвт шилжүүлж үндсэн самбар дээр харагдах болгоно.")


# =============================================================================
# RUN PAGE
# =============================================================================

if __name__ == "__main__":
    main()
else:
    main()

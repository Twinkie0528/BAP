"""
Workflow Page - Manager Reviews Excel Files
============================================

Managers can view and download uploaded Excel files exactly as they were uploaded.

Author: CPP Development Team
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Төсвийн ажлын урсгал",
    page_icon="🔄",
    layout="wide"
)

# Import our modules
from config import FileStatus, UserRole
from database import get_session, User, BudgetFile
from modules.jwt_auth import get_current_user_from_token
from modules.services import (
    get_files_pending_approval,
    update_budget_file_status
)
from modules.file_storage import (
    get_excel_file_path, 
    read_excel_file, 
    read_excel_file_bytes,
    create_preview_pdf,
    read_pdf_as_base64,
    preview_pdf_exists,
    get_preview_pdf_path
)


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    """Main workflow page."""
    
    # Check JWT authentication
    jwt_user = get_current_user_from_token()
    if not jwt_user:
        st.title("🔄 Төсвийн ажлын урсгал")
        st.warning("⚠️ Нэвтрэх шаардлагатай")
        st.info("👈 Зүүн талын цэснээс **🏠 Home** хуудас руу очиж нэвтэрнэ үү.")
        if st.button("🔐 Нэвтрэх хуудас руу очих"):
            st.switch_page("app.py")
        return
    
    # Get user from database for full object
    with get_session() as session:
        user = session.get(User, int(jwt_user['id']))
    
    if not user:
        st.error("Хэрэглэгч олдсонгүй. Дахин нэвтэрнэ үү.")
        st.stop()
    
    # Page header
    st.title("🔄 Төсвийн ажлын урсгал")
    st.markdown(f"Нэвтэрсэн: **{user.full_name or user.username}** ({user.role.value})")
    
    st.divider()
    
    # Show different views based on role
    if user.role in [UserRole.MANAGER, UserRole.ADMIN]:
        show_manager_view(user)
    else:
        show_planner_view(user)


# =============================================================================
# MANAGER VIEW
# =============================================================================

def show_manager_view(user: User):
    """Show pending approvals for managers - with Excel download."""
    
    st.header("👔 Менежерийн самбар - Хүлээгдэж байгаа")
    st.info("📋 Доорх файлуудыг хянаж, Excel файлыг татаж үзээд батлах эсвэл буцаах боломжтой.")
    
    # =========================================================================
    # SPECIALIST MANAGEMENT (Admin/Manager only)
    # =========================================================================
    with st.expander("⚙️ Мэргэжилтнүүдийн жагсаалт засварлах"):
        st.caption("Төсөв оруулах үед сонгох мэргэжилтнүүдийг нэмэх эсвэл хасах")
        
        # Initialize session state
        if 'removed_specialists' not in st.session_state:
            st.session_state.removed_specialists = []
        if 'custom_specialists' not in st.session_state:
            st.session_state.custom_specialists = []
        
        # Default specialists list
        DEFAULT_SPECIALISTS = [
            "Н. Энх-Өлзий",
            "Д. Эгшиглэн",
            "Ц. Содномцэрэн",
            "М. Золзаяа",
            "А. Жавхлан",
            "М. Наранцацрал",
            "Б. Наранцэцэг"
        ]
        
        # Get current specialists
        all_default = [s for s in DEFAULT_SPECIALISTS if s not in st.session_state.removed_specialists]
        all_specialists = all_default + st.session_state.custom_specialists
        
        col1, col2 = st.columns([3, 1])
        with col1:
            new_specialist = st.text_input(
                "Шинэ мэргэжилтний нэр",
                placeholder="Ж. Болд",
                key="new_specialist_input"
            )
        with col2:
            st.write("")  # spacing
            if st.button("➕ Нэмэх", key="add_specialist_btn"):
                if new_specialist and new_specialist.strip():
                    name = new_specialist.strip()
                    # Remove from removed list if it was there
                    if name in st.session_state.removed_specialists:
                        st.session_state.removed_specialists.remove(name)
                        st.success(f"✅ '{name}' сэргээгдлээ!")
                    elif name not in all_specialists:
                        st.session_state.custom_specialists.append(name)
                        st.success(f"✅ '{name}' нэмэгдлээ!")
                    else:
                        st.warning("Энэ нэр аль хэдийн байна")
                    st.rerun()
        
        st.divider()
        st.write("**Одоогийн мэргэжилтнүүд:**")
        
        # Refresh all_specialists after potential changes
        all_default = [s for s in DEFAULT_SPECIALISTS if s not in st.session_state.removed_specialists]
        all_specialists = all_default + st.session_state.custom_specialists
        
        # Show all specialists with remove option
        for i, name in enumerate(all_specialists):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {name}")
            with col2:
                if st.button("❌ Хасах", key=f"remove_specialist_{i}"):
                    # Add to removed list or remove from custom list
                    if name in DEFAULT_SPECIALISTS:
                        st.session_state.removed_specialists.append(name)
                    elif name in st.session_state.custom_specialists:
                        st.session_state.custom_specialists.remove(name)
                    st.rerun()
        
        if not all_specialists:
            st.warning("Мэргэжилтэн байхгүй байна. Шинээр нэмнэ үү.")
    
    st.divider()
    
    # Load pending files
    pending_files = get_files_pending_approval(limit=50)
    
    if not pending_files:
        st.success("✅ Батлах хүлээгдэж буй файл байхгүй байна!")
        return
    
    st.write(f"**Таны хянаж үзэх {len(pending_files)} файл байна:**")
    
    # Display each pending file
    for idx, file in enumerate(pending_files, 1):
        budget_type_label = "Үндсэн төсөв" if file.budget_type.value == "primary" else "Нэмэлт төсөв"
        
        with st.expander(f"📄 {file.filename} - {budget_type_label} (ID: {file.id})", expanded=(idx == 1)):
            
            # File information
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Нийт бодит төсөв (actual budget)
                if file.total_amount:
                    st.metric("Нийт бодит төсөв", f"₮{float(file.total_amount):,.0f}")
                else:
                    st.metric("Нийт бодит төсөв", "N/A")
            with col2:
                # Нийт төсөв (planned budget)
                if hasattr(file, 'planned_amount') and file.planned_amount:
                    st.metric("Нийт төсөв", f"₮{float(file.planned_amount):,.0f}")
                else:
                    st.metric("Нийт төсөв", "N/A")
            with col3:
                # Show specialist name from budget file
                specialist = getattr(file, 'specialist_name', None) or 'N/A'
                st.write(f"**Төсөв оруулсан:** {specialist}")
            with col4:
                st.write(f"**Огноо:** {file.uploaded_at.strftime('%Y-%m-%d %H:%M')}")
            
            st.divider()
            
            # Download Excel file button
            excel_path = file.pdf_file_path  # We stored excel path here
            if not excel_path:
                excel_path = get_excel_file_path(file.id)
            
            if excel_path and os.path.exists(excel_path):
                # Read Excel file as bytes for download
                excel_bytes = read_excel_file_bytes(excel_path)
                if excel_bytes:
                    st.download_button(
                        label="📥 Excel файл татах",
                        data=excel_bytes,
                        file_name=file.filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_{file.id}"
                    )
                    
                    # Show PDF preview
                    st.subheader("📄 PDF Preview")
                    
                    # Create or get existing PDF preview
                    with st.spinner("PDF үүсгэж байна..."):
                        pdf_path = create_preview_pdf(excel_path, file.id)
                    
                    if pdf_path and os.path.exists(pdf_path):
                        # Read PDF as base64
                        pdf_base64 = read_pdf_as_base64(pdf_path)
                        
                        if pdf_base64:
                            # Display PDF in iframe
                            pdf_display = f'''
                            <iframe 
                                src="data:application/pdf;base64,{pdf_base64}" 
                                width="100%" 
                                height="600px" 
                                type="application/pdf"
                                style="border: 1px solid #ddd; border-radius: 8px;">
                            </iframe>
                            '''
                            st.markdown(pdf_display, unsafe_allow_html=True)
                            
                            # Also provide PDF download button
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(
                                    label="📥 PDF татах",
                                    data=pdf_file.read(),
                                    file_name=f"{file.filename.rsplit('.', 1)[0]}.pdf",
                                    mime="application/pdf",
                                    key=f"download_pdf_{file.id}"
                                )
                        else:
                            st.warning("PDF унших боломжгүй байна")
                    else:
                        st.warning("⚠️ PDF үүсгэхэд алдаа гарлаа. Excel preview харуулж байна.")
                        # Fallback to Excel preview
                        try:
                            import pandas as pd
                            xl = pd.ExcelFile(excel_path)
                            target_sheet = xl.sheet_names[0]
                            df = pd.read_excel(xl, sheet_name=target_sheet, header=None)
                            for col in df.columns:
                                df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) else "")
                            st.dataframe(df, height=400)
                        except Exception as e:
                            st.error(f"Preview харуулахад алдаа: {e}")
            else:
                st.warning("⚠️ Excel файл олдсонгүй")
            
            st.divider()
            
            # Action buttons
            st.subheader("⚡ Үйлдэл")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("✅ Батлах", key=f"approve_{file.id}", type="primary"):
                    success = update_budget_file_status(
                        file.id,
                        FileStatus.APPROVED_FOR_PRINT,
                        reviewer_id=user.id
                    )
                    if success:
                        st.success("✅ Файл батлагдлаа!")
                        st.rerun()
                    else:
                        st.error("Батлахад алдаа гарлаа")
            
            with col2:
                reject_comment = st.text_input(
                    "Буцаах шалтгаан",
                    key=f"reject_comment_{file.id}",
                    placeholder="Шалтгаан бичнэ үү..."
                )
                if st.button("❌ Буцаах", key=f"reject_{file.id}"):
                    if not reject_comment:
                        st.warning("Буцаах шалтгаан оруулна уу")
                    else:
                        # Reject = set to REJECTED status
                        success = update_budget_file_status(
                            file.id,
                            FileStatus.REJECTED,
                            reviewer_id=user.id,
                            reviewer_comment=reject_comment
                        )
                        if success:
                            st.success("✅ Файл буцаагдлаа. Ажилтан засвар хийх боломжтой.")
                            st.rerun()
                        else:
                            st.error("Буцаахад алдаа гарлаа")


# =============================================================================
# PLANNER VIEW
# =============================================================================

def show_planner_view(user: User):
    """Show planner's uploaded files status."""
    
    st.header("📋 Миний оруулсан төсвүүд")
    
    # Get user's files
    with get_session() as session:
        from sqlmodel import select
        statement = (
            select(BudgetFile)
            .where(BudgetFile.uploader_id == user.id)
            .order_by(BudgetFile.uploaded_at.desc())
        )
        my_files = session.exec(statement).all()
    
    # Show rejected files prominently
    rejected_files = [f for f in my_files if f.status == FileStatus.REJECTED]
    if rejected_files:
        st.error(f"⚠️ {len(rejected_files)} файл буцаагдсан байна! Засвар хийж дахин илгээнэ үү.")
        
        for file in rejected_files:
            with st.expander(f"❌ {file.campaign_name or file.filename}", expanded=True):
                st.markdown(f"**📌 Буцаасан шалтгаан:** {file.reviewer_comment or 'Шалтгаан бичигдээгүй'}")
                st.markdown(f"**📅 Огноо:** {file.reviewed_at.strftime('%Y-%m-%d %H:%M') if file.reviewed_at else 'N/A'}")
                
                # Button to resubmit (redirect to upload page)
                if st.button("📤 Дахин засаж илгээх", key=f"resubmit_{file.id}"):
                    st.page_link("pages/2_📤_Upload.py", label="Upload хуудас руу очих")
        
        st.divider()
    
    if not my_files:
        st.info("Та одоогоор ямар ч төсөв оруулаагүй байна.")
        st.page_link("pages/2_📤_Upload.py", label="📤 Төсөв оруулах", icon="📤")
        return
    
    # Display files
    for file in my_files:
        status_emoji = {
            FileStatus.PENDING_APPROVAL: "🕐",
            FileStatus.APPROVED_FOR_PRINT: "✅",
            FileStatus.SIGNING: "📝",
            FileStatus.FINALIZED: "🏁",
            FileStatus.REJECTED: "❌"
        }.get(file.status, "❓")
        
        status_text = {
            FileStatus.PENDING_APPROVAL: "Хүлээгдэж байгаа",
            FileStatus.APPROVED_FOR_PRINT: "Батлагдсан",
            FileStatus.SIGNING: "Гарын үсэг зурж байна",
            FileStatus.FINALIZED: "Дууссан",
            FileStatus.REJECTED: "Буцаагдсан"
        }.get(file.status, str(file.status))
        
        with st.expander(f"{status_emoji} {file.filename} - {status_text}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**ID:** {file.id}")
                st.write(f"**Мөрийн тоо:** {file.row_count or 'N/A'}")
            
            with col2:
                if file.total_amount:
                    st.write(f"**Нийт дүн:** ₮{float(file.total_amount):,.0f}")
                st.write(f"**Илгээсэн:** {file.uploaded_at.strftime('%Y-%m-%d %H:%M')}")
            
            with col3:
                st.write(f"**Төлөв:** {status_text}")
                if file.reviewer_comment:
                    st.warning(f"**Тайлбар:** {file.reviewer_comment}")


# =============================================================================
# RUN PAGE
# =============================================================================

if __name__ == "__main__":
    main()
else:
    main()

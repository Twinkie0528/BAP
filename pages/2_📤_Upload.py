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
        st.error("Хэрэглэгч олдсонгүй. Дахин нэвтэрнэ үү.")
        st.stop()
    
    # Page header
    st.title("📤 Төсвийн файл хуулах")
    st.markdown(f"Тавтай морил, **{user.full_name or user.username}**")
    st.info("📋 Энд хуулсан файлууд 1-р үе шат: БАТЛАХ ХҮЛЭЭЛТЭНД орж менежерийн хянан баталгаажилт хүлээнэ.")
    
    st.divider()
    
    # Upload form
    with st.form("upload_form", clear_on_submit=False):
        
        # Channel selection
        col1, col2 = st.columns([1, 2])
        
        with col1:
            channel_options = [ch.value for ch in ChannelType]
            selected_channel = st.selectbox(
                "Сувгийн төрөл сонгох*",
                channel_options,
                help="Энэ төсвийн файлд зориулсан маркетингийн сувгийг сонгоно уу"
            )
        
        # File upload
        uploaded_file = st.file_uploader(
            "Excel эсвэл CSV файл сонгох*",
            type=['xlsx', 'xls', 'csv'],
            help="Төсвийн төлөвлөлтийн файлаа хуулна уу"
        )
        
        # Show preview
        if uploaded_file:
            # Auto-detect channel from filename
            detected = detect_channel_from_filename(uploaded_file.name)
            if detected and detected != selected_channel:
                st.info(f"💡 Файлын нэрээс сувгийг таньсан: **{detected}**")
            
            st.subheader("📋 Файлын урьдчилсан харагдац")
            
            # Show preview
            preview_df, _ = get_file_preview(uploaded_file, max_rows=10)
            if not preview_df.empty:
                st.dataframe(preview_df, use_container_width=True)
                st.caption(f"Эхний мөрүүдийн урьдчилсан харагдац. Файл илгээхэд бүрэн боловсруулагдана.")
        
        # Submit button
        submitted = st.form_submit_button("🚀 Боловсруулж хуулах", type="primary")
    
    # Process form submission
    if submitted:
        if not uploaded_file:
            st.error("❌ Хуулах файлаа сонгоно уу")
            return
        
        process_and_save_file(uploaded_file, selected_channel, user)


# =============================================================================
# FILE PROCESSING
# =============================================================================

def process_and_save_file(uploaded_file, channel_type: str, user: User):
    """Process uploaded file and save to database."""
    
    with st.spinner("Файл боловсруулж байна..."):
        
        # Process the file
        df, metadata, errors = process_uploaded_file(
            uploaded_file,
            channel_type
        )
        
        if df is None:
            st.error("❌ Файл боловсруулахад алдаа гарлаа")
            for error in errors:
                st.error(f"  • {error}")
            return
        
        # Show processing results
        st.success(f"✅ Амжилттай боловсруулсан {metadata['row_count']} мөр!")
        
        # Show metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Мөр", metadata['row_count'])
        with col2:
            total = metadata['total_amount']
            st.metric("Нийт төсөв", f"₮{total:,.0f}" if total else "N/A")
        with col3:
            st.metric("Толгой мөр", metadata['header_row'])
        
        # Show validation issues
        validation_issues = validate_dataframe(df)
        if validation_issues:
            with st.expander("⚠️ Баталгаажуулалтын тэмдэглэлүүд (дэлгэх бол дарна уу)"):
                for issue in validation_issues:
                    st.warning(f"  • {issue}")
        
        # Check for duplicates
        if metadata['file_hash']:
            existing = check_duplicate_file(metadata['file_hash'])
            if existing:
                st.error(f"❌ Энэ файл аль хэдийн хуулагдсан байна (File ID: {existing.id})")
                st.warning("Засварласан хувилбарыг хуулахыг хүсвэл эхлээд файлд өөрчлөлт оруулна уу.")
                return
        
        # Show processed data preview
        st.subheader("📊 Боловсруулсан өгөгдлийн урьдчилсан харагдац")
        st.dataframe(df.head(20), use_container_width=True)
        
        if len(df) > 20:
            st.caption(f"Харуулж байна 20 {len(df)}-ийн мөр")
        
        st.divider()
        
        # Confirmation
        st.write("**Өгөгдлийн санд хадгалахад бэлэн үү?**")
        st.info("💡 Энэ нь БАТЛАХ ХҮЛЭЭЛТ төлөвтэй шинэ төсвийн файл үүсгэнэ. Менежерүүд үүнийг хянаж батлах боломжтой.")
        
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            if st.button("💾 Баталгаажуулж хадгалах", type="primary"):
                save_to_database(df, metadata, channel_type, user)
        
        with col2:
            if st.button("❌ Цуцлах"):
                st.rerun()


def save_to_database(df: pd.DataFrame, metadata: dict, channel_type: str, user: User):
    """Save processed data to database."""
    
    with st.spinner("Өгөгдлийн санд хадгалж байна..."):
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
            
            st.success(f"✅ Төсвийн файл үүсгэгдлээ (ID: {budget_file.id})")
            
            # Convert DataFrame to BudgetItem dictionaries
            items = dataframe_to_budget_items(
                df,
                budget_file.id,
                channel_type,
                specialist_username=user.username  # Set specialist for row-level security
            )
            
            # Bulk insert items
            created_count = create_budget_items_bulk(items)
            
            st.success(f"✅ {created_count} төсвийн зүйлс амжилттай хадгалагдлаа!")
            
            # Show success message and next steps
            st.balloons()
            
            st.success("🎉 **Хуулалт дууслаа!**")
            st.info(f"""
            **Дараагийн алхмууд:**
            1. ✅ Таны файл одоо БАТЛАХ ХҮЛЭЭЛТ төлөвтэй байна
            2. 👔 Менежер таны төсвийг хянаж батална
            3. 🖨️ Батлагдсаны дараа та хэвлэхэд зориулсан PDF үүсгэж болно
            4. ✍️ Хэвлэсэн баримт дээр гарын үсэг авах
            5. 📤 Эцэслэхийн тулд гарын үсэгтэй сканыг хуулах
            6. 📊 Эцэслэсний дараа таны төсөв үндсэн самбар дээр гарч ирнэ
            """)
            
            # Link to workflow page
            st.page_link("pages/1_🔄_Workflow.py", label="➡️ Ажлын урсгалын хуудас руу очих", icon="🔄")
            
            # Clear session state to allow new upload
            if st.button("Өөр файл хуулах"):
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Өгөгдлийн санд хадгалахад алдаа гарлаа: {str(e)}")
            import traceback
            with st.expander("Алдааны дэлгэрэнгүй"):
                st.code(traceback.format_exc())


# =============================================================================
# RUN PAGE
# =============================================================================

if __name__ == "__main__":
    main()
else:
    main()

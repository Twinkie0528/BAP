"""
Budget File Upload Page
========================

Upload Excel files and send them directly to manager for review.
Files are stored exactly as uploaded - no modifications.

Author: CPP Development Team
"""

import streamlit as st
import pandas as pd
import hashlib
import re
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Upload Budget",
    page_icon="📤",
    layout="wide"
)

# Import our modules
from config import BudgetType, FileStatus
from database import get_session, User, BudgetFile
from modules.jwt_auth import get_current_user_from_token
from modules.file_storage import (
    save_excel_file, 
    create_preview_pdf, 
    read_pdf_as_base64, 
    get_excel_file_path
)
from modules.services import create_budget_file, check_duplicate_file
from sqlmodel import select


# =============================================================================
# SPECIALIST NAMES (Configurable list)
# =============================================================================

DEFAULT_SPECIALISTS = [
    "Н. Энх-Өлзий",
    "Д. Эгшиглэн",
    "Ц. Содномцэрэн",
    "М. Золзаяа",
    "А. Жавхлан",
    "М. Наранцацрал",
    "Б. Наранцэцэг"
]


def get_specialist_list():
    """Get list of specialists. Can be extended to load from database."""
    # Check if custom specialists exist in session state
    if 'custom_specialists' not in st.session_state:
        st.session_state.custom_specialists = []
    if 'removed_specialists' not in st.session_state:
        st.session_state.removed_specialists = []
    
    # Combine default and custom, exclude removed
    all_specialists = DEFAULT_SPECIALISTS + st.session_state.custom_specialists
    return [s for s in all_specialists if s not in st.session_state.removed_specialists]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_user_rejected_files(user_id: int):
    """Get rejected files for a specific user."""
    with get_session() as session:
        statement = (
            select(BudgetFile)
            .where(BudgetFile.uploader_id == user_id)
            .where(BudgetFile.status == FileStatus.REJECTED)
            .order_by(BudgetFile.reviewed_at.desc())
        )
        return list(session.exec(statement).all())


def delete_rejected_file(file_id: int) -> bool:
    """Delete a rejected file from database and filesystem."""
    import os
    
    try:
        with get_session() as session:
            statement = select(BudgetFile).where(BudgetFile.id == file_id)
            file = session.exec(statement).first()
            
            if not file:
                return False
            
            # Only allow deletion of REJECTED files
            if file.status != FileStatus.REJECTED:
                return False
            
            # Delete the physical Excel file if exists
            if file.pdf_file_path and os.path.exists(file.pdf_file_path):
                try:
                    os.remove(file.pdf_file_path)
                except:
                    pass
            
            # Also check for uploaded Excel files
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            excel_pattern = os.path.join(base_dir, 'assets', 'uploaded_files', f"budget_{file_id}_*.xlsx")
            import glob
            for excel_file in glob.glob(excel_pattern):
                try:
                    os.remove(excel_file)
                except:
                    pass
            
            # Delete from database
            session.delete(file)
            session.commit()
            
        return True
    except Exception as e:
        print(f"Error deleting rejected file: {e}")
        return False


def get_primary_campaigns(user_id: int = None):
    """Get list of PRIMARY budget campaigns for dropdown.
    
    Args:
        user_id: If provided, filter by uploader. If None, return all.
    """
    with get_session() as session:
        statement = (
            select(BudgetFile)
            .where(BudgetFile.budget_type == BudgetType.PRIMARY)
            .where(BudgetFile.campaign_name != None)
            .where(BudgetFile.campaign_name != "")
        )
        
        # Filter by user if provided
        if user_id:
            statement = statement.where(BudgetFile.uploader_id == user_id)
        
        statement = statement.order_by(BudgetFile.uploaded_at.desc())
        
        files = session.exec(statement).all()
        # Return unique campaign names with their file IDs
        campaigns = {}
        for f in files:
            if f.campaign_name and f.campaign_name not in campaigns:
                campaigns[f.campaign_name] = {
                    'file_id': f.id,
                    'specialist': f.specialist_name or '',
                    'budget_code': f.budget_code or '',
                    'brand': f.brand or ''
                }
        return campaigns

def clean_currency_value(value_str: str) -> float:
    """
    Clean and parse currency values from Excel.
    
    Handles:
    - Commas: "10,000,000" -> 10000000
    - Spaces: "10 000 000" -> 10000000
    - Unicode spaces: "\xa0", "\u202f"
    - Currency symbols: "₮", "$"
    - Trailing text: "16,434,532₮" -> 16434532
    
    Returns:
        Float value or None if cannot parse
    """
    if not value_str or value_str.lower() in ['nan', 'none', '', '-']:
        return None
    
    # Remove all non-numeric characters except digits, dots, and minus
    cleaned = re.sub(r'[^\d.\-]', '', str(value_str))
    
    if not cleaned or cleaned == '-':
        return None
    
    try:
        return float(cleaned)
    except ValueError:
        return None# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    """Main upload page."""
    
    # Check JWT authentication
    jwt_user = get_current_user_from_token()
    if not jwt_user:
        st.title("📤 Төсөв оруулах")
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
    st.title("📤 Төсөв оруулах")
    st.markdown(f"Тавтай морил, **{user.full_name or user.username}**")
    st.info("📋 Энд оруулсан төсвүүд шууд менежерийн хянан баталгаажилтанд очно.")
    
    # =========================================================================
    # SHOW REJECTED FILES SECTION
    # =========================================================================
    rejected_files = get_user_rejected_files(user.id)
    if rejected_files:
        st.error(f"⚠️ **{len(rejected_files)} төсөв буцаагдсан байна!** Засвар хийж дахин илгээнэ үү.")
        
        for file in rejected_files:
            with st.expander(f"❌ {file.campaign_name or file.filename}", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**📌 Буцаасан шалтгаан:** {file.reviewer_comment or 'Шалтгаан бичигдээгүй'}")
                    st.markdown(f"**📅 Буцаасан огноо:** {file.reviewed_at.strftime('%Y-%m-%d %H:%M') if file.reviewed_at else 'N/A'}")
                    st.markdown(f"**📄 Файлын нэр:** {file.filename}")
                
                with col2:
                    # Delete rejected file button
                    if st.button("🗑️ Устгах", key=f"delete_rejected_{file.id}", type="secondary"):
                        if delete_rejected_file(file.id):
                            st.success("Файл устгагдлаа!")
                            st.rerun()
                        else:
                            st.error("Устгахад алдаа гарлаа")
        
        st.markdown("---")
        st.markdown("👆 **Дээрх буцаагдсан файлуудаа устгаж, доорхи хэсгээр дахин зөв засаж хуулна уу.**")
        st.divider()
    
    st.divider()
    
    # Budget type selection - OUTSIDE FORM for immediate rerun on change
    budget_type_options = {
        "Үндсэн төсөв": BudgetType.PRIMARY.value,
        "Нэмэлт төсөв": BudgetType.ADDITIONAL.value
    }
    selected_budget_label = st.selectbox(
        "Төсвийн төрөл сонгох*",
        list(budget_type_options.keys()),
        help="Үндсэн төсөв: Campaign ажлын үндсэн төсөв | Нэмэлт төсөв: Нэмэлт төсвийг үндсэн кампаниттай холбоно"
    )
    selected_budget_type = budget_type_options[selected_budget_label]
    
    # Get existing campaigns for ADDITIONAL budget
    existing_campaigns = get_primary_campaigns(user_id=user.id)
    
    # Show campaign selection for ADDITIONAL type - ALSO OUTSIDE FORM
    if selected_budget_type == BudgetType.ADDITIONAL.value:
        st.markdown("#### 🔗 Үндсэн кампанит ажилтай холбох")
        
        if not existing_campaigns:
            st.warning("⚠️ Нэмэлт төсөв холбох үндсэн кампанит ажил байхгүй байна. Эхлээд үндсэн төсөв оруулна уу.")
            campaign_name = None
            specialist_name = None
            parent_file_id = None
        else:
            campaign_options = list(existing_campaigns.keys())
            selected_campaign = st.selectbox(
                "Үндсэн кампанит ажил сонгох*",
                options=campaign_options,
                help="Нэмэлт төсвийг холбох үндсэн кампанит ажлаа сонгоно уу"
            )
            
            # Auto-fill from selected campaign
            if selected_campaign:
                campaign_info = existing_campaigns[selected_campaign]
                campaign_name = selected_campaign
                specialist_name = campaign_info['specialist']
                parent_file_id = campaign_info['file_id']
                
                st.success(f"""
                **✅ Сонгосон кампанит ажил:**
                - 📌 Нэр: {campaign_name}
                - 👤 Мэргэжилтэн: {specialist_name or 'N/A'}
                - 🏷️ Брэнд: {campaign_info['brand'] or 'N/A'}
                - 📋 Код: {campaign_info['budget_code'] or 'N/A'}
                """)
            else:
                campaign_name = None
                specialist_name = None
                parent_file_id = None
    else:
        # PRIMARY - will be filled from Excel file
        parent_file_id = None
    
    st.divider()
    
    # ==========================================================================
    # FILE UPLOAD FIRST - Then extract campaign info from Excel
    # ==========================================================================
    
    st.markdown("#### 📁 Excel файл сонгох")
    
    uploaded_file = st.file_uploader(
        "Excel файл сонгох*",
        type=['xlsx', 'xls'],
        help="Төсвийн төлөвлөлтийн Excel файлаа оруулна уу",
        key="budget_excel_upload"
    )
    
    # Show file info
    if uploaded_file:
        st.subheader("📋 Файлын мэдээлэл")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Файлын нэр:** {uploaded_file.name}")
        with col2:
            size_kb = uploaded_file.size / 1024
            st.write(f"**Хэмжээ:** {size_kb:.1f} KB")
        with col3:
            st.write(f"**Төрөл:** Excel")
        
        # Show sheet names
        try:
            uploaded_file.seek(0)
            xl = pd.ExcelFile(uploaded_file)
            st.write(f"**Sheet-үүд:** {', '.join(xl.sheet_names)}")
            uploaded_file.seek(0)
        except:
            pass
    
    st.divider()
    
    # Upload form - Campaign info section
    with st.form("upload_form", clear_on_submit=False):
        
        # PRIMARY: Show campaign name input (manual entry)
        if selected_budget_type == BudgetType.PRIMARY.value:
            st.markdown("#### 📋 Кампанит ажлын мэдээлэл")
            
            col1, col2 = st.columns(2)
            with col1:
                # Manual input for campaign name
                campaign_name = st.text_input(
                    "Кампанит ажлын нэр*",
                    placeholder="Кампанит ажлын нэрээ оруулна уу",
                    help="Кампанит ажлын нэрийг гараар оруулна уу"
                )
            with col2:
                # Мэргэжилтний нэр - автоматаар нэвтэрсэн хэрэглэгчийн нэр
                specialist_name = user.full_name or user.username
                st.text_input(
                    "Мэргэжилтний нэр*",
                    value=specialist_name,
                    disabled=True,
                    help="Таны бүртгэлийн нэр автоматаар ашиглагдана"
                )
            
            st.divider()
        else:
            # ADDITIONAL - specialist_name from user
            specialist_name = user.full_name or user.username
        
        # Submit button
        submitted = st.form_submit_button("🚀 Хянагчид илгээх", type="primary")
    
    # Process form submission
    if submitted:
        if not uploaded_file:
            st.error("❌ Хуулах файлаа сонгоно уу")
            return
        
        # Validate campaign info for PRIMARY
        if selected_budget_type == BudgetType.PRIMARY.value:
            if not campaign_name or not campaign_name.strip():
                st.error("❌ Үндсэн төсөв оруулахад кампанит ажлын нэр заавал шаардлагатай")
                return
            # specialist_name автоматаар хэрэглэгчийн нэрээс авах учир шалгах шаардлагагүй
        
        # Validate campaign selection for ADDITIONAL
        if selected_budget_type == BudgetType.ADDITIONAL.value:
            if not campaign_name or parent_file_id is None:
                st.error("❌ Нэмэлт төсөв оруулахад үндсэн кампанит ажил сонгох шаардлагатай")
                return
        
        save_file_and_notify(
            uploaded_file, 
            selected_budget_type, 
            user,
            campaign_name=campaign_name,
            specialist_name=specialist_name,
            parent_file_id=parent_file_id
        )


# =============================================================================
# FILE SAVING
# =============================================================================

def save_file_and_notify(
    uploaded_file, 
    budget_type: str, 
    user: User,
    campaign_name: str = None,
    specialist_name: str = None,
    parent_file_id: int = None
):
    """Save the uploaded file and create database record."""
    
    with st.spinner("Файл хадгалж байна..."):
        try:
            # Calculate file hash
            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            uploaded_file.seek(0)
            
            # Check for duplicates
            existing = check_duplicate_file(file_hash)
            if existing:
                st.error(f"❌ Энэ файл аль хэдийн хуулагдсан байна (File ID: {existing.id})")
                st.warning("Засварласан хувилбарыг хуулахыг хүсвэл эхлээд файлд өөрчлөлт оруулна уу.")
                return
            
            # Get data from Excel
            try:
                uploaded_file.seek(0)
                xl = pd.ExcelFile(uploaded_file)
                
                # =================================================================
                # FIND TARGET SHEET - Priority order matters!
                # =================================================================
                target_sheet = None
                
                # 1. First, look for EXACT "TEMPLATE" sheet name
                for sn in xl.sheet_names:
                    if sn.upper() == 'TEMPLATE':
                        target_sheet = sn
                        break
                
                # 2. If not found, look for "гүйцэтгэл" sheet
                if target_sheet is None:
                    for sn in xl.sheet_names:
                        if 'гүйцэтгэл' in sn.lower():
                            target_sheet = sn
                            break
                
                # 3. Fallback to first non-excluded sheet
                if target_sheet is None:
                    exclude_keywords = ['general', 'employee', 'target', 'all', 'validation', 'budget list', 'names']
                    for sn in xl.sheet_names:
                        sn_lower = sn.lower()
                        if not any(ex in sn_lower for ex in exclude_keywords):
                            target_sheet = sn
                            break
                
                # 4. Last resort - first sheet
                if target_sheet is None:
                    target_sheet = xl.sheet_names[0]
                
                df = pd.read_excel(xl, sheet_name=target_sheet, header=None)
                row_count = len(df)
                
                # Extract budget_code, brand, total_budget and actual_budget from Excel
                budget_code = None
                brand = None
                total_budget = None      # Нийт төсөв (planned)
                actual_budget = None     # Нийт бодит төсөв (actual)
                
                # =================================================================
                # IMPROVED BUDGET EXTRACTION LOGIC
                # =================================================================
                # Search from BOTTOM to TOP - budget totals are usually at the end
                for idx in range(len(df) - 1, -1, -1):
                    row = df.iloc[idx]
                    
                    # Convert row to list of strings for easier processing
                    row_values = [str(v).strip() if pd.notna(v) else "" for v in row.values]
                    row_text = ' '.join(row_values).upper()
                    
                    # ===== FIND "НИЙТ БОДИТ ТӨСӨВ" =====
                    # This should be the FINAL actual budget at the very bottom
                    if actual_budget is None and 'НИЙТ БОДИТ ТӨСӨВ' in row_text:
                        # Find the cell index containing "НИЙТ БОДИТ ТӨСӨВ"
                        for i, val in enumerate(row_values):
                            if 'НИЙТ БОДИТ ТӨСӨВ' in val.upper():
                                # Look for number in cells AFTER this label (same row)
                                for j in range(i + 1, len(row_values)):
                                    num_str = row_values[j]
                                    cleaned = clean_currency_value(num_str)
                                    if cleaned and cleaned > 1000000:  # At least 1M
                                        actual_budget = cleaned
                                        break
                                break
                        # If not found in same row, check next row (label might be in separate row)
                        if actual_budget is None:
                            for val in row_values:
                                cleaned = clean_currency_value(val)
                                if cleaned and cleaned > 1000000:
                                    actual_budget = cleaned
                                    break
                    
                    # ===== FIND "НИЙТ ТӨСӨВ" (but NOT "БОДИТ" or subtotals) =====
                    # Must be the main total, not sub-category totals
                    if total_budget is None:
                        # Check if this row has EXACTLY "НИЙТ ТӨСӨВ" (standalone total)
                        is_main_total = False
                        exclude_words = ['БОДИТ', 'ДОТООД', 'УРТ ХУГАЦААНЫ', 'ХИЙГДЭХ', 'СУВГИЙН', 'НӨЛӨӨЛӨГЧ', 'КОНТЕНТ']
                        
                        if 'НИЙТ ТӨСӨВ' in row_text:
                            # Check it's not a subtotal
                            if not any(ex in row_text for ex in exclude_words):
                                is_main_total = True
                        
                        if is_main_total:
                            for i, val in enumerate(row_values):
                                if 'НИЙТ ТӨСӨВ' in val.upper() and 'БОДИТ' not in val.upper():
                                    # Look for number AFTER this label
                                    for j in range(i + 1, len(row_values)):
                                        cleaned = clean_currency_value(row_values[j])
                                        if cleaned and cleaned > 1000000:
                                            total_budget = cleaned
                                            break
                                    break
                            # If not found after label, check whole row
                            if total_budget is None:
                                for val in row_values:
                                    cleaned = clean_currency_value(val)
                                    if cleaned and cleaned > 1000000:
                                        total_budget = cleaned
                                        break
                    
                    # Stop if we found both values
                    if actual_budget is not None and total_budget is not None:
                        break
                
                # Search first 20 rows for metadata (code, brand)
                for idx in range(min(20, len(df))):
                    row = df.iloc[idx]
                    row_text = ' '.join([str(v) for v in row.values if pd.notna(v)])
                    
                    # Find budget code - look for patterns like "B2506E04" or "ТК-001"
                    if budget_code is None:
                        for val in row.values:
                            if pd.notna(val):
                                val_str = str(val).strip()
                                # Check if looks like a code (has numbers and letters or dashes)
                                if any(c.isdigit() for c in val_str) and (any(c.isalpha() for c in val_str) or '-' in val_str):
                                    if len(val_str) >= 4 and len(val_str) <= 30:
                                        if 'код' in row_text.lower() or 'code' in row_text.lower() or 'budget' in row_text.lower() or 'төсөв' in row_text.lower():
                                            budget_code = val_str
                                            break
                    
                    # Find brand - look for "Brand:", "Брэнд:" etc
                    if brand is None:
                        for i, val in enumerate(row.values):
                            if pd.notna(val):
                                val_str = str(val).lower()
                                if 'brand' in val_str or 'брэнд' in val_str:
                                    # Next non-empty cell might be the brand name
                                    for j in range(i+1, len(row.values)):
                                        next_val = row.values[j]
                                        if pd.notna(next_val) and str(next_val).strip():
                                            brand = str(next_val).strip()
                                            break
                                    break
                
                # If budget_code not found, try to find from filename
                if budget_code is None:
                    # Try to extract code from filename like "B2506E04_TOKI MOVIE.xlsx"
                    import re
                    match = re.search(r'([A-Z]\d{4}[A-Z]\d{2}|[A-Za-z0-9]+-\d+-\d+|[A-Za-z]{2,}-\d+)', uploaded_file.name)
                    if match:
                        budget_code = match.group(1)
                
                # If brand not found, try from filename
                if brand is None:
                    # Extract brand from filename (first part before underscore)
                    name_parts = uploaded_file.name.replace('.xlsx', '').replace('.xls', '').split('_')
                    if len(name_parts) > 1:
                        brand = name_parts[0]
                        
            except Exception as e:
                row_count = 0
                total_budget = None
                actual_budget = None
                budget_code = None
                brand = None
            
            # Create database record first
            budget_file = create_budget_file(
                filename=uploaded_file.name,
                budget_type=budget_type,
                uploader_id=user.id,
                row_count=row_count,
                total_amount=actual_budget,       # Нийт бодит төсөв
                planned_amount=total_budget,      # Нийт төсөв
                file_hash=file_hash,
                budget_code=budget_code,
                brand=brand,
                campaign_name=campaign_name,
                specialist_name=specialist_name,
                parent_file_id=parent_file_id
            )
            
            # Save Excel file to disk
            uploaded_file.seek(0)
            success, file_path, message = save_excel_file(
                uploaded_file,
                budget_file.id,
                user.username
            )
            
            if not success:
                st.error(f"❌ Файл хадгалахад алдаа: {message}")
                return
            
            # Update file path in database
            with get_session() as session:
                db_file = session.get(BudgetFile, budget_file.id)
                if db_file:
                    db_file.pdf_file_path = file_path  # Using this field for excel path
                    session.commit()
            
            # Show success
            st.balloons()
            st.success("🎉 **Файл амжилттай хуулагдлаа!**")
            
            # Show campaign info
            if campaign_name:
                budget_type_label = "Үндсэн төсөв" if budget_type == BudgetType.PRIMARY.value else "Нэмэлт төсөв"
                st.info(f"""
                **📋 Кампанит ажлын мэдээлэл:**
                - 🏷️ Төрөл: {budget_type_label}
                - 📌 Кампанит ажил: {campaign_name}
                - 👤 Мэргэжилтэн: {specialist_name or 'N/A'}
                {f"- 🔗 Холбосон үндсэн төсөв: #{parent_file_id}" if parent_file_id else ""}
                """)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                # Нийт бодит төсөв
                if actual_budget:
                    st.metric("Нийт бодит төсөв", f"₮{actual_budget:,.0f}")
                else:
                    st.metric("Нийт бодит төсөв", "N/A")
            with col2:
                # Нийт төсөв
                if total_budget:
                    st.metric("Нийт төсөв", f"₮{total_budget:,.0f}")
                else:
                    st.metric("Нийт төсөв", "N/A")
            with col3:
                st.metric("File ID", budget_file.id)
            
            # Generate and show PDF preview
            st.divider()
            st.subheader("📄 Файлын PDF Preview")
            
            with st.spinner("PDF үүсгэж байна..."):
                pdf_path = create_preview_pdf(file_path, budget_file.id)
            
            if pdf_path:
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
                else:
                    st.info("PDF preview ачааллах боломжгүй байна")
            else:
                st.info("PDF preview үүсгэх боломжгүй байна")
            
            st.divider()
            st.info(f"""
            **Дараагийн алхмууд:**
            1. ✅ Таны файл одоо БАТЛАХ ХҮЛЭЭЛТ төлөвтэй байна
            2. 👔 Менежер таны Excel файлыг шууд хянаж батална
            3. 📋 Менежер файлыг татаж, Excel дээр шууд үзэх боломжтой
            """)
            
            st.page_link("pages/1_🔄_Workflow.py", label="➡️ Ажлын урсгал руу очих", icon="🔄")
            
        except Exception as e:
            st.error(f"❌ Алдаа гарлаа: {str(e)}")
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

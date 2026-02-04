"""
Admin Panel - Reference Data Management
========================================

Admin болон Manager эрхтэй хэрэглэгчид энд:
- Channel Categories харах, нэмэх, засах
- Channel Activities харах, нэмэх, засах
- Budget Codes харах, нэмэх, засах
- Database stats харах

Author: CPP Development Team
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Admin Panel",
    page_icon="⚙️",
    layout="wide"
)

from sqlmodel import select
from database import (
    get_session, 
    BudgetCodeRef, 
    ChannelCategory, 
    ChannelActivity,
    CampaignType,
    ProductService,
    Approver,
    User,
    BudgetFile,
    BudgetItem,
    HeaderTemplate,
    CppBudgetItem
)
from modules.jwt_auth import (
    get_current_user_from_token,
    get_all_users,
    update_user_role,
    toggle_user_active,
    reset_user_password,
    require_role_jwt
)
from config import UserRole


def get_database_stats() -> dict:
    """Get counts of all tables."""
    with get_session() as session:
        return {
            "users": len(session.exec(select(User)).all()),
            "budget_files": len(session.exec(select(BudgetFile)).all()),
            "budget_items": len(session.exec(select(BudgetItem)).all()),
            "cpp_items": len(session.exec(select(CppBudgetItem)).all()),
            "categories": len(session.exec(select(ChannelCategory)).all()),
            "activities": len(session.exec(select(ChannelActivity)).all()),
            "budget_codes": len(session.exec(select(BudgetCodeRef)).all()),
            "campaign_types": len(session.exec(select(CampaignType)).all()),
            "products": len(session.exec(select(ProductService)).all()),
            "approvers": len(session.exec(select(Approver)).all()),
            "header_templates": len(session.exec(select(HeaderTemplate)).all()),
        }


# =============================================================================
# USER MANAGEMENT (Admin only)
# =============================================================================

def show_user_management():
    """User management interface - Admin only."""
    st.subheader("👥 Хэрэглэгч удирдах")
    
    # Check if current user is admin
    jwt_user = get_current_user_from_token()
    if not jwt_user or jwt_user.get('role', '').lower() != 'admin':
        st.error("❌ Зөвхөн Admin эрхтэй хэрэглэгч хандах боломжтой")
        return
    
    # Load all users
    users = get_all_users()
    
    if not users:
        st.info("Хэрэглэгч байхгүй байна")
        return
    
    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Нийт хэрэглэгч", len(users))
    with col2:
        admins = len([u for u in users if u['role'] == 'admin'])
        st.metric("👑 Admin", admins)
    with col3:
        managers = len([u for u in users if u['role'] == 'manager'])
        st.metric("👔 Manager", managers)
    with col4:
        planners = len([u for u in users if u['role'] == 'planner'])
        st.metric("📋 Planner", planners)
    
    st.divider()
    
    # Users table with actions
    st.markdown("##### 📋 Хэрэглэгчдийн жагсаалт")
    
    # Create DataFrame for display
    df_data = []
    for u in users:
        role_emoji = {"admin": "👑", "manager": "👔", "planner": "📋"}.get(u['role'], "👤")
        status_emoji = "✅" if u['is_active'] else "❌"
        last_login = u['last_login'].strftime("%Y-%m-%d %H:%M") if u['last_login'] else "Нэвтрээгүй"
        
        df_data.append({
            "ID": u['id'],
            "👤 Нэр": u['full_name'] or "-",
            "📧 Email": u['email'] or "-",
            "🔑 Username": u['username'],
            "Role": f"{role_emoji} {u['role'].title()}",
            "Төлөв": status_emoji,
            "Сүүлд нэвтэрсэн": last_login
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    st.divider()
    
    # User actions
    st.markdown("##### ⚙️ Хэрэглэгч засах")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Select user
        user_options = {f"{u['full_name'] or u['username']} ({u['email']})": u['id'] for u in users}
        selected_user_label = st.selectbox("Хэрэглэгч сонгох", options=list(user_options.keys()))
        
        if selected_user_label:
            selected_user_id = user_options[selected_user_label]
            selected_user = next((u for u in users if u['id'] == selected_user_id), None)
            
            if selected_user:
                st.info(f"📧 {selected_user['email']}\n👤 {selected_user['full_name']}\n🔑 Role: {selected_user['role']}")
    
    with col2:
        if selected_user_label and selected_user:
            # Role change
            st.markdown("**🔄 Role өөрчлөх:**")
            new_role = st.selectbox(
                "Шинэ role",
                options=["planner", "manager", "admin"],
                index=["planner", "manager", "admin"].index(selected_user['role']),
                key="new_role_select"
            )
            
            if st.button("💾 Role солих", width='stretch'):
                success, message = update_user_role(selected_user_id, new_role)
                if success:
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            
            st.divider()
            
            # Toggle active status
            current_status = "Идэвхтэй ✅" if selected_user['is_active'] else "Идэвхгүй ❌"
            st.markdown(f"**📌 Төлөв:** {current_status}")
            
            toggle_label = "🔴 Идэвхгүй болгох" if selected_user['is_active'] else "🟢 Идэвхжүүлэх"
            if st.button(toggle_label, width='stretch'):
                success, message = toggle_user_active(selected_user_id)
                if success:
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    st.divider()
    
    # Password reset section
    st.markdown("##### 🔑 Нууц үг шинэчлэх")
    
    col1, col2 = st.columns(2)
    
    with col1:
        reset_user_label = st.selectbox(
            "Хэрэглэгч сонгох",
            options=list(user_options.keys()),
            key="reset_user_select"
        )
    
    with col2:
        new_password = st.text_input(
            "Шинэ нууц үг",
            type="password",
            placeholder="Хамгийн багадаа 6 тэмдэгт",
            key="new_password_input"
        )
    
    if st.button("🔄 Нууц үг шинэчлэх", type="primary"):
        if reset_user_label and new_password:
            reset_user_id = user_options[reset_user_label]
            success, message = reset_user_password(reset_user_id, new_password)
            if success:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")
        else:
            st.warning("Хэрэглэгч болон шинэ нууц үг оруулна уу")


def show_categories_management():
    """Channel Categories CRUD interface."""
    st.subheader("📁 Channel Categories")
    
    # Load data
    with get_session() as session:
        categories = session.exec(
            select(ChannelCategory).order_by(ChannelCategory.display_order)
        ).all()
        
        # Convert to DataFrame
        data = []
        for cat in categories:
            activities_count = len(session.exec(
                select(ChannelActivity).where(ChannelActivity.category_id == cat.id)
            ).all())
            data.append({
                "ID": cat.id,
                "Нэр": cat.name,
                "Тайлбар": cat.description or "",
                "Дараалал": cat.display_order,
                "Activities": activities_count,
                "Идэвхтэй": "✅" if cat.is_active else "❌"
            })
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("Категори байхгүй байна")
    
    # Add new category
    st.divider()
    st.markdown("##### ➕ Шинэ категори нэмэх")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_cat_name = st.text_input("Категорийн нэр", key="new_cat_name")
    with col2:
        new_cat_desc = st.text_input("Тайлбар (English)", key="new_cat_desc")
    with col3:
        new_cat_order = st.number_input("Дараалал", min_value=1, value=len(data) + 1, key="new_cat_order")
    
    if st.button("➕ Категори нэмэх", type="primary"):
        if new_cat_name:
            with get_session() as session:
                # Check if exists
                existing = session.exec(
                    select(ChannelCategory).where(ChannelCategory.name == new_cat_name)
                ).first()
                
                if existing:
                    st.error(f"'{new_cat_name}' нэртэй категори аль хэдийн байна!")
                else:
                    new_category = ChannelCategory(
                        name=new_cat_name,
                        description=new_cat_desc,
                        display_order=new_cat_order,
                        is_active=True
                    )
                    session.add(new_category)
                    session.commit()
                    st.success(f"✅ '{new_cat_name}' категори амжилттай нэмэгдлээ!")
                    st.rerun()
        else:
            st.warning("Категорийн нэр оруулна уу")
    
    # Delete category
    st.divider()
    st.markdown("##### 🗑️ Категори устгах")
    
    if data:
        cat_delete_options = {f"{d['ID']}. {d['Нэр']} ({d['Activities']} activities)": d['ID'] for d in data}
        selected_delete_cat = st.selectbox(
            "Устгах категори сонгох",
            options=list(cat_delete_options.keys()),
            key="delete_cat_select"
        )
        selected_delete_cat_id = cat_delete_options[selected_delete_cat]
        
        # Check if has activities
        has_activities = next((d['Activities'] for d in data if d['ID'] == selected_delete_cat_id), 0) > 0
        
        if has_activities:
            st.warning("⚠️ Энэ категорид activities байгаа тул эхлээд activities-г устгана уу")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🗑️ Устгах", type="secondary", key="delete_cat_btn", disabled=has_activities):
                with get_session() as session:
                    cat_to_delete = session.get(ChannelCategory, selected_delete_cat_id)
                    if cat_to_delete:
                        session.delete(cat_to_delete)
                        session.commit()
                        st.success(f"✅ Категори устгагдлаа!")
                        st.rerun()


def show_activities_management():
    """Channel Activities CRUD interface."""
    st.subheader("📋 Channel Activities")
    
    # Load categories for filter
    with get_session() as session:
        categories = session.exec(
            select(ChannelCategory).order_by(ChannelCategory.display_order)
        ).all()
    
    if not categories:
        st.warning("Эхлээд категори нэмнэ үү")
        return
    
    # Category filter
    cat_options = {f"{c.id}. {c.name}": c.id for c in categories}
    selected_cat = st.selectbox(
        "Категори сонгох",
        options=list(cat_options.keys()),
        key="activity_cat_filter"
    )
    selected_cat_id = cat_options[selected_cat]
    selected_cat_name = selected_cat.split(". ", 1)[1]
    
    # Load activities for selected category
    with get_session() as session:
        activities = session.exec(
            select(ChannelActivity)
            .where(ChannelActivity.category_id == selected_cat_id)
            .order_by(ChannelActivity.name)
        ).all()
        
        data = []
        for act in activities:
            data.append({
                "ID": act.id,
                "Нэр": act.name,
                "Тайлбар": act.description or "",
                "Идэвхтэй": "✅" if act.is_active else "❌"
            })
    
    st.markdown(f"**{selected_cat_name}** - {len(data)} activities")
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("Энэ категорид activity байхгүй байна")
    
    # Add new activity
    st.divider()
    st.markdown("##### ➕ Шинэ activity нэмэх")
    
    col1, col2 = st.columns([2, 2])
    with col1:
        new_act_name = st.text_input("Activity нэр", key="new_act_name")
    with col2:
        new_act_desc = st.text_input("Тайлбар", key="new_act_desc")
    
    if st.button("➕ Activity нэмэх", type="primary", key="add_activity_btn"):
        if new_act_name:
            with get_session() as session:
                # Check if exists
                existing = session.exec(
                    select(ChannelActivity).where(
                        ChannelActivity.category_id == selected_cat_id,
                        ChannelActivity.name == new_act_name
                    )
                ).first()
                
                if existing:
                    st.error(f"'{new_act_name}' нэртэй activity аль хэдийн байна!")
                else:
                    new_activity = ChannelActivity(
                        category_id=selected_cat_id,
                        name=new_act_name,
                        description=new_act_desc,
                        is_active=True
                    )
                    session.add(new_activity)
                    session.commit()
                    st.success(f"✅ '{new_act_name}' activity амжилттай нэмэгдлээ!")
                    st.rerun()
        else:
            st.warning("Activity нэр оруулна уу")
    
    # Bulk add activities
    st.divider()
    st.markdown("##### 📝 Олон activity нэг дор нэмэх")
    st.caption("Мөр бүрт нэг activity бичнэ үү")
    
    bulk_activities = st.text_area(
        "Activities (мөр бүрт нэг)",
        height=150,
        key="bulk_activities",
        placeholder="Activity 1\nActivity 2\nActivity 3"
    )
    
    if st.button("📝 Бүгдийг нэмэх", key="bulk_add_btn"):
        if bulk_activities:
            lines = [line.strip() for line in bulk_activities.split("\n") if line.strip()]
            added = 0
            skipped = 0
            
            with get_session() as session:
                for act_name in lines:
                    existing = session.exec(
                        select(ChannelActivity).where(
                            ChannelActivity.category_id == selected_cat_id,
                            ChannelActivity.name == act_name
                        )
                    ).first()
                    
                    if not existing:
                        new_activity = ChannelActivity(
                            category_id=selected_cat_id,
                            name=act_name,
                            is_active=True
                        )
                        session.add(new_activity)
                        added += 1
                    else:
                        skipped += 1
                
                session.commit()
            
            st.success(f"✅ {added} activity нэмэгдлээ, {skipped} давхардсан")
            st.rerun()
    
    # Delete activity
    st.divider()
    st.markdown("##### 🗑️ Activity устгах")
    
    if data:
        act_delete_options = {f"{d['ID']}. {d['Нэр']}": d['ID'] for d in data}
        selected_delete_act = st.selectbox(
            "Устгах activity сонгох",
            options=list(act_delete_options.keys()),
            key="delete_act_select"
        )
        selected_delete_act_id = act_delete_options[selected_delete_act]
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🗑️ Устгах", type="secondary", key="delete_act_btn"):
                with get_session() as session:
                    act_to_delete = session.get(ChannelActivity, selected_delete_act_id)
                    if act_to_delete:
                        session.delete(act_to_delete)
                        session.commit()
                        st.success(f"✅ Activity устгагдлаа!")
                        st.rerun()
        with col2:
            if st.button("🗑️ Энэ категорийн бүх activity устгах", type="secondary", key="delete_all_acts_btn"):
                with get_session() as session:
                    activities_to_delete = session.exec(
                        select(ChannelActivity).where(ChannelActivity.category_id == selected_cat_id)
                    ).all()
                    for act in activities_to_delete:
                        session.delete(act)
                    session.commit()
                    st.success(f"✅ {len(activities_to_delete)} activity устгагдлаа!")
                    st.rerun()


def show_budget_codes_management():
    """Budget Codes CRUD interface."""
    st.subheader("💰 Budget Codes")
    
    # Load data
    with get_session() as session:
        codes = session.exec(
            select(BudgetCodeRef).order_by(BudgetCodeRef.code)
        ).all()
        
        data = []
        for code in codes:
            data.append({
                "ID": code.id,
                "Код": code.code,
                "Тайлбар": code.description or "",
                "Брэнд": code.brand or "",
                "Жил": code.year,
                "Идэвхтэй": "✅" if code.is_active else "❌"
            })
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, width='stretch', hide_index=True, height=400)
    else:
        st.info("Budget code байхгүй байна")
    
    # Add new code
    st.divider()
    st.markdown("##### ➕ Шинэ budget code нэмэх")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_code = st.text_input("Budget Code", placeholder="MD-BRANDING-MB1-110010001", key="new_budget_code")
    with col2:
        new_code_desc = st.text_input("Тайлбар", key="new_code_desc")
    with col3:
        new_code_year = st.number_input("Жил", min_value=2020, max_value=2030, value=2025, key="new_code_year")
    
    col4, col5 = st.columns([2, 2])
    with col4:
        new_code_brand = st.text_input("Брэнд", key="new_code_brand")
    with col5:
        new_code_dept = st.text_input("Департмент", key="new_code_dept")
    
    if st.button("➕ Budget Code нэмэх", type="primary", key="add_code_btn"):
        if new_code:
            with get_session() as session:
                existing = session.exec(
                    select(BudgetCodeRef).where(BudgetCodeRef.code == new_code)
                ).first()
                
                if existing:
                    st.error(f"'{new_code}' код аль хэдийн байна!")
                else:
                    new_budget_code = BudgetCodeRef(
                        code=new_code,
                        description=new_code_desc,
                        brand=new_code_brand,
                        department=new_code_dept,
                        year=new_code_year,
                        is_active=True
                    )
                    session.add(new_budget_code)
                    session.commit()
                    st.success(f"✅ '{new_code}' код амжилттай нэмэгдлээ!")
                    st.rerun()
        else:
            st.warning("Budget code оруулна уу")
    
    # Delete budget code
    st.divider()
    st.markdown("##### 🗑️ Budget Code устгах")
    
    if data:
        code_delete_options = {f"{d['ID']}. {d['Код']}": d['ID'] for d in data}
        selected_delete_code = st.selectbox(
            "Устгах code сонгох",
            options=list(code_delete_options.keys()),
            key="delete_code_select"
        )
        selected_delete_code_id = code_delete_options[selected_delete_code]
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🗑️ Устгах", type="secondary", key="delete_code_btn"):
                with get_session() as session:
                    code_to_delete = session.get(BudgetCodeRef, selected_delete_code_id)
                    if code_to_delete:
                        session.delete(code_to_delete)
                        session.commit()
                        st.success(f"✅ Budget code устгагдлаа!")
                        st.rerun()


def show_campaign_types_management():
    """Campaign Types CRUD interface."""
    st.subheader("🏷️ Campaign Types (Төрөл)")
    
    # Load data
    with get_session() as session:
        types = session.exec(
            select(CampaignType).order_by(CampaignType.display_order)
        ).all()
        
        data = []
        for t in types:
            data.append({
                "ID": t.id,
                "Нэр": t.name,
                "Тайлбар": t.description or "",
                "Дараалал": t.display_order,
                "Идэвхтэй": "✅" if t.is_active else "❌"
            })
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("Campaign type байхгүй байна")
    
    # Add new type
    st.divider()
    st.markdown("##### ➕ Шинэ төрөл нэмэх")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_type_name = st.text_input("Төрлийн нэр", key="new_type_name")
    with col2:
        new_type_desc = st.text_input("Тайлбар", key="new_type_desc")
    with col3:
        new_type_order = st.number_input("Дараалал", min_value=1, value=len(data) + 1, key="new_type_order")
    
    if st.button("➕ Төрөл нэмэх", type="primary", key="add_type_btn"):
        if new_type_name:
            with get_session() as session:
                existing = session.exec(
                    select(CampaignType).where(CampaignType.name == new_type_name)
                ).first()
                
                if existing:
                    st.error(f"'{new_type_name}' нэртэй төрөл аль хэдийн байна!")
                else:
                    new_type = CampaignType(
                        name=new_type_name,
                        description=new_type_desc,
                        display_order=new_type_order,
                        is_active=True
                    )
                    session.add(new_type)
                    session.commit()
                    st.success(f"✅ '{new_type_name}' төрөл амжилттай нэмэгдлээ!")
                    st.rerun()
        else:
            st.warning("Төрлийн нэр оруулна уу")
    
    # Delete campaign type
    st.divider()
    st.markdown("##### 🗑️ Төрөл устгах")
    
    if data:
        type_delete_options = {f"{d['ID']}. {d['Нэр']}": d['ID'] for d in data}
        selected_delete_type = st.selectbox(
            "Устгах төрөл сонгох",
            options=list(type_delete_options.keys()),
            key="delete_type_select"
        )
        selected_delete_type_id = type_delete_options[selected_delete_type]
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🗑️ Устгах", type="secondary", key="delete_type_btn"):
                with get_session() as session:
                    type_to_delete = session.get(CampaignType, selected_delete_type_id)
                    if type_to_delete:
                        session.delete(type_to_delete)
                        session.commit()
                        st.success(f"✅ Төрөл устгагдлаа!")
                        st.rerun()


def show_products_management():
    """Products & Services CRUD interface."""
    st.subheader("📦 Products & Services (Бүтээгдэхүүн)")
    
    # Load data
    with get_session() as session:
        products = session.exec(
            select(ProductService).order_by(ProductService.display_order)
        ).all()
        
        data = []
        for p in products:
            data.append({
                "ID": p.id,
                "Нэр": p.name,
                "Тайлбар": p.description or "",
                "Дараалал": p.display_order,
                "Идэвхтэй": "✅" if p.is_active else "❌"
            })
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, width='stretch', hide_index=True, height=400)
    else:
        st.info("Product байхгүй байна")
    
    # Add new product
    st.divider()
    st.markdown("##### ➕ Шинэ бүтээгдэхүүн нэмэх")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_prod_name = st.text_input("Бүтээгдэхүүний нэр", key="new_prod_name")
    with col2:
        new_prod_desc = st.text_input("Тайлбар", key="new_prod_desc")
    with col3:
        new_prod_order = st.number_input("Дараалал", min_value=1, value=len(data) + 1, key="new_prod_order")
    
    if st.button("➕ Бүтээгдэхүүн нэмэх", type="primary", key="add_prod_btn"):
        if new_prod_name:
            with get_session() as session:
                existing = session.exec(
                    select(ProductService).where(ProductService.name == new_prod_name)
                ).first()
                
                if existing:
                    st.error(f"'{new_prod_name}' нэртэй бүтээгдэхүүн аль хэдийн байна!")
                else:
                    new_product = ProductService(
                        name=new_prod_name,
                        description=new_prod_desc,
                        display_order=new_prod_order,
                        is_active=True
                    )
                    session.add(new_product)
                    session.commit()
                    st.success(f"✅ '{new_prod_name}' бүтээгдэхүүн амжилттай нэмэгдлээ!")
                    st.rerun()
        else:
            st.warning("Бүтээгдэхүүний нэр оруулна уу")
    
    # Delete product
    st.divider()
    st.markdown("##### 🗑️ Бүтээгдэхүүн устгах")
    
    if data:
        prod_delete_options = {f"{d['ID']}. {d['Нэр']}": d['ID'] for d in data}
        selected_delete_prod = st.selectbox(
            "Устгах бүтээгдэхүүн сонгох",
            options=list(prod_delete_options.keys()),
            key="delete_prod_select"
        )
        selected_delete_prod_id = prod_delete_options[selected_delete_prod]
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🗑️ Устгах", type="secondary", key="delete_prod_btn"):
                with get_session() as session:
                    prod_to_delete = session.get(ProductService, selected_delete_prod_id)
                    if prod_to_delete:
                        session.delete(prod_to_delete)
                        session.commit()
                        st.success(f"✅ Бүтээгдэхүүн устгагдлаа!")
                        st.rerun()


def show_approvers_management():
    """Approvers CRUD interface."""
    st.subheader("✍️ Approvers (Батлах эрхтэй)")
    
    # Load data
    with get_session() as session:
        approvers = session.exec(
            select(Approver).order_by(Approver.approval_level)
        ).all()
        
        data = []
        for a in approvers:
            data.append({
                "ID": a.id,
                "Нэр": a.name,
                "Албан тушаал": a.position or "",
                "Түвшин": a.approval_level,
                "Идэвхтэй": "✅" if a.is_active else "❌"
            })
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("Approver байхгүй байна")
    
    # Add new approver
    st.divider()
    st.markdown("##### ➕ Шинэ approver нэмэх")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_appr_name = st.text_input("Нэр", key="new_appr_name")
    with col2:
        new_appr_pos = st.text_input("Албан тушаал", key="new_appr_pos")
    with col3:
        new_appr_level = st.number_input("Түвшин", min_value=1, max_value=10, value=1, key="new_appr_level")
    
    if st.button("➕ Approver нэмэх", type="primary", key="add_appr_btn"):
        if new_appr_name:
            with get_session() as session:
                existing = session.exec(
                    select(Approver).where(Approver.name == new_appr_name)
                ).first()
                
                if existing:
                    st.error(f"'{new_appr_name}' нэртэй approver аль хэдийн байна!")
                else:
                    new_approver = Approver(
                        name=new_appr_name,
                        position=new_appr_pos,
                        approval_level=new_appr_level,
                        is_active=True
                    )
                    session.add(new_approver)
                    session.commit()
                    st.success(f"✅ '{new_appr_name}' approver амжилттай нэмэгдлээ!")
                    st.rerun()
        else:
            st.warning("Approver нэр оруулна уу")
    
    # Delete approver
    st.divider()
    st.markdown("##### 🗑️ Approver устгах")
    
    if data:
        appr_delete_options = {f"{d['ID']}. {d['Нэр']} ({d['Албан тушаал']})": d['ID'] for d in data}
        selected_delete_appr = st.selectbox(
            "Устгах approver сонгох",
            options=list(appr_delete_options.keys()),
            key="delete_appr_select"
        )
        selected_delete_appr_id = appr_delete_options[selected_delete_appr]
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🗑️ Устгах", type="secondary", key="delete_appr_btn"):
                with get_session() as session:
                    appr_to_delete = session.get(Approver, selected_delete_appr_id)
                    if appr_to_delete:
                        session.delete(appr_to_delete)
                        session.commit()
                        st.success(f"✅ Approver устгагдлаа!")
                        st.rerun()


def show_header_templates_management():
    """Header Templates CRUD interface - Dynamic headers for CPP and Excel."""
    st.subheader("📑 Header Templates")
    st.caption("CPP болон Excel upload-ийн header-үүдийг динамикаар удирдах")
    
    # Template type selector
    template_type = st.radio(
        "Template төрөл",
        ["cpp", "excel"],
        horizontal=True,
        format_func=lambda x: "CPP (UI)" if x == "cpp" else "Excel Upload"
    )
    
    st.divider()
    
    # Load headers
    with get_session() as session:
        headers = session.exec(
            select(HeaderTemplate)
            .where(HeaderTemplate.template_type == template_type)
            .order_by(HeaderTemplate.display_order)
        ).all()
        
        data = []
        for h in headers:
            data.append({
                "ID": h.id,
                "Column Key": h.column_key,
                "Display Name": h.display_name,
                "Type": h.column_type,
                "Order": h.display_order,
                "Required": "✅" if h.is_required else "",
                "Active": "✅" if h.is_active else "❌"
            })
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info(f"{template_type.upper()} template-д header байхгүй байна")
    
    # Add new header
    st.divider()
    st.markdown("##### ➕ Шинэ header нэмэх")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        new_column_key = st.text_input("Column Key (English)", placeholder="unit_price", key="new_header_key")
    with col2:
        new_display_name = st.text_input("Display Name", placeholder="Нэгж үнэ", key="new_header_name")
    with col3:
        new_column_type = st.selectbox("Type", ["text", "number", "date", "dropdown"], key="new_header_type")
    
    col4, col5, col6 = st.columns(3)
    with col4:
        new_order = st.number_input("Display Order", min_value=1, value=len(data) + 1, key="new_header_order")
    with col5:
        new_required = st.checkbox("Required?", key="new_header_required")
    with col6:
        new_dropdown_options = st.text_input("Dropdown options (comma-separated)", key="new_header_dropdown", 
                                              disabled=(new_column_type != "dropdown"))
    
    if st.button("➕ Header нэмэх", type="primary", key="add_header_btn"):
        if new_column_key and new_display_name:
            with get_session() as session:
                # Check if exists
                existing = session.exec(
                    select(HeaderTemplate).where(
                        HeaderTemplate.template_type == template_type,
                        HeaderTemplate.column_key == new_column_key
                    )
                ).first()
                
                if existing:
                    st.error(f"'{new_column_key}' key аль хэдийн байна!")
                else:
                    import json
                    dropdown_json = None
                    if new_column_type == "dropdown" and new_dropdown_options:
                        options_list = [o.strip() for o in new_dropdown_options.split(",")]
                        dropdown_json = json.dumps(options_list, ensure_ascii=False)
                    
                    new_header = HeaderTemplate(
                        template_type=template_type,
                        column_key=new_column_key,
                        display_name=new_display_name,
                        column_type=new_column_type,
                        display_order=new_order,
                        is_required=new_required,
                        dropdown_options=dropdown_json,
                        is_active=True
                    )
                    session.add(new_header)
                    session.commit()
                    st.success(f"✅ '{new_display_name}' header нэмэгдлээ!")
                    st.rerun()
        else:
            st.warning("Column key болон Display name оруулна уу")
    
    # Edit existing header
    if data:
        st.divider()
        st.markdown("##### ✏️ Header засах")
        
        header_options = {f"{d['ID']}. {d['Display Name']} ({d['Column Key']})": d['ID'] for d in data}
        selected_header = st.selectbox(
            "Засах header сонгох",
            options=list(header_options.keys()),
            key="edit_header_select"
        )
        selected_header_id = header_options[selected_header]
        
        # Get current values
        with get_session() as session:
            current_header = session.get(HeaderTemplate, selected_header_id)
        
        if current_header:
            col1, col2 = st.columns(2)
            with col1:
                edit_display_name = st.text_input("Display Name", value=current_header.display_name, key="edit_header_name")
                edit_order = st.number_input("Display Order", value=current_header.display_order, key="edit_header_order")
            with col2:
                edit_type = st.selectbox("Type", ["text", "number", "date", "dropdown"], 
                                         index=["text", "number", "date", "dropdown"].index(current_header.column_type),
                                         key="edit_header_type")
                edit_required = st.checkbox("Required?", value=current_header.is_required, key="edit_header_required")
                edit_active = st.checkbox("Active?", value=current_header.is_active, key="edit_header_active")
            
            if st.button("💾 Хадгалах", key="save_header_btn"):
                with get_session() as session:
                    header = session.get(HeaderTemplate, selected_header_id)
                    if header:
                        header.display_name = edit_display_name
                        header.display_order = edit_order
                        header.column_type = edit_type
                        header.is_required = edit_required
                        header.is_active = edit_active
                        session.add(header)
                        session.commit()
                        st.success("✅ Header шинэчлэгдлээ!")
                        st.rerun()
    
    # Delete header
    if data:
        st.divider()
        st.markdown("##### 🗑️ Header устгах")
        
        header_delete_options = {f"{d['ID']}. {d['Display Name']}": d['ID'] for d in data}
        selected_delete = st.selectbox(
            "Устгах header сонгох",
            options=list(header_delete_options.keys()),
            key="delete_header_select"
        )
        selected_delete_id = header_delete_options[selected_delete]
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🗑️ Устгах", type="secondary", key="delete_header_btn"):
                with get_session() as session:
                    header_to_delete = session.get(HeaderTemplate, selected_delete_id)
                    if header_to_delete:
                        session.delete(header_to_delete)
                        session.commit()
                        st.success(f"✅ Header устгагдлаа!")
                        st.rerun()


def show_database_overview():
    """Database overview and stats."""
    st.subheader("📊 Database Overview")
    
    stats = get_database_stats()
    
    # Stats cards - Reference Data
    st.markdown("##### 📚 Reference Data")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📁 Categories", stats["categories"])
        st.metric("📋 Activities", stats["activities"])
    with col2:
        st.metric("💰 Budget Codes", stats["budget_codes"])
        st.metric("🏷️ Campaign Types", stats["campaign_types"])
    with col3:
        st.metric("📦 Products", stats["products"])
        st.metric("✍️ Approvers", stats["approvers"])
    with col4:
        st.metric("👥 Хэрэглэгчид", stats["users"])
        st.metric("� Header Templates", stats["header_templates"])
    
    st.divider()
    
    # Transaction data
    st.markdown("##### 📊 Transaction Data")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Budget Files", stats["budget_files"])
    with col2:
        st.metric("📝 Excel Items", stats["budget_items"])
    with col3:
        st.metric("📋 CPP Items", stats["cpp_items"])
    
    st.divider()
    
    # Seed reference data
    st.markdown("##### 🌱 Reference Data Seed")
    st.caption("Master Excel файлаас эсвэл hardcoded өгөгдлөөс seed хийх")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🌱 Бүх Reference Data Seed", type="secondary"):
            from modules.seeder import seed_all_reference_data
            with st.spinner("Seed хийж байна..."):
                result = seed_all_reference_data()
            st.success(f"""✅ Seed амжилттай:
            - Categories: {result['categories']}
            - Activities: {result['activities']}
            - Campaign Types: {result['campaign_types']}
            - Products: {result['products']}
            - Approvers: {result['approvers']}
            """)
            st.rerun()
    
    with col2:
        if st.button("🗑️ Reference Data Устгах", type="secondary"):
            st.warning("⚠️ Энэ үйлдэл бүх reference data устгана!")
            if st.button("Тийм, устгах", key="confirm_delete"):
                from modules.seeder import clear_reference_data
                clear_reference_data()
                st.success("✅ Бүх reference data устгагдлаа")
                st.rerun()


def main():
    """Main admin page."""
    
    st.title("⚙️ Admin Panel")
    st.caption("Reference Data Management")
    
    # Check JWT authentication
    jwt_user = get_current_user_from_token()
    if not jwt_user:
        st.warning("🔐 Нэвтрэх шаардлагатай")
        st.info("👈 Зүүн талын цэснээс **🏠 Home** хуудас руу очиж нэвтэрнэ үү.")
        if st.button("🔐 Нэвтрэх хуудас руу очих"):
            st.switch_page("app.py")
        return
    
    # Get user from database for full object
    with get_session() as session:
        user = session.get(User, int(jwt_user['id']))
    
    if not user:
        st.warning("🔐 Нэвтэрнэ үү")
        st.page_link("app.py", label="🏠 Нүүр хуудас руу буцах")
        return
    
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        st.error("❌ Таны эрх хүрэлцэхгүй байна. Зөвхөн Admin болон Manager эрхтэй хүмүүс хандах боломжтой.")
        return
    
    st.success(f"Нэвтэрсэн: **{user.full_name or user.username}** ({user.role.value})")
    
    st.divider()
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 Overview",
        "👥 Users",
        "📁 Categories", 
        "📋 Activities",
        "💰 Budget Codes",
        "🏷️ Types",
        "📦 Products",
        "✍️ Approvers",
        "📑 Headers"
    ])
    
    with tab1:
        show_database_overview()
    
    with tab2:
        show_user_management()
    
    with tab3:
        show_categories_management()
    
    with tab4:
        show_activities_management()
    
    with tab5:
        show_budget_codes_management()
    
    with tab6:
        show_campaign_types_management()
    
    with tab7:
        show_products_management()
    
    with tab8:
        show_approvers_management()
    
    with tab9:
        show_header_templates_management()


if __name__ == "__main__":
    main()

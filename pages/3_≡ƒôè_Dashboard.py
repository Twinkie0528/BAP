"""
CPP Dashboard - Page 3
======================

Budget Dashboard with Row-Level Security:
- ALL users can VIEW all data (Global Visibility)
- Users can EDIT only their own rows (specialist == current_user)
- Visual highlighting for user's own rows
- Backend verification before saving

Author: CPP Development Team
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from sqlmodel import select, Session

# Import our modules
import sys
sys.path.append('..')
from config import FileStatus, ChannelType
from database.connection import get_session, engine
from database.models import BudgetFile, BudgetItem, User


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="CPP Dashboard",
    page_icon="📊",
    layout="wide"
)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize session state with demo user if not logged in."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None


# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_all_budget_items() -> pd.DataFrame:
    """
    Load ALL budget items from FINALIZED files only.
    
    Dashboard Rule: Only show data where status = 'FINALIZED'.
    This ensures only completed, signed budgets appear on the dashboard.
    
    Returns:
        DataFrame with all budget items from finalized files
    """
    with get_session() as session:
        # Join BudgetItem with BudgetFile and User to get specialist name
        statement = select(
            BudgetItem.id,
            BudgetItem.file_id,
            BudgetItem.row_number,
            BudgetItem.campaign_name,
            BudgetItem.budget_code,
            BudgetItem.vendor,
            BudgetItem.channel,
            BudgetItem.sub_channel,
            BudgetItem.amount_planned,
            BudgetItem.start_date,
            BudgetItem.end_date,
            BudgetItem.metric_1,
            BudgetItem.metric_2,
            BudgetItem.metric_3,
            BudgetItem.description,
            BudgetItem.created_at,
            BudgetItem.specialist,  # Use specialist from BudgetItem
            BudgetFile.filename,
            BudgetFile.status,
            User.full_name.label('specialist_name')
        ).join(
            BudgetFile, BudgetItem.file_id == BudgetFile.id
        ).join(
            User, BudgetFile.uploader_id == User.id
        ).where(
            # CRITICAL: Only show FINALIZED items (Stage 4 complete)
            BudgetFile.status == FileStatus.FINALIZED
        )
        
        results = session.exec(statement).all()
        
        if not results:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame([dict(row._mapping) for row in results])
        
        # Convert channel enum to string
        if 'channel' in df.columns:
            df['channel'] = df['channel'].apply(lambda x: x.value if x else None)
        
        # Convert status enum to string
        if 'status' in df.columns:
            df['status'] = df['status'].apply(lambda x: x.value if x else None)
        
        # Format amount for display
        if 'amount_planned' in df.columns:
            df['amount_planned'] = pd.to_numeric(df['amount_planned'], errors='coerce')
        
        # Use specialist from BudgetItem if available, otherwise fall back to username
        if 'specialist' not in df.columns or df['specialist'].isna().all():
            # If specialist column doesn't exist or is empty, we need to add it
            # This is for backwards compatibility
            pass
        
        return df


def load_all_budget_items_simple() -> pd.DataFrame:
    """
    Simplified version - Load all budget items without complex joins.
    Use this if the joined query causes issues.
    """
    with get_session() as session:
        # Get all budget items
        items = session.exec(select(BudgetItem)).all()
        
        if not items:
            return pd.DataFrame()
        
        # Convert to list of dicts
        data = []
        for item in items:
            item_dict = {
                'id': item.id,
                'file_id': item.file_id,
                'campaign_name': item.campaign_name,
                'budget_code': item.budget_code,
                'vendor': item.vendor,
                'channel': item.channel.value if item.channel else None,
                'sub_channel': item.sub_channel,
                'amount_planned': float(item.amount_planned) if item.amount_planned else None,
                'start_date': item.start_date,
                'end_date': item.end_date,
                'metric_1': item.metric_1,
                'metric_2': item.metric_2,
                'description': item.description,
            }
            
            # Get specialist from file
            if item.budget_file:
                item_dict['specialist'] = item.budget_file.uploader.username if item.budget_file.uploader else 'Unknown'
            else:
                item_dict['specialist'] = 'Unknown'
            
            data.append(item_dict)
        
        return pd.DataFrame(data)


# =============================================================================
# AGGRID CONFIGURATION WITH ROW-LEVEL SECURITY
# =============================================================================

def create_secure_aggrid(df: pd.DataFrame, current_username: str):
    """
    Create AgGrid with row-level editing security.
    
    - ALL rows are visible to everyone
    - Only rows where specialist == current_username are editable
    - Visual highlighting for user's own rows
    
    Args:
        df: DataFrame with all budget items
        current_username: Currently logged-in user's username
    
    Returns:
        AgGrid response with user interactions
    """
    
    # ===================
    # JSCODE: Editable Function
    # ===================
    # This function determines if a cell is editable
    # Returns true only if the row's 'specialist' matches current user
    
    cell_editable_js = JsCode(f"""
    function(params) {{
        // Check if this row belongs to current user
        if (params.data && params.data.specialist) {{
            return params.data.specialist === '{current_username}';
        }}
        return false;
    }}
    """)
    
    # ===================
    # JSCODE: Row Styling
    # ===================
    # Highlight rows that belong to current user with light green background
    
    row_style_js = JsCode(f"""
    function(params) {{
        if (params.data && params.data.specialist === '{current_username}') {{
            return {{
                'backgroundColor': '#d4edda',  // Light green
                'borderLeft': '4px solid #28a745'  // Green left border
            }};
        }}
        return null;
    }}
    """)
    
    # ===================
    # JSCODE: Cell Styling for Non-Editable
    # ===================
    # Gray out cells that user cannot edit
    
    cell_style_js = JsCode(f"""
    function(params) {{
        if (params.data && params.data.specialist !== '{current_username}') {{
            return {{
                'backgroundColor': '#f8f9fa',  // Light gray
                'color': '#6c757d'  // Gray text
            }};
        }}
        return null;
    }}
    """)
    
    # ===================
    # Grid Options Builder
    # ===================
    
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # Default column settings
    gb.configure_default_column(
        resizable=True,
        filterable=True,
        sortable=True,
        editable=False,  # Default: not editable
        cellStyle=cell_style_js
    )
    
    # ID column - hidden but needed for updates
    gb.configure_column(
        'id',
        hide=True,
        editable=False
    )
    
    # File ID - hidden
    gb.configure_column(
        'file_id',
        hide=True,
        editable=False
    )
    
    # Specialist column - READ ONLY (shows who owns the row)
    gb.configure_column(
        'specialist',
        headerName='👤 Мэргэжилтэн',
        editable=False,
        pinned='left',
        width=120,
        cellStyle={'fontWeight': 'bold'}
    )
    
    # Campaign Name - Editable by owner
    gb.configure_column(
        'campaign_name',
        headerName='Кампанит ажил',
        editable=cell_editable_js,
        width=200
    )
    
    # Budget Code - Editable by owner
    gb.configure_column(
        'budget_code',
        headerName='Төсвийн код',
        editable=cell_editable_js,
        width=120
    )
    
    # Vendor - Editable by owner
    gb.configure_column(
        'vendor',
        headerName='Нийлүүлэгч',
        editable=cell_editable_js,
        width=150
    )
    
    # Channel - Read only (set during upload)
    gb.configure_column(
        'channel',
        headerName='Сувag',
        editable=False,
        width=100
    )
    
    # Amount - Editable by owner (main field to edit)
    gb.configure_column(
        'amount_planned',
        headerName='💰 Дүн',
        editable=cell_editable_js,
        type=['numericColumn'],
        valueFormatter=JsCode("""
        function(params) {
            if (params.value != null) {
                return '₮' + params.value.toLocaleString();
            }
            return '';
        }
        """),
        width=130
    )
    
    # Dates - Editable by owner
    gb.configure_column(
        'start_date',
        headerName='Эхлэх огноо',
        editable=cell_editable_js,
        type=['dateColumn'],
        width=120
    )
    
    gb.configure_column(
        'end_date',
        headerName='Дуусах огноо',
        editable=cell_editable_js,
        type=['dateColumn'],
        width=120
    )
    
    # Metrics - Editable by owner
    gb.configure_column(
        'metric_1',
        headerName='Хэмжүүр 1',
        editable=cell_editable_js,
        width=100
    )
    
    gb.configure_column(
        'metric_2',
        headerName='Хэмжүүр 2',
        editable=cell_editable_js,
        width=100
    )
    
    # Description - Editable by owner
    gb.configure_column(
        'description',
        headerName='Тайлбар',
        editable=cell_editable_js,
        width=200
    )
    
    # Sub-channel
    gb.configure_column(
        'sub_channel',
        headerName='Дэд сувaг',
        editable=cell_editable_js,
        width=120
    )
    
    # Grid options
    gb.configure_grid_options(
        getRowStyle=row_style_js,
        enableRangeSelection=True,
        suppressRowClickSelection=True,
        rowSelection='multiple',
        domLayout='normal'
    )
    
    # Selection
    gb.configure_selection(
        selection_mode='multiple',
        use_checkbox=True
    )
    
    # Pagination
    gb.configure_pagination(
        enabled=True,
        paginationAutoPageSize=False,
        paginationPageSize=20
    )
    
    grid_options = gb.build()
    
    # ===================
    # Render AgGrid
    # ===================
    
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        theme='streamlit',  # 'streamlit', 'alpine', 'balham', 'material'
        height=500,
        allow_unsafe_jscode=True,  # Required for JsCode
        reload_data=False
    )
    
    return grid_response


# =============================================================================
# BACKEND SECURITY - VERIFY OWNERSHIP BEFORE SAVE
# =============================================================================

def verify_and_save_changes(
    original_df: pd.DataFrame,
    updated_df: pd.DataFrame,
    current_username: str
) -> Dict[str, Any]:
    """
    Verify ownership and save changes to database.
    
    BACKEND SECURITY: Double-check that user only modified their own rows.
    
    Args:
        original_df: Original DataFrame before edits
        updated_df: DataFrame after user edits
        current_username: Currently logged-in user
    
    Returns:
        Dictionary with success status and messages
    """
    result = {
        'success': False,
        'updated_count': 0,
        'unauthorized_count': 0,
        'errors': [],
        'messages': []
    }
    
    # Find changed rows by comparing dataframes
    if original_df.empty or updated_df.empty:
        result['messages'].append("No data to save")
        return result
    
    # Ensure both have same columns for comparison
    common_cols = list(set(original_df.columns) & set(updated_df.columns))
    
    # Find rows that have been modified
    changed_rows = []
    
    for idx, updated_row in updated_df.iterrows():
        item_id = updated_row.get('id')
        if item_id is None:
            continue
        
        # Find original row
        original_row = original_df[original_df['id'] == item_id]
        if original_row.empty:
            continue
        
        original_row = original_row.iloc[0]
        
        # Check if any editable field changed
        editable_fields = [
            'campaign_name', 'budget_code', 'vendor', 'amount_planned',
            'start_date', 'end_date', 'metric_1', 'metric_2', 'description',
            'sub_channel'
        ]
        
        is_changed = False
        for field in editable_fields:
            if field in updated_row and field in original_row:
                old_val = original_row[field]
                new_val = updated_row[field]
                
                # Handle NaN comparison
                if pd.isna(old_val) and pd.isna(new_val):
                    continue
                if old_val != new_val:
                    is_changed = True
                    break
        
        if is_changed:
            changed_rows.append({
                'id': item_id,
                'specialist': updated_row.get('specialist'),
                'data': updated_row.to_dict()
            })
    
    if not changed_rows:
        result['success'] = True
        result['messages'].append("Өөрчлөлт илрээгүй")
        return result
    
    # ===================
    # SECURITY CHECK: Verify ownership
    # ===================
    
    authorized_updates = []
    unauthorized_updates = []
    
    for row in changed_rows:
        if row['specialist'] == current_username:
            authorized_updates.append(row)
        else:
            unauthorized_updates.append(row)
            result['errors'].append(
                f"⛔ Зөвшөөрөлгүй: Мөрийн ID {row['id']} хамаарах '{row['specialist']}', та биш!"
            )
    
    result['unauthorized_count'] = len(unauthorized_updates)
    
    # ===================
    # Save authorized changes to database
    # ===================
    
    if authorized_updates:
        try:
            with get_session() as session:
                for update in authorized_updates:
                    item_id = update['id']
                    data = update['data']
                    
                    # Get item from database
                    item = session.get(BudgetItem, item_id)
                    
                    if item:
                        # Double-check ownership in database
                        file = session.get(BudgetFile, item.file_id)
                        if file and file.uploader:
                            if file.uploader.username != current_username:
                                result['errors'].append(
                                    f"⛔ Өгөгдлийн сангийн шалгалт амжилтгүй боллоо: Мөр {item_id} танд хамааралгүй!"
                                )
                                continue
                        
                        # Update fields
                        if 'campaign_name' in data and data['campaign_name']:
                            item.campaign_name = str(data['campaign_name'])
                        
                        if 'budget_code' in data and data['budget_code']:
                            item.budget_code = str(data['budget_code'])
                        
                        if 'vendor' in data:
                            item.vendor = str(data['vendor']) if data['vendor'] else None
                        
                        if 'amount_planned' in data:
                            try:
                                item.amount_planned = Decimal(str(data['amount_planned'])) if data['amount_planned'] else None
                            except:
                                pass
                        
                        if 'description' in data:
                            item.description = str(data['description']) if data['description'] else None
                        
                        if 'metric_1' in data:
                            item.metric_1 = str(data['metric_1']) if data['metric_1'] else None
                        
                        if 'metric_2' in data:
                            item.metric_2 = str(data['metric_2']) if data['metric_2'] else None
                        
                        if 'sub_channel' in data:
                            item.sub_channel = str(data['sub_channel']) if data['sub_channel'] else None
                        
                        session.add(item)
                        result['updated_count'] += 1
                
                session.commit()
                result['success'] = True
                result['messages'].append(
                    f"✅ Амжилттай шинэчлэгдлээ {result['updated_count']} мөр"
                )
                
        except Exception as e:
            result['errors'].append(f"Өгөгдлийн сангийн алдаа: {str(e)}")
    
    # Add warning if there were unauthorized attempts
    if unauthorized_updates:
        result['messages'].append(
            f"⚠️ {len(unauthorized_updates)} зөвшөөрөлгүй засварууд хаагдсан"
        )
    
    return result


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    """Main dashboard page."""
    
    # Initialize session state
    init_session_state()
    
    # Page header
    st.title("📊 Төсвийн самбар")
    st.markdown("Бүх төсвүүдийг харах болон өөрийн бичлэгүүдийг засах")
    
    # ===================
    # Login Check / Demo Mode
    # ===================
    
    # Sidebar - User info and demo login
    with st.sidebar:
        st.subheader("👤 Хэрэглэгчийн сешн")
        
        if st.session_state.authenticated and st.session_state.username:
            st.success(f"Нэвтэрсэн нэр: **{st.session_state.username}**")
            st.caption(f"Үүрэг: {st.session_state.user_role or 'Хэрэглэгч'}")
            
            if st.button("Гарах"):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.rerun()
        else:
            st.warning("Нэвтрээгүй - Туршилтын горим")
            st.markdown("**Хурдан туршилтын нэвтрэлт:**")
            
            demo_user = st.selectbox(
                "Туршилтын хэрэглэгч сонгох",
                ["planner", "manager", "admin"],
                help="Мөрийн түвшний аюулгүй байдлыг турших хэрэглэгч сонгох"
            )
            
            if st.button("Туршилтын хэрэглэгч болж нэвтрэх"):
                st.session_state.authenticated = True
                st.session_state.username = demo_user
                st.session_state.user_id = 1  # Demo ID
                st.session_state.user_role = demo_user
                st.rerun()
        
        st.divider()
        
        # Legend
        st.subheader("📋 Тайлбар")
        st.markdown("""
        <div style='background-color: #d4edda; padding: 8px; border-left: 4px solid #28a745; margin: 5px 0;'>
            <strong>Ногоон мөр</strong> = Таны өгөгдөл (засах боломжтой)
        </div>
        <div style='background-color: #f8f9fa; padding: 8px; border-left: 4px solid #6c757d; margin: 5px 0;'>
            <strong>Саарал мөр</strong> = Бусдын өгөгдөл (зөвхөн унших)
        </div>
        """, unsafe_allow_html=True)
    
    # ===================
    # Get current user
    # ===================
    
    current_username = st.session_state.get('username', 'anonymous')
    
    if not st.session_state.authenticated:
        st.warning("⚠️ Өөрийн төсвөө засахын тулд нэвтэрнэ үү. Та бүх өгөгдлийг зөвхөн унших горимд харж болно.")
        current_username = 'anonymous'  # No editing allowed
    else:
        st.info(f"👤 Нэвтэрсэн **{current_username}** - Та ногоон өнгөөр онцолсон мөрүүдийг засаж болно")
    
    # ===================
    # Load Data
    # ===================
    
    with st.spinner("Бүх төсвийн өгөгдлийг ачаалж байна..."):
        try:
            df = load_all_budget_items()
        except Exception as e:
            st.error(f"Өгөгдөл ачаалахад алдаа гарлаа: {e}")
            # Try simplified loader
            try:
                df = load_all_budget_items_simple()
            except:
                df = pd.DataFrame()
    
    if df.empty:
        st.warning("📭 Төсвийн өгөгдөл олдсонгүй. Эхлээд файл хуулна уу!")
        
        # Show demo data option
        if st.button("Туршилтын өгөгдөл ачаалах"):
            df = create_demo_data()
            st.session_state['demo_data'] = df
            st.rerun()
        
        # Check for demo data in session
        if 'demo_data' in st.session_state:
            df = st.session_state['demo_data']
        else:
            return
    
    # ===================
    # Summary Metrics
    # ===================
    
    st.subheader("📈 Хураангуй")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_budget = df['amount_planned'].sum() if 'amount_planned' in df.columns else 0
        st.metric("Нийт төсөв", f"₮{total_budget:,.0f}")
    
    with col2:
        total_rows = len(df)
        st.metric("Нийт зүйл", total_rows)
    
    with col3:
        my_rows = len(df[df['specialist'] == current_username]) if 'specialist' in df.columns else 0
        st.metric("Миний зүйлүүд", my_rows)
    
    with col4:
        unique_campaigns = df['campaign_name'].nunique() if 'campaign_name' in df.columns else 0
        st.metric("Кампанит ажлууд", unique_campaigns)
    
    st.divider()
    
    # ===================
    # Filters
    # ===================
    
    st.subheader("🔍 Шүүлтүүр")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Channel filter
        channels = ['Бүгд'] + (df['channel'].dropna().unique().tolist() if 'channel' in df.columns else [])
        selected_channel = st.selectbox("Сувag", channels)
    
    with col2:
        # Specialist filter
        specialists = ['Бүгд'] + (df['specialist'].dropna().unique().tolist() if 'specialist' in df.columns else [])
        selected_specialist = st.selectbox("Мэргэжилтэн", specialists)
    
    with col3:
        # Show only my data toggle
        show_only_mine = st.checkbox("Зөвхөн миний өгөгдлийг харуулах", value=False)
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_channel != 'Бүгд':
        filtered_df = filtered_df[filtered_df['channel'] == selected_channel]
    
    if selected_specialist != 'Бүгд':
        filtered_df = filtered_df[filtered_df['specialist'] == selected_specialist]
    
    if show_only_mine:
        filtered_df = filtered_df[filtered_df['specialist'] == current_username]
    
    st.caption(f"Харуулж байна {len(filtered_df)} {len(df)}-ийн зүйл")
    
    # ===================
    # Data Grid with Row-Level Security
    # ===================
    
    st.subheader("📋 Төсвийн өгөгдөл")
    
    # Store original for comparison
    original_df = filtered_df.copy()
    
    # Render secure AgGrid
    grid_response = create_secure_aggrid(filtered_df, current_username)
    
    # Get updated data
    updated_df = pd.DataFrame(grid_response['data'])
    
    # ===================
    # Save Changes Button
    # ===================
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Өөрчлөлт хадгалах", type="primary", disabled=not st.session_state.authenticated):
            if not st.session_state.authenticated:
                st.error("Өөрчлөлт хадгалахын тулд нэвтэрнэ үү")
            else:
                with st.spinner("Өөрчлөлтүүдийг хадгалж байна..."):
                    result = verify_and_save_changes(original_df, updated_df, current_username)
                
                # Show results
                for msg in result['messages']:
                    if '✅' in msg:
                        st.success(msg)
                    elif '⚠️' in msg:
                        st.warning(msg)
                    else:
                        st.info(msg)
                
                for error in result['errors']:
                    st.error(error)
                
                # Refresh data if changes were made
                if result['updated_count'] > 0:
                    st.cache_data.clear()
                    st.rerun()
    
    with col2:
        if st.button("🔄 Өгөгдөл шинэчлэх"):
            st.cache_data.clear()
            st.rerun()
    
    with col3:
        if not st.session_state.authenticated:
            st.caption("⚠️ Өөрчлөлт хадгалахын тулд нэвтрэх шаардлагатай")


# =============================================================================
# DEMO DATA GENERATOR
# =============================================================================

def create_demo_data() -> pd.DataFrame:
    """Create demo data for testing when database is empty."""
    
    demo_data = [
        {
            'id': 1, 'file_id': 1, 'campaign_name': 'New Year Campaign',
            'budget_code': 'TV-001', 'vendor': 'MNB', 'channel': 'TV',
            'amount_planned': 50000000, 'start_date': '2024-01-01',
            'end_date': '2024-01-31', 'specialist': 'planner',
            'metric_1': '30', 'metric_2': '100', 'description': 'Holiday ads'
        },
        {
            'id': 2, 'file_id': 1, 'campaign_name': 'Spring Sale',
            'budget_code': 'TV-002', 'vendor': 'TV5', 'channel': 'TV',
            'amount_planned': 35000000, 'start_date': '2024-03-01',
            'end_date': '2024-03-15', 'specialist': 'planner',
            'metric_1': '15', 'metric_2': '50', 'description': 'Spring promo'
        },
        {
            'id': 3, 'file_id': 2, 'campaign_name': 'Billboard Q1',
            'budget_code': 'OOH-001', 'vendor': 'AdBoard', 'channel': 'OOH',
            'amount_planned': 25000000, 'start_date': '2024-01-01',
            'end_date': '2024-03-31', 'specialist': 'manager',
            'metric_1': '5x3m', 'metric_2': '10', 'description': 'City center'
        },
        {
            'id': 4, 'file_id': 2, 'campaign_name': 'Radio Spots',
            'budget_code': 'FM-001', 'vendor': 'MGL Radio', 'channel': 'FM',
            'amount_planned': 15000000, 'start_date': '2024-02-01',
            'end_date': '2024-02-28', 'specialist': 'manager',
            'metric_1': '30', 'metric_2': '200', 'description': 'Morning show'
        },
        {
            'id': 5, 'file_id': 3, 'campaign_name': 'Digital Campaign',
            'budget_code': 'DIG-001', 'vendor': 'Facebook', 'channel': 'Digital',
            'amount_planned': 20000000, 'start_date': '2024-01-15',
            'end_date': '2024-02-15', 'specialist': 'admin',
            'metric_1': '500000', 'metric_2': '25000', 'description': 'Social media ads'
        },
    ]
    
    return pd.DataFrame(demo_data)


# =============================================================================
# RUN PAGE
# =============================================================================

if __name__ == "__main__":
    main()
else:
    main()

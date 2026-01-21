"""
CPP Dashboard - STANDALONE TEST VERSION
========================================

This is a self-contained version for testing AgGrid row-level security.
No database required - uses demo data.

Run with: streamlit run dashboard_test.py

Author: CPP Development Team
"""

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="CPP Dashboard - Test",
    page_icon="📊",
    layout="wide"
)

# =============================================================================
# DEMO DATA
# =============================================================================

@st.cache_data
def get_demo_data() -> pd.DataFrame:
    """Create demo budget data for testing."""
    
    data = [
        # Planner's data
        {'id': 1, 'campaign_name': 'New Year TV Campaign', 'budget_code': 'TV-001', 
         'vendor': 'MNB', 'channel': 'TV', 'amount_planned': 50000000,
         'start_date': '2024-01-01', 'end_date': '2024-01-31',
         'specialist': 'planner', 'description': 'Holiday television ads'},
        
        {'id': 2, 'campaign_name': 'Spring Sale TV', 'budget_code': 'TV-002',
         'vendor': 'TV5', 'channel': 'TV', 'amount_planned': 35000000,
         'start_date': '2024-03-01', 'end_date': '2024-03-15',
         'specialist': 'planner', 'description': 'Spring promotion spots'},
        
        {'id': 3, 'campaign_name': 'Summer FM Campaign', 'budget_code': 'FM-001',
         'vendor': 'Radio 100', 'channel': 'FM', 'amount_planned': 15000000,
         'start_date': '2024-06-01', 'end_date': '2024-06-30',
         'specialist': 'planner', 'description': 'Radio advertisements'},
        
        # Manager's data
        {'id': 4, 'campaign_name': 'Q1 Billboard Campaign', 'budget_code': 'OOH-001',
         'vendor': 'AdBoard LLC', 'channel': 'OOH', 'amount_planned': 25000000,
         'start_date': '2024-01-01', 'end_date': '2024-03-31',
         'specialist': 'manager', 'description': 'City center billboards'},
        
        {'id': 5, 'campaign_name': 'Airport Displays', 'budget_code': 'OOH-002',
         'vendor': 'SkyAds', 'channel': 'OOH', 'amount_planned': 40000000,
         'start_date': '2024-02-01', 'end_date': '2024-12-31',
         'specialist': 'manager', 'description': 'Airport terminal screens'},
        
        # Admin's data
        {'id': 6, 'campaign_name': 'Facebook Ads Q1', 'budget_code': 'DIG-001',
         'vendor': 'Meta', 'channel': 'Digital', 'amount_planned': 20000000,
         'start_date': '2024-01-15', 'end_date': '2024-03-15',
         'specialist': 'admin', 'description': 'Social media advertising'},
        
        {'id': 7, 'campaign_name': 'Google Search Ads', 'budget_code': 'DIG-002',
         'vendor': 'Google', 'channel': 'Digital', 'amount_planned': 30000000,
         'start_date': '2024-01-01', 'end_date': '2024-06-30',
         'specialist': 'admin', 'description': 'Search engine marketing'},
        
        {'id': 8, 'campaign_name': 'Print Magazine Ad', 'budget_code': 'PRT-001',
         'vendor': 'Zuunii Medee', 'channel': 'Print', 'amount_planned': 8000000,
         'start_date': '2024-04-01', 'end_date': '2024-04-30',
         'specialist': 'admin', 'description': 'Magazine full page ad'},
    ]
    
    return pd.DataFrame(data)


# =============================================================================
# AGGRID WITH ROW-LEVEL SECURITY
# =============================================================================

def create_secure_grid(df: pd.DataFrame, current_user: str):
    """
    Create AgGrid with row-level editing security.
    
    Features:
    - ALL data visible to everyone
    - ONLY rows where specialist == current_user are editable
    - Visual highlighting for editable rows
    """
    
    # ===================
    # JsCode: Cell Editable Function
    # ===================
    # Returns true only if row's specialist matches current user
    
    is_editable = JsCode(f"""
    function(params) {{
        return params.data.specialist === '{current_user}';
    }}
    """)
    
    # ===================
    # JsCode: Row Styling
    # ===================
    # Green background for user's own rows
    
    row_style = JsCode(f"""
    function(params) {{
        if (params.data.specialist === '{current_user}') {{
            return {{
                'backgroundColor': '#d4edda',
                'borderLeft': '4px solid #28a745'
            }};
        }}
        return {{
            'backgroundColor': '#f8f9fa'
        }};
    }}
    """)
    
    # ===================
    # JsCode: Cell Styling
    # ===================
    # Gray out non-editable cells
    
    cell_style = JsCode(f"""
    function(params) {{
        if (params.data.specialist !== '{current_user}') {{
            return {{'color': '#6c757d'}};
        }}
        return {{'color': '#212529'}};
    }}
    """)
    
    # ===================
    # Amount Formatter
    # ===================
    
    amount_formatter = JsCode("""
    function(params) {
        if (params.value != null) {
            return '₮' + Number(params.value).toLocaleString();
        }
        return '';
    }
    """)
    
    # ===================
    # Build Grid Options
    # ===================
    
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # Default settings
    gb.configure_default_column(
        resizable=True,
        filterable=True,
        sortable=True,
        editable=False,
        cellStyle=cell_style
    )
    
    # ID - hidden
    gb.configure_column('id', hide=True)
    
    # Specialist - pinned, read-only, bold
    gb.configure_column(
        'specialist',
        headerName='👤 Specialist',
        pinned='left',
        width=120,
        editable=False,
        cellStyle={'fontWeight': 'bold'}
    )
    
    # Editable columns (only for owner)
    gb.configure_column('campaign_name', headerName='Campaign', editable=is_editable, width=180)
    gb.configure_column('budget_code', headerName='Code', editable=is_editable, width=100)
    gb.configure_column('vendor', headerName='Vendor', editable=is_editable, width=130)
    gb.configure_column('channel', headerName='Channel', editable=False, width=90)
    
    gb.configure_column(
        'amount_planned',
        headerName='💰 Amount',
        editable=is_editable,
        type=['numericColumn'],
        valueFormatter=amount_formatter,
        width=140
    )
    
    gb.configure_column('start_date', headerName='Start', editable=is_editable, width=110)
    gb.configure_column('end_date', headerName='End', editable=is_editable, width=110)
    gb.configure_column('description', headerName='Description', editable=is_editable, width=200)
    
    # Grid options with row styling
    gb.configure_grid_options(
        getRowStyle=row_style,
        domLayout='normal'
    )
    
    # Pagination
    gb.configure_pagination(enabled=True, paginationPageSize=10)
    
    grid_options = gb.build()
    
    # Render grid
    return AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        theme='streamlit',
        height=400,
        allow_unsafe_jscode=True  # Required for JsCode!
    )


# =============================================================================
# BACKEND SECURITY CHECK
# =============================================================================

def verify_changes(original_df: pd.DataFrame, updated_df: pd.DataFrame, current_user: str):
    """
    Backend verification: Only allow saving changes to user's own rows.
    """
    results = {
        'authorized': [],
        'unauthorized': [],
        'messages': []
    }
    
    # Compare each row
    for idx, row in updated_df.iterrows():
        row_id = row['id']
        specialist = row['specialist']
        
        # Find original
        orig = original_df[original_df['id'] == row_id]
        if orig.empty:
            continue
        orig = orig.iloc[0]
        
        # Check if changed
        changed = False
        for col in ['campaign_name', 'budget_code', 'vendor', 'amount_planned', 'description']:
            if str(row.get(col, '')) != str(orig.get(col, '')):
                changed = True
                break
        
        if changed:
            if specialist == current_user:
                results['authorized'].append(row_id)
            else:
                results['unauthorized'].append({
                    'id': row_id,
                    'owner': specialist
                })
    
    return results


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    st.title("📊 CPP Budget Dashboard")
    st.markdown("**Row-Level Security Demo** - Edit only your own data")
    
    # ===================
    # Sidebar - User Selection
    # ===================
    
    with st.sidebar:
        st.header("👤 User Login")
        
        # Demo user selection
        current_user = st.selectbox(
            "Login as:",
            ["planner", "manager", "admin"],
            help="Select a user to test row-level security"
        )
        
        st.success(f"Logged in as: **{current_user}**")
        
        st.divider()
        
        # Legend
        st.subheader("📋 Color Legend")
        
        st.markdown("""
        <div style='background:#d4edda; padding:10px; border-left:4px solid #28a745; margin:5px 0; border-radius:4px;'>
            <b>🟢 Green</b> = Your data (editable)
        </div>
        <div style='background:#f8f9fa; padding:10px; border-left:4px solid #6c757d; margin:5px 0; border-radius:4px;'>
            <b>⚪ Gray</b> = Others' data (read-only)
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Instructions
        st.subheader("📝 Instructions")
        st.markdown("""
        1. Select a user above
        2. Try editing green rows ✅
        3. Try editing gray rows ❌
        4. Click "Save Changes"
        5. See security check results
        """)
    
    # ===================
    # Main Content
    # ===================
    
    st.info(f"👤 You are logged in as **{current_user}**. Only green rows (your data) can be edited.")
    
    # Load demo data
    df = get_demo_data()
    original_df = df.copy()
    
    # Store in session for comparison
    if 'original_data' not in st.session_state:
        st.session_state.original_data = df.copy()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = df['amount_planned'].sum()
        st.metric("💰 Total Budget", f"₮{total:,.0f}")
    
    with col2:
        st.metric("📋 Total Rows", len(df))
    
    with col3:
        my_rows = len(df[df['specialist'] == current_user])
        st.metric("✏️ My Rows", my_rows)
    
    with col4:
        others_rows = len(df[df['specialist'] != current_user])
        st.metric("🔒 Others' Rows", others_rows)
    
    st.divider()
    
    # Render secure grid
    st.subheader("📋 Budget Data")
    
    grid_response = create_secure_grid(df, current_user)
    updated_df = pd.DataFrame(grid_response['data'])
    
    # ===================
    # Save Button with Security Check
    # ===================
    
    st.divider()
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        save_clicked = st.button("💾 Save Changes", type="primary")
    
    if save_clicked:
        st.subheader("🔒 Security Verification Results")
        
        # Run backend verification
        results = verify_changes(st.session_state.original_data, updated_df, current_user)
        
        if results['authorized']:
            st.success(f"✅ {len(results['authorized'])} row(s) authorized for update: IDs {results['authorized']}")
        
        if results['unauthorized']:
            st.error("⛔ UNAUTHORIZED EDITS BLOCKED!")
            for item in results['unauthorized']:
                st.error(f"Row ID {item['id']} belongs to **{item['owner']}** - You cannot edit this!")
        
        if not results['authorized'] and not results['unauthorized']:
            st.info("No changes detected")
        
        # Show code example
        with st.expander("🔍 View Security Check Code"):
            st.code("""
# Backend Security Check (Python)
for row in updated_rows:
    if row['specialist'] != current_username:
        # BLOCK THE UPDATE!
        errors.append(f"Unauthorized: Row {row['id']} belongs to {row['specialist']}")
    else:
        # Allow update
        session.update(row)
            """, language="python")


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    main()

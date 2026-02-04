"""
Database Module for Central Planning Platform
"""

from .connection import (
    get_session,
    get_session_for_streamlit,
    init_db,
    check_database_connection,
    seed_demo_users
)

from .models import (
    # Reference Data (Part A)
    BudgetCodeRef,
    ChannelCategory,
    ChannelActivity,
    CampaignType,
    ProductService,
    Approver,
    # Dynamic Headers
    HeaderTemplate,
    # Transaction Data (Part B)
    User,
    BudgetFile,
    BudgetItem,
    # CPP Items
    CppBudgetItem,
    # Audit Log
    AuditLog,
    # Audit Helper Functions
    log_create,
    log_update,
    log_delete,
    get_record_history,
    get_user_activity,
    # Cleanup Functions
    cleanup_deleted_records,
    SOFT_DELETE_RETENTION_DAYS,
    AUDIT_RETENTION_DAYS,
    # Channel Metrics
    CHANNEL_METRICS_SCHEMA,
    get_metric_label,
)

__all__ = [
    # Connection
    'get_session',
    'get_session_for_streamlit', 
    'init_db',
    'check_database_connection',
    'seed_demo_users',
    # Reference Data
    'BudgetCodeRef',
    'ChannelCategory',
    'ChannelActivity',
    'CampaignType',
    'ProductService',
    'Approver',
    # Dynamic Headers
    'HeaderTemplate',
    # Transaction Data
    'User',
    'BudgetFile',
    'BudgetItem',
    # CPP Items
    'CppBudgetItem',
    # Audit
    'AuditLog',
    'log_create',
    'log_update', 
    'log_delete',
    'get_record_history',
    'get_user_activity',
    'cleanup_deleted_records',
    'SOFT_DELETE_RETENTION_DAYS',
    'AUDIT_RETENTION_DAYS',
    # Channel Metrics
    'CHANNEL_METRICS_SCHEMA',
    'get_metric_label',
]

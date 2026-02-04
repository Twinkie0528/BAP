"""
Database Models for Central Planning Platform (CPP) - V2
=========================================================

IMPROVEMENTS:
1. Proper Relationships with forward references (TYPE_CHECKING)
2. JSONB for channel_metrics instead of generic metric_1,2,3
3. JSONB for validation_errors instead of Text
4. Added soft delete (is_deleted, deleted_at)
5. Added audit fields (created_by, updated_by)
6. Added proper indexes for frequently queried columns

Author: CPP Development Team
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from decimal import Decimal
import json

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Numeric, Enum as SAEnum, Boolean, Integer, Index
from sqlalchemy.dialects.postgresql import JSONB

# Import our enums from config
from config import FileStatus, UserRole, ChannelType, BudgetType


# =============================================================================
# HELPER: JSONB Column with SQLite fallback
# =============================================================================

def JSONBColumn():
    """
    Returns JSONB column for PostgreSQL, Text for SQLite.
    This allows development with SQLite while using JSONB in production.
    """
    from config import DATABASE_TYPE
    if DATABASE_TYPE == "postgresql":
        return Column(JSONB, nullable=True)
    else:
        # SQLite fallback - store as JSON string
        return Column(Text, nullable=True)


# =============================================================================
# PART A: REFERENCE DATA MODELS (Seeded from Master Excel)
# =============================================================================

class BudgetCodeRef(SQLModel, table=True):
    """
    Reference table for valid Budget Codes.
    Seeded from Master Excel "BUDGET LIST" sheet.
    """
    __tablename__ = "budget_code_refs"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    code: str = Field(
        sa_column=Column(String(100), unique=True, nullable=False, index=True),
        description="Unique budget code"
    )
    
    description: Optional[str] = Field(
        sa_column=Column(String(500)),
        default=None,
        description="Human-readable description of this budget code"
    )
    
    department: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Department this code belongs to"
    )
    
    brand: Optional[str] = Field(
        sa_column=Column(String(200)),
        default=None,
        description="Brand associated with this code"
    )
    
    year: int = Field(
        default=2025,
        description="Budget year this code is valid for"
    )
    
    budget_limit: Optional[Decimal] = Field(
        sa_column=Column(Numeric(15, 2)),
        default=None,
        description="Maximum allowed budget for this code"
    )
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChannelCategory(SQLModel, table=True):
    """
    Reference table for valid Channel Categories.
    Examples: TV, OOH, FM, Digital, Print, Event
    """
    __tablename__ = "channel_categories"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    name: str = Field(
        sa_column=Column(String(50), unique=True, nullable=False, index=True),
        description="Channel category name"
    )
    
    description: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None
    )
    
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship to activities
    activities: List["ChannelActivity"] = Relationship(back_populates="category")


class ChannelActivity(SQLModel, table=True):
    """
    Reference table for valid Activities per Channel.
    Examples: News, Boost, Billboard, Radio Spot
    """
    __tablename__ = "channel_activities"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    category_id: int = Field(
        foreign_key="channel_categories.id",
        index=True,
        description="Parent channel category"
    )
    
    name: str = Field(
        sa_column=Column(String(100), nullable=False, index=True),
        description="Activity name"
    )
    
    description: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None
    )
    
    # Default metric labels for this activity type (stored as JSONB)
    default_metrics_schema: Optional[Dict[str, Any]] = Field(
        sa_column=JSONBColumn(),
        default=None,
        description="JSON schema for this activity's metrics"
    )
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship to parent category
    category: Optional["ChannelCategory"] = Relationship(back_populates="activities")


class CampaignType(SQLModel, table=True):
    """
    Reference table for Campaign/Activity Types.
    Examples: BRANDING CAMPAIGN, PRODUCT LAUNCH, SPONSORSHIP
    """
    __tablename__ = "campaign_types"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    name: str = Field(
        sa_column=Column(String(100), unique=True, nullable=False, index=True)
    )
    
    description: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None
    )
    
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProductService(SQLModel, table=True):
    """
    Reference table for Products & Services (Brands).
    Examples: UNITEL, UNIVISION, TOKI
    """
    __tablename__ = "product_services"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    name: str = Field(
        sa_column=Column(String(100), unique=True, nullable=False, index=True)
    )
    
    description: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None
    )
    
    parent_brand: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Parent brand if applicable"
    )
    
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Approver(SQLModel, table=True):
    """
    Reference table for Authorized Approvers.
    """
    __tablename__ = "approvers"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    name: str = Field(
        sa_column=Column(String(100), unique=True, nullable=False, index=True)
    )
    
    position: str = Field(
        sa_column=Column(String(200), nullable=False)
    )
    
    department: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None
    )
    
    signature_image_path: Optional[str] = Field(
        sa_column=Column(String(500)),
        default=None
    )
    
    approval_level: int = Field(default=1)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# PART B: TRANSACTION DATA MODELS (User uploads)
# =============================================================================

class User(SQLModel, table=True):
    """
    System users - planners who upload files and managers who approve them.
    
    Relationships:
        uploaded_files: Files this user has uploaded
        reviewed_files: Files this user has reviewed (managers only)
    """
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # User Credentials
    username: str = Field(
        sa_column=Column(String(50), unique=True, nullable=False, index=True)
    )
    email: Optional[str] = Field(
        sa_column=Column(String(100), unique=True),
        default=None
    )
    password_hash: str = Field(
        sa_column=Column(String(255), nullable=False)
    )
    
    # Profile Information
    full_name: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None
    )
    
    # Role and Status
    role: UserRole = Field(
        sa_column=Column(SAEnum(UserRole), nullable=False, default=UserRole.PLANNER),
        default=UserRole.PLANNER
    )
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    
    # =========================================================================
    # RELATIONSHIPS - Properly configured with back_populates
    # =========================================================================
    
    # Files uploaded by this user
    uploaded_files: List["BudgetFile"] = Relationship(
        back_populates="uploader",
        sa_relationship_kwargs={"foreign_keys": "[BudgetFile.uploader_id]"}
    )
    
    # Files reviewed by this user (manager)
    reviewed_files: List["BudgetFile"] = Relationship(
        back_populates="reviewer",
        sa_relationship_kwargs={"foreign_keys": "[BudgetFile.reviewer_id]"}
    )
    
    # CPP items created by this user
    cpp_items: List["CppBudgetItem"] = Relationship(back_populates="owner")


class BudgetFile(SQLModel, table=True):
    """
    Tracks uploaded Excel files and their workflow status.
    
    Workflow States:
        PENDING_APPROVAL -> Submitted for manager review
        APPROVED_FOR_PRINT -> Manager approved
        SIGNING -> Getting signatures
        FINALIZED -> Completed
        REJECTED -> Manager rejected
    """
    __tablename__ = "budget_files"
    __table_args__ = (
        # Composite index for common queries
        Index('ix_budget_files_status_uploader', 'status', 'uploader_id'),
        Index('ix_budget_files_uploaded_at', 'uploaded_at'),
        {'extend_existing': True}
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # File Information
    filename: str = Field(
        sa_column=Column(String(255), nullable=False)
    )
    budget_type: BudgetType = Field(
        sa_column=Column(SAEnum(BudgetType), nullable=False, default=BudgetType.PRIMARY),
        default=BudgetType.PRIMARY
    )
    
    # Budget Info from Excel
    budget_code: Optional[str] = Field(
        sa_column=Column(String(100), index=True),
        default=None
    )
    brand: Optional[str] = Field(
        sa_column=Column(String(200)),
        default=None
    )
    
    file_hash: Optional[str] = Field(
        sa_column=Column(String(64)),
        default=None
    )
    
    # Workflow Status
    status: FileStatus = Field(
        sa_column=Column(SAEnum(FileStatus), nullable=False, default=FileStatus.PENDING_APPROVAL),
        default=FileStatus.PENDING_APPROVAL
    )
    
    # Foreign Keys
    uploader_id: int = Field(
        foreign_key="users.id",
        index=True
    )
    reviewer_id: Optional[int] = Field(
        default=None,
        foreign_key="users.id"
    )
    parent_file_id: Optional[int] = Field(
        default=None,
        foreign_key="budget_files.id",
        description="Parent PRIMARY budget file (for ADDITIONAL budgets)"
    )
    
    # Timestamps
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = Field(default=None)
    reviewed_at: Optional[datetime] = Field(default=None)
    published_at: Optional[datetime] = Field(default=None)
    
    # PDF and Signing
    pdf_generated_at: Optional[datetime] = Field(default=None)
    pdf_file_path: Optional[str] = Field(
        sa_column=Column(String(500)),
        default=None
    )
    signed_file_path: Optional[str] = Field(
        sa_column=Column(String(500)),
        default=None
    )
    signed_uploaded_at: Optional[datetime] = Field(default=None)
    finalized_at: Optional[datetime] = Field(default=None)
    
    # Review Information
    reviewer_comment: Optional[str] = Field(
        sa_column=Column(Text),
        default=None
    )
    
    # Summary Statistics
    row_count: int = Field(default=0)
    total_amount: Optional[Decimal] = Field(
        sa_column=Column(Numeric(15, 2)),
        default=None,
        description="Нийт бодит төсөв"
    )
    planned_amount: Optional[Decimal] = Field(
        sa_column=Column(Numeric(15, 2)),
        default=None,
        description="Нийт төсөв"
    )
    
    # Campaign & Specialist
    campaign_name: Optional[str] = Field(
        sa_column=Column(String(200), index=True),
        default=None
    )
    specialist_name: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None
    )
    
    # Validation
    is_valid: bool = Field(default=True)
    validation_error_count: int = Field(default=0)
    
    # =========================================================================
    # SOFT DELETE
    # =========================================================================
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    
    uploader: Optional["User"] = Relationship(
        back_populates="uploaded_files",
        sa_relationship_kwargs={"foreign_keys": "[BudgetFile.uploader_id]"}
    )
    
    reviewer: Optional["User"] = Relationship(
        back_populates="reviewed_files",
        sa_relationship_kwargs={"foreign_keys": "[BudgetFile.reviewer_id]"}
    )
    
    items: List["BudgetItem"] = Relationship(back_populates="budget_file")
    
    # Self-referential for parent file
    parent_file: Optional["BudgetFile"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[BudgetFile.parent_file_id]",
            "remote_side": "[BudgetFile.id]"
        }
    )


class BudgetItem(SQLModel, table=True):
    """
    Individual budget line items extracted from Excel files.
    
    DESIGN CHANGE: Instead of generic metric_1, metric_2, metric_3 fields,
    we now use JSONB 'channel_metrics' field that stores channel-specific data.
    
    Example channel_metrics by channel:
        TV:      {"duration_sec": 30, "frequency": 5, "grp": 12.5, "time_slot": "prime"}
        OOH:     {"size_sqm": 50, "quantity": 3, "location": "UB Center"}
        FM:      {"duration_sec": 30, "spots_per_day": 10, "station": "MNB FM"}
        Digital: {"impressions": 100000, "clicks": 5000, "platform": "Facebook"}
    """
    __tablename__ = "budget_items"
    __table_args__ = (
        Index('ix_budget_items_campaign_vendor', 'campaign_name', 'vendor'),
        Index('ix_budget_items_dates', 'start_date', 'end_date'),
        {'extend_existing': True}
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign Key to Parent File
    file_id: int = Field(
        foreign_key="budget_files.id",
        index=True
    )
    
    # Traceability
    row_number: Optional[int] = Field(default=None)
    
    # Specialist/Owner
    specialist: Optional[str] = Field(
        sa_column=Column(String(100), index=True),
        default=None
    )
    
    # ===================
    # CORE FIELDS
    # ===================
    
    campaign_name: str = Field(
        sa_column=Column(String(255), nullable=False, index=True)
    )
    
    budget_code: str = Field(
        sa_column=Column(String(50), nullable=False, index=True)
    )
    
    vendor: Optional[str] = Field(
        sa_column=Column(String(255), index=True),
        default=None,
        description="Company/agency/influencer name"
    )
    
    channel: ChannelType = Field(
        sa_column=Column(SAEnum(ChannelType), nullable=False)
    )
    
    sub_channel: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None
    )
    
    amount_planned: Optional[Decimal] = Field(
        sa_column=Column(Numeric(15, 2)),
        default=None
    )
    
    start_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(String(50)),  # Allow flexible date formats
        description="Campaign start date"
    )
    
    end_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(String(50)),  # Allow flexible date formats
        description="Campaign end date"
    )
    
    # ===================
    # CHANNEL METRICS (JSONB) - Replaces metric_1, metric_2, metric_3
    # ===================
    
    channel_metrics: Optional[Dict[str, Any]] = Field(
        sa_column=JSONBColumn(),
        default=None,
        description="Channel-specific metrics stored as JSONB"
    )
    
    # ===================
    # LEGACY FIELDS (kept for backward compatibility, will be migrated)
    # ===================
    metric_1: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="DEPRECATED: Use channel_metrics instead"
    )
    
    metric_2: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="DEPRECATED: Use channel_metrics instead"
    )
    
    metric_3: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="DEPRECATED: Use channel_metrics instead"
    )
    
    # ===================
    # ADDITIONAL FIELDS
    # ===================
    
    description: Optional[str] = Field(
        sa_column=Column(Text),
        default=None
    )
    
    # ===================
    # VALIDATION FIELDS (JSONB instead of Text)
    # ===================
    
    ref_budget_code_id: Optional[int] = Field(
        default=None,
        foreign_key="budget_code_refs.id"
    )
    
    ref_channel_id: Optional[int] = Field(
        default=None,
        foreign_key="channel_categories.id"
    )
    
    ref_activity_id: Optional[int] = Field(
        default=None,
        foreign_key="channel_activities.id"
    )
    
    is_valid: bool = Field(default=True)
    
    # JSONB for validation errors - allows queries like:
    # SELECT * FROM budget_items WHERE validation_errors ? 'invalid_budget_code'
    validation_errors: Optional[Dict[str, Any]] = Field(
        sa_column=JSONBColumn(),
        default=None,
        description="Validation errors as JSONB for efficient querying"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # =========================================================================
    # SOFT DELETE
    # =========================================================================
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    
    budget_file: Optional["BudgetFile"] = Relationship(back_populates="items")
    
    # ===================
    # HELPER METHODS
    # ===================
    
    def set_channel_metric(self, key: str, value: Any) -> None:
        """Set a channel-specific metric."""
        if self.channel_metrics is None:
            self.channel_metrics = {}
        self.channel_metrics[key] = value
    
    def get_channel_metric(self, key: str, default: Any = None) -> Any:
        """Get a channel-specific metric."""
        if self.channel_metrics is None:
            return default
        # Handle both JSONB (dict) and Text (string) storage
        metrics = self.channel_metrics
        if isinstance(metrics, str):
            try:
                import json
                metrics = json.loads(metrics)
            except (json.JSONDecodeError, TypeError):
                return default
        return metrics.get(key, default) if isinstance(metrics, dict) else default
    
    def add_validation_error(self, error_code: str, message: str) -> None:
        """Add a validation error."""
        if self.validation_errors is None:
            self.validation_errors = {}
        elif isinstance(self.validation_errors, str):
            try:
                import json
                self.validation_errors = json.loads(self.validation_errors)
            except:
                self.validation_errors = {}
        self.validation_errors[error_code] = message
        self.is_valid = False
    
    def get_validation_errors(self) -> Dict[str, str]:
        """Get validation errors as dict."""
        if self.validation_errors is None:
            return {}
        # Handle both JSONB (dict) and Text (string) storage
        if isinstance(self.validation_errors, str):
            try:
                import json
                return json.loads(self.validation_errors)
            except (json.JSONDecodeError, TypeError):
                return {}
        return self.validation_errors or {}
    
    def has_validation_error(self, error_code: str) -> bool:
        """Check if specific error exists."""
        if self.validation_errors is None:
            return False
        return error_code in self.validation_errors
    
    def clear_validation_errors(self) -> None:
        """Clear all validation errors."""
        self.validation_errors = None
        self.is_valid = True
    
    def migrate_legacy_metrics(self) -> None:
        """
        Migrate legacy metric_1, metric_2, metric_3 to channel_metrics.
        Call this during data migration.
        """
        if self.channel_metrics is None:
            self.channel_metrics = {}
        
        # Get labels based on channel type
        from mappings.column_maps import METRIC_LABELS
        channel_labels = METRIC_LABELS.get(self.channel.value, {})
        
        if self.metric_1:
            label = channel_labels.get('metric_1', 'metric_1')
            self.channel_metrics[label] = self.metric_1
        
        if self.metric_2:
            label = channel_labels.get('metric_2', 'metric_2')
            self.channel_metrics[label] = self.metric_2
        
        if self.metric_3:
            label = channel_labels.get('metric_3', 'metric_3')
            self.channel_metrics[label] = self.metric_3


class HeaderTemplate(SQLModel, table=True):
    """
    Dynamic header templates for CPP and Excel uploads.
    """
    __tablename__ = "header_templates"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    template_type: str = Field(
        sa_column=Column(String(50), nullable=False, index=True)
    )
    
    column_key: str = Field(
        sa_column=Column(String(50), nullable=False)
    )
    
    display_name: str = Field(
        sa_column=Column(String(100), nullable=False)
    )
    
    column_type: str = Field(
        sa_column=Column(String(30), nullable=False, default="text"),
        default="text"
    )
    
    # JSONB for dropdown options
    dropdown_options: Optional[List[str]] = Field(
        sa_column=JSONBColumn(),
        default=None
    )
    
    display_order: int = Field(default=0)
    is_required: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def get_dropdown_options_list(self) -> List[str]:
        """Get dropdown options as list."""
        return self.dropdown_options or []


class CppBudgetItem(SQLModel, table=True):
    """
    Budget items entered through CPP UI (not Excel upload).
    """
    __tablename__ = "cpp_budget_items"
    __table_args__ = (
        Index('ix_cpp_budget_items_owner_status', 'owner_id', 'status'),
        {'extend_existing': True}
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    owner_id: int = Field(
        foreign_key="users.id",
        index=True
    )
    
    owner_username: str = Field(
        sa_column=Column(String(100), nullable=False, index=True)
    )
    
    budget_file_id: Optional[int] = Field(
        default=None,
        foreign_key="budget_files.id"
    )
    
    row_number: int = Field(default=0)
    
    # Category
    category_id: Optional[int] = Field(
        default=None,
        foreign_key="channel_categories.id"
    )
    category_name: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None
    )
    
    # Standard Fields
    activity_channel: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None
    )
    
    schedule: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None
    )
    
    responsible_person: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None
    )
    
    frequency: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None
    )
    
    unit_price: Optional[Decimal] = Field(
        sa_column=Column(Numeric(15, 2)),
        default=None
    )
    
    total_budget: Optional[Decimal] = Field(
        sa_column=Column(Numeric(15, 2)),
        default=None
    )
    
    description: Optional[str] = Field(
        sa_column=Column(Text),
        default=None
    )
    
    # JSONB for custom fields
    custom_fields: Optional[Dict[str, Any]] = Field(
        sa_column=JSONBColumn(),
        default=None
    )
    
    status: str = Field(
        sa_column=Column(String(30), nullable=False, default="draft"),
        default="draft"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Soft Delete
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    
    owner: Optional["User"] = Relationship(back_populates="cpp_items")
    
    def get_custom_fields(self) -> dict:
        """Get custom fields as dictionary."""
        if self.custom_fields is None:
            return {}
        # Handle both JSONB (dict) and Text (string) storage
        if isinstance(self.custom_fields, str):
            try:
                import json
                return json.loads(self.custom_fields)
            except (json.JSONDecodeError, TypeError):
                return {}
        return self.custom_fields or {}
    
    def set_custom_field(self, key: str, value: Any) -> None:
        """Set a custom field value."""
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[key] = value


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_metric_label(channel: ChannelType, metric_name: str) -> Optional[str]:
    """
    Get human-readable label for a metric field based on channel type.
    """
    from mappings.column_maps import METRIC_LABELS
    channel_labels = METRIC_LABELS.get(channel.value, {})
    return channel_labels.get(metric_name)


# =============================================================================
# AUDIT LOG MODEL - Full history tracking (Option B)
# =============================================================================

class AuditLog(SQLModel, table=True):
    """
    Audit trail for all database changes.
    
    Tracks every create, update, delete operation with full before/after values.
    Allows complete history reconstruction and undo functionality.
    
    Retention: 14 days (configurable via AUDIT_RETENTION_DAYS)
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('ix_audit_logs_table_record', 'table_name', 'record_id'),
        Index('ix_audit_logs_user_action', 'changed_by_id', 'action'),
        Index('ix_audit_logs_created_at', 'created_at'),
        {'extend_existing': True}
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # What was changed
    table_name: str = Field(
        sa_column=Column(String(100), nullable=False, index=True),
        description="Table name (e.g., 'budget_items', 'budget_files')"
    )
    
    record_id: int = Field(
        description="Primary key of the changed record"
    )
    
    # What action was performed
    action: str = Field(
        sa_column=Column(String(20), nullable=False),
        description="Action: 'create', 'update', 'delete', 'restore'"
    )
    
    # Who made the change
    changed_by_id: Optional[int] = Field(
        default=None,
        foreign_key="users.id",
        description="User who made the change"
    )
    
    changed_by_username: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Username (cached for display)"
    )
    
    # When
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the change occurred"
    )
    
    # What changed (JSONB)
    old_values: Optional[Dict[str, Any]] = Field(
        sa_column=JSONBColumn(),
        default=None,
        description="Previous values (for update/delete)"
    )
    
    new_values: Optional[Dict[str, Any]] = Field(
        sa_column=JSONBColumn(),
        default=None,
        description="New values (for create/update)"
    )
    
    # Additional context
    ip_address: Optional[str] = Field(
        sa_column=Column(String(50)),
        default=None,
        description="Client IP address"
    )
    
    user_agent: Optional[str] = Field(
        sa_column=Column(String(500)),
        default=None,
        description="Browser/client info"
    )
    
    # Diff summary for quick display
    change_summary: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Human-readable change summary"
    )
    
    @classmethod
    def create_log(
        cls,
        table_name: str,
        record_id: int,
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None
    ) -> "AuditLog":
        """
        Factory method to create an audit log entry.
        """
        # Generate change summary
        summary = None
        if action == "update" and old_values and new_values:
            changed_fields = []
            for key in new_values:
                if key not in old_values or old_values.get(key) != new_values.get(key):
                    changed_fields.append(key)
            summary = f"Changed: {', '.join(changed_fields[:5])}"
            if len(changed_fields) > 5:
                summary += f" (+{len(changed_fields) - 5} more)"
        elif action == "create":
            summary = f"Created new {table_name} record"
        elif action == "delete":
            summary = f"Deleted {table_name} record"
        elif action == "restore":
            summary = f"Restored {table_name} record"
        
        return cls(
            table_name=table_name,
            record_id=record_id,
            action=action,
            changed_by_id=user_id,
            changed_by_username=username,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            change_summary=summary
        )


# =============================================================================
# SOFT DELETE CLEANUP CONFIGURATION
# =============================================================================

SOFT_DELETE_RETENTION_DAYS = 14  # Keep deleted records for 14 days
AUDIT_RETENTION_DAYS = 14        # Keep audit logs for 14 days


def cleanup_deleted_records(session) -> dict:
    """
    Permanently delete records that have been soft-deleted for more than RETENTION_DAYS.
    Should be run as a scheduled job (daily).
    
    Returns:
        Dictionary with counts of deleted records per table
    """
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=SOFT_DELETE_RETENTION_DAYS)
    results = {}
    
    # Tables with soft delete
    soft_delete_tables = [BudgetFile, BudgetItem, CppBudgetItem]
    
    for model in soft_delete_tables:
        try:
            deleted = session.query(model).filter(
                model.is_deleted == True,
                model.deleted_at < cutoff_date
            ).delete(synchronize_session=False)
            results[model.__tablename__] = deleted
        except Exception as e:
            results[model.__tablename__] = f"Error: {e}"
    
    # Cleanup old audit logs
    try:
        audit_cutoff = datetime.utcnow() - timedelta(days=AUDIT_RETENTION_DAYS)
        deleted_audits = session.query(AuditLog).filter(
            AuditLog.created_at < audit_cutoff
        ).delete(synchronize_session=False)
        results['audit_logs'] = deleted_audits
    except Exception as e:
        results['audit_logs'] = f"Error: {e}"
    
    session.commit()
    return results


# =============================================================================
# AUDIT HELPER FUNCTIONS
# =============================================================================

def log_create(session, record, user_id: int = None, username: str = None) -> AuditLog:
    """Log a create action."""
    # Convert record to dict (exclude internal fields)
    new_values = {}
    for key, value in record.__dict__.items():
        if not key.startswith('_'):
            if isinstance(value, (datetime, Decimal)):
                value = str(value)
            new_values[key] = value
    
    log = AuditLog.create_log(
        table_name=record.__tablename__,
        record_id=record.id,
        action="create",
        user_id=user_id,
        username=username,
        new_values=new_values
    )
    session.add(log)
    return log


def log_update(session, record, old_values: dict, user_id: int = None, username: str = None) -> AuditLog:
    """Log an update action."""
    new_values = {}
    for key, value in record.__dict__.items():
        if not key.startswith('_'):
            if isinstance(value, (datetime, Decimal)):
                value = str(value)
            new_values[key] = value
    
    log = AuditLog.create_log(
        table_name=record.__tablename__,
        record_id=record.id,
        action="update",
        user_id=user_id,
        username=username,
        old_values=old_values,
        new_values=new_values
    )
    session.add(log)
    return log


def log_delete(session, record, user_id: int = None, username: str = None) -> AuditLog:
    """Log a delete action."""
    old_values = {}
    for key, value in record.__dict__.items():
        if not key.startswith('_'):
            if isinstance(value, (datetime, Decimal)):
                value = str(value)
            old_values[key] = value
    
    log = AuditLog.create_log(
        table_name=record.__tablename__,
        record_id=record.id,
        action="delete",
        user_id=user_id,
        username=username,
        old_values=old_values
    )
    session.add(log)
    return log


def get_record_history(session, table_name: str, record_id: int) -> List[AuditLog]:
    """Get full history of a record."""
    from sqlmodel import select
    
    statement = select(AuditLog).where(
        AuditLog.table_name == table_name,
        AuditLog.record_id == record_id
    ).order_by(AuditLog.created_at.desc())
    
    return session.exec(statement).all()


def get_user_activity(session, user_id: int, limit: int = 50) -> List[AuditLog]:
    """Get recent activity by a user."""
    from sqlmodel import select
    
    statement = select(AuditLog).where(
        AuditLog.changed_by_id == user_id
    ).order_by(AuditLog.created_at.desc()).limit(limit)
    
    return session.exec(statement).all()


# =============================================================================
# CHANNEL METRICS SCHEMA - Define what metrics each channel expects
# =============================================================================

CHANNEL_METRICS_SCHEMA = {
    "TV": {
        "duration_sec": {"type": "number", "label": "Duration (sec)", "required": True},
        "frequency": {"type": "number", "label": "Frequency", "required": True},
        "grp": {"type": "number", "label": "GRP", "required": False},
        "time_slot": {"type": "string", "label": "Time Slot", "required": False},
        "program_name": {"type": "string", "label": "Program Name", "required": False},
    },
    "FM": {
        "duration_sec": {"type": "number", "label": "Duration (sec)", "required": True},
        "spots_per_day": {"type": "number", "label": "Spots/Day", "required": True},
        "station": {"type": "string", "label": "Station", "required": False},
    },
    "OOH": {
        "size_sqm": {"type": "number", "label": "Size (sqm)", "required": True},
        "quantity": {"type": "number", "label": "Quantity", "required": True},
        "location": {"type": "string", "label": "Location", "required": False},
        "type": {"type": "string", "label": "OOH Type", "required": False},
    },
    "DIGITAL": {
        "impressions": {"type": "number", "label": "Impressions", "required": False},
        "clicks": {"type": "number", "label": "Clicks", "required": False},
        "platform": {"type": "string", "label": "Platform", "required": True},
        "ad_type": {"type": "string", "label": "Ad Type", "required": False},
    },
    "INFLUENCER": {
        "posts": {"type": "number", "label": "Posts", "required": True},
        "stories": {"type": "number", "label": "Stories", "required": False},
        "platform": {"type": "string", "label": "Platform", "required": True},
        "followers": {"type": "number", "label": "Followers", "required": False},
    },
}


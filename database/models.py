"""
Database Models for Central Planning Platform (CPP)
===================================================

This file defines all database tables using SQLModel (SQLAlchemy + Pydantic).
SQLModel provides both database ORM and data validation in one package.

Tables:
    - User: System users (Planners, Managers, Admins)
    - BudgetFile: Uploaded file metadata and workflow status
    - BudgetItem: Individual budget line items (normalized structure)

Author: CPP Development Team
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Numeric, Enum as SAEnum

# Import our enums from config
import sys
sys.path.append('..')
from config import FileStatus, UserRole, ChannelType


# =============================================================================
# USER MODEL
# =============================================================================

class User(SQLModel, table=True):
    """
    System users - planners who upload files and managers who approve them.
    
    Attributes:
        id: Primary key
        username: Unique login name
        email: User's email address
        full_name: Display name
        role: User's role (planner/manager/admin)
        password_hash: Hashed password (never store plain text!)
        is_active: Whether user can login
        created_at: Account creation timestamp
        
    Relationships:
        uploaded_files: Files this user has uploaded
        reviewed_files: Files this user has reviewed (managers only)
    """
    __tablename__ = "users"
    
    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # User Credentials
    username: str = Field(
        sa_column=Column(String(50), unique=True, nullable=False, index=True),
        description="Unique username for login"
    )
    email: Optional[str] = Field(
        sa_column=Column(String(100), unique=True),
        default=None,
        description="User email address"
    )
    password_hash: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Bcrypt hashed password"
    )
    
    # Profile Information
    full_name: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="User's display name"
    )
    
    # Role and Status
    role: UserRole = Field(
        sa_column=Column(SAEnum(UserRole), nullable=False, default=UserRole.PLANNER),
        default=UserRole.PLANNER,
        description="User role: planner, manager, or admin"
    )
    is_active: bool = Field(
        default=True,
        description="Whether user account is active"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Account creation timestamp"
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="Last successful login timestamp"
    )
    
    # Relationships (back-references to BudgetFile)
    # These will be populated by SQLModel automatically
    uploaded_files: List["BudgetFile"] = Relationship(
        back_populates="uploader",
        sa_relationship_kwargs={"foreign_keys": "[BudgetFile.uploader_id]"}
    )
    reviewed_files: List["BudgetFile"] = Relationship(
        back_populates="reviewer",
        sa_relationship_kwargs={"foreign_keys": "[BudgetFile.reviewer_id]"}
    )


# =============================================================================
# BUDGET FILE MODEL
# =============================================================================

class BudgetFile(SQLModel, table=True):
    """
    Tracks uploaded Excel files and their workflow status.
    
    Workflow States:
        DRAFT -> User uploaded but not submitted
        PENDING -> Submitted for manager review
        APPROVED -> Manager approved
        REJECTED -> Manager rejected (with comment)
        PUBLISHED -> Final, archived to dashboard
    
    Attributes:
        id: Primary key
        filename: Original uploaded filename
        channel_type: Marketing channel (TV, OOH, FM, etc.)
        status: Current workflow status
        uploader_id: Foreign key to User who uploaded
        reviewer_id: Foreign key to User who reviewed (manager)
        uploaded_at: Upload timestamp
        submitted_at: When submitted for review
        reviewed_at: When manager made decision
        reviewer_comment: Manager's feedback
        row_count: Number of data rows in file
        total_amount: Sum of all budget amounts
        
    Relationships:
        uploader: User who uploaded this file
        reviewer: User who reviewed this file
        items: List of BudgetItem rows from this file
    """
    __tablename__ = "budget_files"
    
    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # File Information
    filename: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Original filename of uploaded Excel"
    )
    channel_type: ChannelType = Field(
        sa_column=Column(SAEnum(ChannelType), nullable=False),
        description="Marketing channel type"
    )
    file_hash: Optional[str] = Field(
        sa_column=Column(String(64)),
        default=None,
        description="MD5 hash for duplicate detection"
    )
    
    # Workflow Status
    status: FileStatus = Field(
        sa_column=Column(SAEnum(FileStatus), nullable=False, default=FileStatus.DRAFT),
        default=FileStatus.DRAFT,
        description="Current workflow status"
    )
    
    # Foreign Keys - Links to Users
    uploader_id: int = Field(
        foreign_key="users.id",
        description="User who uploaded this file"
    )
    reviewer_id: Optional[int] = Field(
        default=None,
        foreign_key="users.id",
        description="Manager who reviewed this file"
    )
    
    # Timestamps
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When file was uploaded"
    )
    submitted_at: Optional[datetime] = Field(
        default=None,
        description="When file was submitted for review"
    )
    reviewed_at: Optional[datetime] = Field(
        default=None,
        description="When manager made decision"
    )
    published_at: Optional[datetime] = Field(
        default=None,
        description="When file was published to dashboard"
    )
    
    # Review Information
    reviewer_comment: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Manager's feedback or rejection reason"
    )
    
    # Summary Statistics (calculated on upload)
    row_count: int = Field(
        default=0,
        description="Number of data rows in file"
    )
    total_amount: Optional[Decimal] = Field(
        sa_column=Column(Numeric(15, 2)),
        default=None,
        description="Sum of all amount_planned values"
    )
    
    # Relationships
    uploader: Optional[User] = Relationship(
        back_populates="uploaded_files",
        sa_relationship_kwargs={"foreign_keys": "[BudgetFile.uploader_id]"}
    )
    reviewer: Optional[User] = Relationship(
        back_populates="reviewed_files",
        sa_relationship_kwargs={"foreign_keys": "[BudgetFile.reviewer_id]"}
    )
    items: List["BudgetItem"] = Relationship(
        back_populates="budget_file",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


# =============================================================================
# BUDGET ITEM MODEL (Normalized/Generic Structure)
# =============================================================================

class BudgetItem(SQLModel, table=True):
    """
    Individual budget line items extracted from Excel files.
    
    DESIGN DECISION - Generic/Normalized Structure:
    Since different channels (TV, OOH, FM) have different column structures,
    we use generic metric fields (metric_1, metric_2, metric_3) to store
    channel-specific data. The meaning of each metric depends on channel_type.
    
    Example Mapping:
        TV:  metric_1 = Duration (sec), metric_2 = Frequency (spots)
        OOH: metric_1 = Size, metric_2 = Quantity
        FM:  metric_1 = Duration (sec), metric_2 = Spots per day
    
    Attributes:
        id: Primary key
        file_id: Foreign key to parent BudgetFile
        row_number: Original row number in Excel (for traceability)
        
        # Core Fields (present in all files)
        campaign_name: Marketing campaign name
        budget_code: Budget tracking code
        vendor: Company/agency providing service
        channel: Channel type (redundant with file, but useful for queries)
        sub_channel: Specific channel (TV station name, billboard location)
        amount_planned: Budget amount in local currency
        start_date: Campaign start date
        end_date: Campaign end date
        
        # Generic Metric Fields (meaning varies by channel)
        metric_1: First flexible metric (Duration/Size/etc.)
        metric_2: Second flexible metric (Frequency/Quantity/etc.)
        metric_3: Third flexible metric (GRP/etc.)
        
        # Additional Fields
        description: Notes or comments
        
    Relationships:
        budget_file: Parent BudgetFile this item belongs to
    """
    __tablename__ = "budget_items"
    
    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign Key to Parent File
    file_id: int = Field(
        foreign_key="budget_files.id",
        index=True,
        description="Parent BudgetFile ID"
    )
    
    # Traceability
    row_number: Optional[int] = Field(
        default=None,
        description="Original row number in Excel file"
    )
    
    # ===================
    # CORE REQUIRED FIELDS
    # ===================
    
    campaign_name: str = Field(
        sa_column=Column(String(255), nullable=False, index=True),
        description="Marketing campaign name"
    )
    
    budget_code: str = Field(
        sa_column=Column(String(50), nullable=False, index=True),
        description="Budget tracking code"
    )
    
    # ===================
    # CORE OPTIONAL FIELDS
    # ===================
    
    vendor: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None,
        description="Company/agency name"
    )
    
    channel: ChannelType = Field(
        sa_column=Column(SAEnum(ChannelType), nullable=False),
        description="Marketing channel type (TV, FM, OOH, etc.)"
    )
    
    sub_channel: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None,
        description="Specific sub-channel (TV station, radio station, location)"
    )
    
    amount_planned: Optional[Decimal] = Field(
        sa_column=Column(Numeric(15, 2)),
        default=None,
        description="Planned budget amount"
    )
    
    start_date: Optional[datetime] = Field(
        default=None,
        description="Campaign start date"
    )
    
    end_date: Optional[datetime] = Field(
        default=None,
        description="Campaign end date"
    )
    
    # ===================
    # GENERIC METRIC FIELDS
    # ===================
    # These store channel-specific data in a normalized way
    # See METRIC_LABELS in column_maps.py for what each means per channel
    
    metric_1: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Flexible metric 1: Duration(TV/FM), Size(OOH), Impressions(Digital)"
    )
    
    metric_2: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Flexible metric 2: Frequency(TV/FM), Quantity(OOH), Clicks(Digital)"
    )
    
    metric_3: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Flexible metric 3: GRP(TV), unused for most channels"
    )
    
    # ===================
    # ADDITIONAL FIELDS
    # ===================
    
    description: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Notes, comments, or additional information"
    )
    
    # Relationship back to parent file
    budget_file: Optional[BudgetFile] = Relationship(back_populates="items")
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was created"
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_metric_label(channel: ChannelType, metric_name: str) -> Optional[str]:
    """
    Get human-readable label for a metric field based on channel type.
    
    Args:
        channel: The channel type (TV, OOH, FM, etc.)
        metric_name: The metric field name (metric_1, metric_2, metric_3)
    
    Returns:
        Human-readable label or None if not defined
        
    Example:
        >>> get_metric_label(ChannelType.TV, "metric_1")
        "Duration (sec)"
    """
    from mappings.column_maps import METRIC_LABELS
    
    channel_labels = METRIC_LABELS.get(channel.value, {})
    return channel_labels.get(metric_name)

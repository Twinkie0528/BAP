"""
Configuration Settings for Central Planning Platform (CPP)
==========================================================

This file contains all configuration variables for the application.
Modify DATABASE_URL to switch between SQLite (development) and PostgreSQL (production).

Author: CPP Development Team
"""

import os
from enum import Enum

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# For Development (SQLite) - Easy setup, no server needed
SQLITE_URL = "sqlite:///./cpp_database.db"

# For Production (PostgreSQL) - Uncomment and configure when ready
# Format: postgresql://username:password@host:port/database_name
POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/cpp_db"
)

# Toggle this to switch databases
# Options: "sqlite" or "postgresql"
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite")

# Active database URL based on type
DATABASE_URL = SQLITE_URL if DATABASE_TYPE == "sqlite" else POSTGRES_URL


# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

APP_NAME = "Central Planning Platform"
APP_VERSION = "1.0.0"

# Session timeout in minutes
SESSION_TIMEOUT = 30

# Maximum file upload size (in MB)
MAX_UPLOAD_SIZE_MB = 50


# =============================================================================
# ENUMS - Status and Role Definitions
# =============================================================================

class FileStatus(str, Enum):
    """
    Budget file workflow statuses.
    
    Workflow: DRAFT -> PENDING -> APPROVED/REJECTED -> PUBLISHED
    """
    DRAFT = "draft"           # Just uploaded, not submitted
    PENDING = "pending"       # Submitted for review
    APPROVED = "approved"     # Manager approved
    REJECTED = "rejected"     # Manager rejected (needs revision)
    PUBLISHED = "published"   # Archived to database, visible in dashboard


class UserRole(str, Enum):
    """
    User roles for access control.
    """
    PLANNER = "planner"       # Can upload, edit drafts, submit
    MANAGER = "manager"       # Can review, approve, reject
    ADMIN = "admin"           # Full access + user management


class ChannelType(str, Enum):
    """
    Marketing channel types.
    Each channel may have different Excel column structures.
    """
    TV = "TV"                 # Television advertising
    FM = "FM"                 # Radio/FM advertising  
    OOH = "OOH"               # Out-of-Home (billboards, etc.)
    DIGITAL = "Digital"       # Online/Digital marketing
    PRINT = "Print"           # Newspaper, magazine ads
    EVENT = "Event"           # Events and activations
    OTHER = "Other"           # Miscellaneous


# =============================================================================
# FILE PROCESSING SETTINGS
# =============================================================================

# Maximum rows to skip when searching for header row
MAX_HEADER_SEARCH_ROWS = 15

# Keywords to identify the header row (English and Mongolian)
HEADER_KEYWORDS = [
    "budget code", "төсвийн код",
    "campaign", "кампанит",
    "amount", "дүн",
    "vendor", "компани",
]

# Supported file extensions
SUPPORTED_EXTENSIONS = [".xlsx", ".xls", ".csv"]

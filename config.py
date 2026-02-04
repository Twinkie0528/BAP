"""
Configuration Settings for Central Planning Platform (CPP)
==========================================================

This file contains all configuration variables for the application.
Environment variables are loaded from .env file for security.

Author: CPP Development Team
"""

import os
from enum import Enum

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# For Development (SQLite) - Easy setup, no server needed
SQLITE_URL = "sqlite:///./cpp_database.db"

# For Production (PostgreSQL) - Load from environment variable
# NEVER hardcode passwords! Use .env file or system environment variables
POSTGRES_URL = os.getenv("DATABASE_URL", SQLITE_URL)

# Toggle this to switch databases
# Options: "sqlite" or "postgresql"
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite")

# Active database URL based on type
DATABASE_URL = SQLITE_URL if DATABASE_TYPE == "sqlite" else POSTGRES_URL

# JWT Secret Key - MUST be set in .env for production
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-change-in-production")


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
    Budget file workflow statuses - 4-Stage Strict Workflow.
    
    Stage 1: PENDING_APPROVAL - Planner uploaded, awaiting manager review (NOT visible on dashboard)
    Stage 2: APPROVED_FOR_PRINT - Manager approved, planner can generate PDF
    Stage 3: SIGNING - Planner downloaded PDF, getting physical signatures offline
    Stage 4: FINALIZED - Signed document uploaded, data visible on main dashboard
    REJECTED: Manager rejected, planner needs to fix and resubmit
    """
    PENDING_APPROVAL = "pending_approval"      # Stage 1: Uploaded, awaiting approval
    APPROVED_FOR_PRINT = "approved_for_print"  # Stage 2: Approved, ready for PDF
    SIGNING = "signing"                        # Stage 3: PDF generated, awaiting signed scan
    FINALIZED = "finalized"                    # Stage 4: Complete, visible on dashboard
    REJECTED = "rejected"                      # Rejected, needs revision


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


class BudgetType(str, Enum):
    """
    Budget types for file categorization.
    """
    PRIMARY = "primary"       # Үндсэн төсөв - Main campaign budget
    ADDITIONAL = "additional" # Нэмэлт төсөв - Additional/supplementary budget


# =============================================================================
# FILE PROCESSING SETTINGS
# =============================================================================

# Maximum rows to skip when searching for header row
MAX_HEADER_SEARCH_ROWS = 30

# Keywords to identify the header row (Mongolian budget template)
HEADER_KEYWORDS = [
    # Primary Mongolian keywords
    "төрөл", "хийгдэх ажил", "нийт төсөв", "давтамж", "тайлбар",
    "хару|/хугацаа", "цогц унэ", "хару|/",
    # Section headers (for detecting budget sections)
    "сурталчилгааны суваг", "суваг", "контент", "арга хэмжээ",
    # English fallback
    "type", "budget", "amount", "description", "frequency",
]

# Supported file extensions
SUPPORTED_EXTENSIONS = [".xlsx", ".xls", ".csv"]

# =============================================================================
# FILE STORAGE SETTINGS
# =============================================================================

# Directory for uploaded budget files
UPLOAD_FOLDER = "assets/uploaded_files"

# Directory for storing signed documents (on disk, not in DB)
SIGNED_FILES_DIR = "assets/signed_files"

# Allowed file types for signed document uploads
ALLOWED_SIGNED_FILE_TYPES = [".pdf", ".jpg", ".jpeg", ".png"]

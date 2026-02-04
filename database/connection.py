"""
Database Connection Manager for Central Planning Platform (CPP)
===============================================================

This module handles all database connections using SQLModel/SQLAlchemy.
Supports both SQLite (development) and PostgreSQL (production).

Usage:
    from database.connection import get_session, init_db
    
    # Initialize database (creates tables)
    init_db()
    
    # Use in Streamlit
    with get_session() as session:
        users = session.exec(select(User)).all()

Author: CPP Development Team
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlmodel import SQLModel, Session, create_engine, text
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Import configuration
from config import DATABASE_URL, DATABASE_TYPE

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# ENGINE CONFIGURATION
# =============================================================================

def get_engine_args() -> dict:
    """
    Get database-specific engine arguments.
    
    SQLite needs special handling for multi-threading in Streamlit.
    PostgreSQL uses connection pooling for better performance.
    
    Returns:
        Dictionary of engine configuration arguments
    """
    if DATABASE_TYPE == "sqlite":
        return {
            # SQLite doesn't support multiple threads by default
            # This allows Streamlit's threaded execution to work
            "connect_args": {"check_same_thread": False},
            # Echo SQL statements for debugging (disable in production)
            "echo": False,
        }
    else:
        # PostgreSQL configuration - Optimized for 15-20 concurrent users
        return {
            # Connection pool settings for production
            "pool_size": 15,             # Base connections (matches expected users)
            "max_overflow": 20,          # Extra connections for peak load (total max: 35)
            "pool_timeout": 30,          # Seconds to wait for connection
            "pool_recycle": 1800,        # Recycle connections after 30 minutes
            "pool_pre_ping": True,       # Test connections before use
            "echo": False,
        }


# Create the database engine (singleton pattern)
# This is created once and reused throughout the application
engine = create_engine(DATABASE_URL, **get_engine_args())


# =============================================================================
# SQLITE FOREIGN KEY ENFORCEMENT
# =============================================================================

# SQLite doesn't enforce foreign keys by default - this enables them
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enable foreign key constraints and WAL mode for SQLite connections.
    WAL mode allows concurrent reads while writing.
    This runs automatically when a new connection is created.
    """
    if DATABASE_TYPE == "sqlite":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        cursor.execute("PRAGMA busy_timeout=5000")  # Wait 5 sec if locked
        cursor.close()


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Automatically handles commit/rollback and session cleanup.
    Use with 'with' statement for proper resource management.
    
    Usage:
        with get_session() as session:
            user = session.exec(select(User).where(User.id == 1)).first()
            session.add(new_user)
            # Auto-commits on exit, rolls back on exception
    
    Yields:
        SQLModel Session object
        
    Raises:
        Exception: Re-raises any database exceptions after rollback
    """
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        session.close()


def get_session_for_streamlit():
    """
    Alternative session getter for Streamlit's session state.
    
    Streamlit sometimes needs a persistent session across reruns.
    Store the session in st.session_state and manage lifecycle manually.
    
    Returns:
        New Session object (caller must manage commit/close)
        
    Note:
        Remember to call session.close() when done!
    """
    return Session(engine, expire_on_commit=False)


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This function is idempotent - safe to call multiple times.
    Existing tables and data are not affected.
    
    Usage:
        Call this once at application startup (in app.py):
        
        from database.connection import init_db
        init_db()
    """
    # Import models to register them with SQLModel
    from .models import User, BudgetFile, BudgetItem
    
    logger.info(f"Initializing database: {DATABASE_TYPE}")
    logger.info(f"Connection URL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created successfully")


def drop_all_tables() -> None:
    """
    DROP ALL TABLES - USE WITH EXTREME CAUTION!
    
    This function deletes all data. Only use for:
    - Development/testing database resets
    - Never use in production without backup!
    """
    logger.warning("⚠️  DROPPING ALL TABLES - THIS WILL DELETE ALL DATA!")
    SQLModel.metadata.drop_all(engine)
    logger.info("All tables dropped")


# =============================================================================
# HEALTH CHECK
# =============================================================================

def check_database_connection() -> bool:
    """
    Test the database connection.
    
    Useful for health checks and startup verification.
    
    Returns:
        True if connection successful, False otherwise
        
    Example:
        if not check_database_connection():
            st.error("Database connection failed!")
    """
    try:
        with get_session() as session:
            # Try a simple query
            session.exec(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False


def get_database_info() -> dict:
    """
    Get information about the current database configuration.
    
    Returns:
        Dictionary with database type, status, and table info
    """
    info = {
        "database_type": DATABASE_TYPE,
        "connected": check_database_connection(),
        "tables": [],
    }
    
    try:
        # Get list of tables
        info["tables"] = list(SQLModel.metadata.tables.keys())
    except Exception as e:
        info["error"] = str(e)
    
    return info


# =============================================================================
# SEEDING (Development Only)
# =============================================================================

def seed_demo_users() -> None:
    """
    Create initial admin users for the system.
    
    Creates 3 admin users with @unitel.mn emails:
        - admin1@unitel.mn (Admin role)
        - admin2@unitel.mn (Admin role)
        - admin3@unitel.mn (Admin role)
    
    Also creates legacy demo users for backward compatibility.
    """
    from .models import User
    from config import UserRole
    
    # Use proper password hashing
    try:
        from modules.jwt_auth import hash_password
    except ImportError:
        import hashlib
        def hash_password(password: str) -> str:
            return hashlib.sha256(password.encode()).hexdigest()
    
    # Initial admin users with @unitel.mn emails
    admin_users = [
        {
            "username": "admin1",
            "email": "admin1@unitel.mn",
            "full_name": "Admin One",
            "role": UserRole.ADMIN,
            "password_hash": hash_password("Admin123!"),
        },
        {
            "username": "admin2",
            "email": "admin2@unitel.mn",
            "full_name": "Admin Two",
            "role": UserRole.ADMIN,
            "password_hash": hash_password("Admin123!"),
        },
        {
            "username": "admin3",
            "email": "admin3@unitel.mn",
            "full_name": "Admin Three",
            "role": UserRole.ADMIN,
            "password_hash": hash_password("Admin123!"),
        },
    ]
    
    # Legacy demo users (for backward compatibility)
    legacy_users = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "full_name": "System Admin",
            "role": UserRole.ADMIN,
            "password_hash": hash_password("admin123"),
        },
        {
            "username": "manager",
            "email": "manager@example.com", 
            "full_name": "Marketing Manager",
            "role": UserRole.MANAGER,
            "password_hash": hash_password("manager123"),
        },
        {
            "username": "planner",
            "email": "planner@example.com",
            "full_name": "Marketing Planner",
            "role": UserRole.PLANNER,
            "password_hash": hash_password("planner123"),
        },
    ]
    
    all_users = admin_users + legacy_users
    
    with get_session() as session:
        from sqlmodel import select
        
        for user_data in all_users:
            # Check if user already exists by email
            existing = session.exec(
                select(User).where(User.email == user_data["email"])
            ).first()
            
            if not existing:
                # Also check by username
                existing_username = session.exec(
                    select(User).where(User.username == user_data["username"])
                ).first()
                
                if not existing_username:
                    user = User(**user_data)
                    session.add(user)
                    logger.info(f"Created user: {user_data['email']}")
                else:
                    logger.info(f"Username already exists: {user_data['username']}")
            else:
                logger.info(f"User already exists: {user_data['email']}")
    
    logger.info("Users seeded successfully")


# =============================================================================
# MAIN - For testing connection
# =============================================================================

if __name__ == "__main__":
    """
    Run this file directly to test database connection:
        python database/connection.py
    """
    print("Testing database connection...")
    print(f"Database type: {DATABASE_TYPE}")
    print(f"URL: {DATABASE_URL}")
    
    # Initialize and test
    init_db()
    
    
    if check_database_connection():
        print("✅ Connection successful!")
        print(f"Tables: {get_database_info()['tables']}")
        
        # Seed demo users
        print("\nSeeding demo users...")
        seed_demo_users()
    else:
        print("❌ Connection failed!")

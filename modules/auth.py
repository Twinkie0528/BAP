"""
Authentication Utilities for Central Planning Platform (CPP)
============================================================

Simple authentication helpers for Streamlit.
Uses bcrypt for secure password hashing.

Usage:
    from modules.auth import authenticate_user, hash_password
    
    # Hash password for storage
    hashed = hash_password("my_password")
    
    # Authenticate user
    user = authenticate_user("username", "password")

Author: CPP Development Team
"""

import hashlib
from typing import Optional

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("⚠️ bcrypt not installed. Using SHA256 fallback (less secure).")

import sys
sys.path.append('..')
from database.models import User
from modules.services import get_user_by_username, update_user_last_login


# =============================================================================
# PASSWORD HASHING
# =============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password for secure storage.
    
    Uses bcrypt if available, falls back to SHA256.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string
    """
    if BCRYPT_AVAILABLE:
        # Generate salt and hash
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    else:
        # Fallback to SHA256 (less secure, but works)
        return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to check
        hashed: Stored hash to compare against
    
    Returns:
        True if password matches, False otherwise
    """
    if BCRYPT_AVAILABLE:
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed.encode('utf-8')
            )
        except Exception:
            # If bcrypt fails, try SHA256 (for backwards compatibility)
            return hashlib.sha256(password.encode()).hexdigest() == hashed
    else:
        return hashlib.sha256(password.encode()).hexdigest() == hashed


# =============================================================================
# USER AUTHENTICATION
# =============================================================================

def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user by username and password.
    
    Args:
        username: User's username
        password: Plain text password
    
    Returns:
        User object if authenticated, None otherwise
    """
    user = get_user_by_username(username)
    
    if user and user.is_active:
        if verify_password(password, user.password_hash):
            # Update last login time
            update_user_last_login(user.id)
            return user
    
    return None


# =============================================================================
# STREAMLIT SESSION HELPERS
# =============================================================================

def init_session_state():
    """
    Initialize Streamlit session state for authentication.
    
    Call this at the start of your Streamlit app.
    """
    import streamlit as st
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None


def login_user(user: User):
    """
    Set session state after successful login.
    
    Args:
        user: Authenticated User object
    """
    import streamlit as st
    
    st.session_state.authenticated = True
    st.session_state.user = user
    st.session_state.user_id = user.id
    st.session_state.user_role = user.role.value


def logout_user():
    """Clear session state on logout."""
    import streamlit as st
    
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.user_id = None
    st.session_state.user_role = None


def require_auth():
    """
    Decorator/function to require authentication.
    
    Usage in Streamlit page:
        if not require_auth():
            st.stop()
    
    Returns:
        True if authenticated, shows login form and returns False otherwise
    """
    import streamlit as st
    
    init_session_state()
    
    if st.session_state.authenticated:
        return True
    
    # Show login form
    st.title("🔐 Login Required")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            user = authenticate_user(username, password)
            
            if user:
                login_user(user)
                st.success(f"Welcome, {user.full_name or user.username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    return False


def require_role(required_roles: list):
    """
    Check if current user has required role.
    
    Args:
        required_roles: List of allowed roles (e.g., ['manager', 'admin'])
    
    Returns:
        True if user has required role, False otherwise
    """
    import streamlit as st
    
    if not st.session_state.authenticated:
        return False
    
    return st.session_state.user_role in required_roles


def get_current_user() -> Optional[User]:
    """Get the currently logged in user."""
    import streamlit as st
    
    if st.session_state.authenticated:
        return st.session_state.user
    return None


def get_current_user_id() -> Optional[int]:
    """Get the currently logged in user's ID."""
    import streamlit as st
    
    if st.session_state.authenticated:
        return st.session_state.user_id
    return None

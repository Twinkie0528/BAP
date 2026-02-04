"""
JWT Authentication Module for BAP
==================================

Secure JWT-based authentication with:
- Token generation and validation
- Cookie-based session persistence
- @unitel.mn email domain restriction
- 7-day token expiration

Author: BAP Development Team
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import streamlit as st

# JWT library
try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("⚠️ python-jose not installed. Run: pip install python-jose[cryptography]")

# Password hashing
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    PASSLIB_AVAILABLE = True
except ImportError:
    PASSLIB_AVAILABLE = False
    print("⚠️ passlib not installed. Run: pip install passlib[bcrypt]")


# =============================================================================
# CONFIGURATION
# =============================================================================

# Secret key for JWT signing (in production, use environment variable!)
SECRET_KEY = "bap-secret-key-change-in-production-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Allowed email domains
ALLOWED_EMAIL_DOMAINS = ["unitel.mn"]

# Cookie settings
COOKIE_NAME = "bap_auth_token"
COOKIE_EXPIRY_DAYS = 7


# =============================================================================
# PASSWORD HASHING
# =============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string
    """
    if PASSLIB_AVAILABLE:
        return pwd_context.hash(password)
    else:
        # Fallback to SHA256 (less secure)
        return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to check
        hashed_password: Stored hash
    
    Returns:
        True if password matches
    """
    if PASSLIB_AVAILABLE:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            # Try SHA256 fallback for old hashes
            return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password
    else:
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


# =============================================================================
# EMAIL VALIDATION
# =============================================================================

def validate_email_domain(email: str) -> bool:
    """
    Check if email domain is allowed.
    
    Args:
        email: Email address to check
    
    Returns:
        True if domain is in ALLOWED_EMAIL_DOMAINS
    """
    if not email or "@" not in email:
        return False
    
    domain = email.split("@")[-1].lower().strip()
    return domain in ALLOWED_EMAIL_DOMAINS


def validate_email_format(email: str) -> bool:
    """
    Basic email format validation.
    
    Args:
        email: Email address to check
    
    Returns:
        True if valid email format
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# =============================================================================
# JWT TOKEN MANAGEMENT
# =============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data (user_id, username, role, etc.)
        expires_delta: Optional custom expiration time
    
    Returns:
        JWT token string
    """
    if not JWT_AVAILABLE:
        raise RuntimeError("python-jose library not installed")
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_hex(16)  # Unique token ID
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload dict if valid, None otherwise
    """
    if not JWT_AVAILABLE:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get token expiration datetime.
    
    Args:
        token: JWT token string
    
    Returns:
        Expiration datetime or None
    """
    payload = verify_token(token)
    if payload and "exp" in payload:
        return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    return None


# =============================================================================
# COOKIE MANAGEMENT (Streamlit-compatible)
# =============================================================================

def set_auth_cookie(token: str):
    """
    Store JWT token in session state (Streamlit doesn't support real cookies easily).
    We use session_state + a marker for persistence.
    
    Args:
        token: JWT token to store
    """
    st.session_state["jwt_token"] = token
    st.session_state["jwt_token_set_at"] = datetime.now(timezone.utc).isoformat()


def get_auth_cookie() -> Optional[str]:
    """
    Get JWT token from session state.
    
    Returns:
        JWT token or None
    """
    return st.session_state.get("jwt_token")


def clear_auth_cookie():
    """Clear JWT token from session state."""
    if "jwt_token" in st.session_state:
        del st.session_state["jwt_token"]
    if "jwt_token_set_at" in st.session_state:
        del st.session_state["jwt_token_set_at"]


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

def init_jwt_session():
    """Initialize JWT session state variables."""
    if "jwt_token" not in st.session_state:
        st.session_state["jwt_token"] = None
    if "jwt_user" not in st.session_state:
        st.session_state["jwt_user"] = None
    if "jwt_authenticated" not in st.session_state:
        st.session_state["jwt_authenticated"] = False


def get_current_user_from_token() -> Optional[Dict[str, Any]]:
    """
    Get current user info from JWT token.
    
    Returns:
        User dict with id, username, email, role, full_name or None
    """
    init_jwt_session()
    
    # Check cached user first
    if st.session_state.get("jwt_authenticated") and st.session_state.get("jwt_user"):
        return st.session_state["jwt_user"]
    
    # Try to get token
    token = get_auth_cookie()
    if not token:
        return None
    
    # Verify token
    payload = verify_token(token)
    if not payload:
        # Token invalid or expired
        clear_auth_cookie()
        st.session_state["jwt_authenticated"] = False
        st.session_state["jwt_user"] = None
        return None
    
    # Extract user info
    user_info = {
        "id": payload.get("sub"),
        "username": payload.get("username"),
        "email": payload.get("email"),
        "role": payload.get("role"),
        "full_name": payload.get("full_name")
    }
    
    # Cache in session
    st.session_state["jwt_authenticated"] = True
    st.session_state["jwt_user"] = user_info
    
    return user_info


def login_with_jwt(user) -> str:
    """
    Create JWT token and set session after successful authentication.
    
    Args:
        user: User object from database
    
    Returns:
        JWT token string
    """
    # Create token payload
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "full_name": user.full_name
    }
    
    # Generate token
    token = create_access_token(token_data)
    
    # Set cookie/session
    set_auth_cookie(token)
    
    # User info for session (with 'id' key for consistency)
    user_info = {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "full_name": user.full_name
    }
    
    # Update session state
    st.session_state["jwt_authenticated"] = True
    st.session_state["jwt_user"] = user_info
    
    return token


def logout_jwt():
    """Clear JWT session and logout user."""
    clear_auth_cookie()
    st.session_state["jwt_authenticated"] = False
    st.session_state["jwt_user"] = None
    
    # Clear legacy session state
    if "authenticated" in st.session_state:
        st.session_state["authenticated"] = False
    if "user" in st.session_state:
        st.session_state["user"] = None
    if "user_id" in st.session_state:
        st.session_state["user_id"] = None
    if "user_role" in st.session_state:
        st.session_state["user_role"] = None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    user = get_current_user_from_token()
    return user is not None


def require_auth_jwt():
    """
    Require authentication. Returns user if authenticated, None otherwise.
    Use: if not require_auth_jwt(): st.stop()
    """
    user = get_current_user_from_token()
    if not user:
        return None
    return user


def require_role_jwt(allowed_roles: list) -> bool:
    """
    Check if current user has one of the allowed roles.
    
    Args:
        allowed_roles: List of allowed role strings ['admin', 'manager']
    
    Returns:
        True if user has required role
    """
    user = get_current_user_from_token()
    if not user:
        return False
    
    return user.get("role", "").lower() in [r.lower() for r in allowed_roles]


# =============================================================================
# USER REGISTRATION & AUTHENTICATION
# =============================================================================

def register_user(email: str, password: str, full_name: str) -> tuple[bool, str]:
    """
    Register a new user.
    
    Args:
        email: User's email (must be @unitel.mn)
        password: Plain text password
        full_name: User's full name
    
    Returns:
        Tuple of (success, message)
    """
    from database import get_session, User
    from config import UserRole
    from sqlmodel import select
    
    # Validate email format
    if not validate_email_format(email):
        return False, "Email формат буруу байна"
    
    # Validate email domain
    if not validate_email_domain(email):
        allowed = ", ".join(ALLOWED_EMAIL_DOMAINS)
        return False, f"Зөвхөн @{allowed} email бүртгүүлэх боломжтой"
    
    # Validate password
    if len(password) < 6:
        return False, "Нууц үг хамгийн багадаа 6 тэмдэгт байх ёстой"
    
    # Validate full name
    if not full_name or len(full_name.strip()) < 2:
        return False, "Нэрээ оруулна уу"
    
    email = email.lower().strip()
    username = email.split("@")[0]  # Use email prefix as username
    
    with get_session() as session:
        # Check if email already exists
        existing = session.exec(
            select(User).where(User.email == email)
        ).first()
        
        if existing:
            return False, "Энэ email бүртгэлтэй байна"
        
        # Check if username already exists
        existing_username = session.exec(
            select(User).where(User.username == username)
        ).first()
        
        if existing_username:
            # Add number suffix to username
            import random
            username = f"{username}{random.randint(1, 999)}"
        
        # Create new user (default role: PLANNER)
        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            role=UserRole.PLANNER,
            is_active=True
        )
        
        session.add(new_user)
        session.commit()
        
        return True, "Амжилттай бүртгэгдлээ! Нэвтэрнэ үү."


def authenticate_user_jwt(email: str, password: str):
    """
    Authenticate user by email and password.
    
    Args:
        email: User's email
        password: Plain text password
    
    Returns:
        User object if authenticated, None otherwise
    """
    from database import get_session, User
    from sqlmodel import select
    
    email = email.lower().strip()
    
    with get_session() as session:
        # Try to find by email first
        user = session.exec(
            select(User).where(User.email == email)
        ).first()
        
        # If not found by email, try username
        if not user:
            user = session.exec(
                select(User).where(User.username == email)
            ).first()
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return user


# =============================================================================
# ADMIN USER MANAGEMENT
# =============================================================================

def get_all_users() -> list:
    """Get all users for admin management."""
    from database import get_session, User
    from sqlmodel import select
    
    with get_session() as session:
        users = session.exec(select(User).order_by(User.created_at.desc())).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
                "is_active": u.is_active,
                "created_at": u.created_at,
                "last_login": u.last_login
            }
            for u in users
        ]


def update_user_role(user_id: int, new_role: str) -> tuple[bool, str]:
    """
    Update user's role.
    
    Args:
        user_id: User ID
        new_role: New role string (admin, manager, planner)
    
    Returns:
        Tuple of (success, message)
    """
    from database import get_session, User
    from config import UserRole
    from sqlmodel import select
    
    try:
        role_enum = UserRole(new_role.lower())
    except ValueError:
        return False, f"Буруу role: {new_role}"
    
    with get_session() as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        
        if not user:
            return False, "Хэрэглэгч олдсонгүй"
        
        user.role = role_enum
        session.add(user)
        session.commit()
        
        return True, f"Role амжилттай солигдлоо: {new_role}"


def toggle_user_active(user_id: int) -> tuple[bool, str]:
    """
    Toggle user's active status.
    
    Args:
        user_id: User ID
    
    Returns:
        Tuple of (success, message)
    """
    from database import get_session, User
    from sqlmodel import select
    
    with get_session() as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        
        if not user:
            return False, "Хэрэглэгч олдсонгүй"
        
        user.is_active = not user.is_active
        session.add(user)
        session.commit()
        
        status = "идэвхжүүллээ" if user.is_active else "идэвхгүй болголоо"
        return True, f"Хэрэглэгчийг {status}"


def reset_user_password(user_id: int, new_password: str) -> tuple[bool, str]:
    """
    Reset user's password (Admin only).
    
    Args:
        user_id: User ID
        new_password: New password
    
    Returns:
        Tuple of (success, message)
    """
    from database import get_session, User
    from sqlmodel import select
    
    if len(new_password) < 6:
        return False, "Нууц үг хамгийн багадаа 6 тэмдэгт байх ёстой"
    
    with get_session() as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        
        if not user:
            return False, "Хэрэглэгч олдсонгүй"
        
        user.password_hash = hash_password(new_password)
        session.add(user)
        session.commit()
        
        return True, "Нууц үг амжилттай солигдлоо"

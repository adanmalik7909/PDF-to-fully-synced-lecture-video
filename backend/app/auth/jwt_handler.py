"""JWT Token Handler - Create and verify tokens"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
from app.config import settings
from app.utils.logger import log_error, log_debug

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode in token (e.g., {"sub": user_id, "role": "teacher"})
        expires_delta: Token expiration time delta
    
    Returns:
        Encoded JWT token
    """
    try:
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        log_debug(f"Token created for user: {data.get('sub')}")
        return encoded_jwt
    
    except Exception as e:
        log_error(f"Error creating token: {str(e)}", exc_info=True)
        raise

def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token to verify
    
    Returns:
        Decoded token payload
    
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    
    except jwt.ExpiredSignatureError:
        log_error("Token has expired")
        raise
    
    except jwt.InvalidTokenError as e:
        log_error(f"Invalid token: {str(e)}")
        raise

def extract_user_id_from_token(token: str) -> int:
    """Extract user ID from token"""
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("Token does not contain user ID")
        return user_id
    except Exception as e:
        log_error(f"Error extracting user ID: {str(e)}")
        raise

def extract_user_role_from_token(token: str) -> str:
    """Extract user role from token"""
    try:
        payload = verify_token(token)
        role = payload.get("role")
        if role is None:
            raise ValueError("Token does not contain user role")
        return role
    except Exception as e:
        log_error(f"Error extracting role: {str(e)}")
        raise

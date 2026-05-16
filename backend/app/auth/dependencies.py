"""FastAPI Dependency for JWT Authentication"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.jwt_handler import verify_token, extract_user_id_from_token, extract_user_role_from_token
from app.database.db import get_db, SessionLocal
from app.database.models import User
from sqlalchemy.orm import Session
from app.utils.logger import log_error, log_warning

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer token
        db: Database session
    
    Returns:
        Current authenticated user
    
    Raises:
        HTTPException: 401 Unauthorized if token is invalid or expired
    """
    token = credentials.credentials
    
    try:
        # Verify token and extract user ID
        user_id = extract_user_id_from_token(token)
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        
        if user is None:
            log_warning(f"User {user_id} not found or inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
    
    except Exception as e:
        log_error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to verify current user is a teacher"""
    if current_user.role not in ["teacher", "admin"]:
        log_warning(f"Non-teacher user {current_user.id} attempted teacher action")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user

async def get_current_student(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to verify current user is a student"""
    if current_user.role not in ["student"]:
        log_warning(f"Non-student user {current_user.id} attempted student action")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this resource"
        )
    return current_user

async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to verify current user is an admin"""
    if current_user.role != "admin":
        log_warning(f"Non-admin user {current_user.id} attempted admin action")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this resource"
        )
    return current_user

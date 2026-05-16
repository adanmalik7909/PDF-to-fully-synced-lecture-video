"""Password Hashing and Verification Utilities"""
from passlib.context import CryptContext
from app.utils.logger import log_error, log_debug

# Password hashing context
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    try:
        hashed = pwd_context.hash(password)
        log_debug("Password hashed successfully")
        return hashed
    except Exception as e:
        log_error(f"Error hashing password: {str(e)}", exc_info=True)
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        if is_valid:
            log_debug("Password verification successful")
        return is_valid
    except Exception as e:
        log_error(f"Error verifying password: {str(e)}")
        return False

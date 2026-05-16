"""Database connection and initialization"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from app.utils.logger import log_info, log_error

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.SQLALCHEMY_ECHO
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Get database session - dependency injection for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database - create all tables"""
    try:
        log_info("[DB] Initializing database...")
        Base.metadata.create_all(bind=engine)
        log_info("[DB] Database initialized successfully")
    except Exception as e:
        log_error(f"[DB] Database initialization failed: {e}")
        # Don't raise, let the app try to start anyway as it might be non-fatal for static assets


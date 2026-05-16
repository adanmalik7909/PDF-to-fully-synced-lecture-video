"""
Database Seeding Script - Create Demo Users

Creates demo accounts for testing:
- teacher01 / Teacher@123 (teacher)
- student01 / Student@123 (student)
- admin01 / Admin@123 (admin)
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.db import get_db, init_db
from app.database.models import User
from app.auth.password_utils import hash_password
from app.utils.logger import log_info, log_warning

def seed_demo_users():
    """Create demo users if they don't already exist"""
    
    # Initialize database
    init_db()
    
    db = next(get_db())
    
    demo_users = [
        {
            "username": "teacher01",
            "email": "teacher@demo.com",
            "password": "Teacher@123",
            "role": "teacher"
        },
        {
            "username": "student01",
            "email": "student@demo.com",
            "password": "Student@123",
            "role": "student"
        },
        {
            "username": "admin01",
            "email": "admin@demo.com",
            "password": "Admin@123",
            "role": "admin"
        }
    ]
    
    created_count = 0
    
    for user_data in demo_users:
        # Check if user already exists
        existing_user = db.query(User).filter(
            User.username == user_data["username"]
        ).first()
        
        if existing_user:
            log_warning(f"User '{user_data['username']}' already exists, skipping...")
            continue
        
        # Create new user
        new_user = User(
            username=user_data["username"],
            email=user_data["email"],
            password_hash=hash_password(user_data["password"]),
            role=user_data["role"],
            is_active=True
        )
        
        db.add(new_user)
        created_count += 1
        log_info(f"✓ Created user: {user_data['username']} ({user_data['role']})")
    
    if created_count > 0:
        db.commit()
        log_info(f"\n✅ Successfully created {created_count} demo user(s)")
    else:
        log_info("\n✅ All demo users already exist")
    
    print("\n" + "="*60)
    print("Demo User Credentials:")
    print("="*60)
    for user_data in demo_users:
        print(f"  {user_data['role'].upper()}: {user_data['username']} / {user_data['password']}")
    print("="*60)
    
    db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("SmartStudyInstructor - Database Seeding")
    print("=" * 60)
    print()
    
    seed_demo_users()

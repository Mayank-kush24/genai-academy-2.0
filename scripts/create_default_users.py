"""
Script to create default system users with properly hashed passwords
Run this after creating the system_users table
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import create_user, DEFAULT_ROLE_PERMISSIONS, get_all_users
from app.database import db_manager

def main():
    """Create default users"""
    
    print("="*60)
    print("Creating Default System Users")
    print("="*60)
    
    # Initialize database
    db_manager.initialize()
    
    # Check existing users
    existing_users = get_all_users()
    print(f"\nFound {len(existing_users)} existing users")
    
    if existing_users:
        print("\nExisting users:")
        for user in existing_users:
            print(f"  - {user.username} ({user.role}) - {user.email}")
        print("\nSkipping user creation. Users already exist.")
        return
    
    print("\nNo users found. Creating default users...")
    
    # Create admin user
    print("\n1. Creating Admin user...")
    admin_user, error = create_user(
        username='admin',
        password='Admin@123',
        email='admin@academy.local',
        full_name='System Administrator',
        role='admin'
    )
    
    if error:
        print(f"   ERROR: {error}")
    else:
        print(f"   ✓ Admin created successfully!")
        print(f"     Username: admin")
        print(f"     Password: Admin@123")
        print(f"     Email: {admin_user.email}")
    
    # Create manager user
    print("\n2. Creating Manager user...")
    manager_user, error = create_user(
        username='manager',
        password='Manager@123',
        email='manager@academy.local',
        full_name='Program Manager',
        role='manager'
    )
    
    if error:
        print(f"   ERROR: {error}")
    else:
        print(f"   ✓ Manager created successfully!")
        print(f"     Username: manager")
        print(f"     Password: Manager@123")
        print(f"     Email: {manager_user.email}")
    
    # Create viewer user
    print("\n3. Creating Viewer user...")
    viewer_user, error = create_user(
        username='viewer',
        password='Viewer@123',
        email='viewer@academy.local',
        full_name='Data Viewer',
        role='viewer'
    )
    
    if error:
        print(f"   ERROR: {error}")
    else:
        print(f"   ✓ Viewer created successfully!")
        print(f"     Username: viewer")
        print(f"     Password: Viewer@123")
        print(f"     Email: {viewer_user.email}")
    
    print("\n" + "="*60)
    print("Default Users Created Successfully!")
    print("="*60)
    print("\nYou can now login with:")
    print("  Admin:   admin / Admin@123")
    print("  Manager: manager / Manager@123")
    print("  Viewer:  viewer / Viewer@123")
    print("\n⚠️  IMPORTANT: Change these default passwords after first login!")
    print("="*60)


if __name__ == '__main__':
    main()


"""
Authentication and Authorization Module
Handles user login, permissions, and access control
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, JSON
from sqlalchemy.sql import func
from datetime import datetime
import json

from app.database import Base, db_manager


class SystemUser(Base):
    """System user model for authentication"""
    __tablename__ = 'system_users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default='viewer')
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON, default={})
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    last_login = Column(TIMESTAMP)
    
    def __repr__(self):
        return f"<SystemUser(username='{self.username}', role='{self.role}')>"
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        """Check if user has a specific permission"""
        # Admin has all permissions
        if self.role == 'admin':
            return True
        
        # Check in permissions JSON
        if isinstance(self.permissions, dict):
            return self.permissions.get(permission, False)
        
        return False
    
    def get_permissions(self):
        """Get all user permissions"""
        if self.role == 'admin':
            return {
                'view_dashboard': True,
                'view_badge_stats': True,
                'view_profiles': True,
                'view_data': True,
                'import_data': True,
                'export_data': True,
                'manage_users': True,
                'verification_queue': True
            }
        
        return self.permissions if isinstance(self.permissions, dict) else {}
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'permissions': self.get_permissions(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


# Default role permissions
DEFAULT_ROLE_PERMISSIONS = {
    'admin': {
        'view_dashboard': True,
        'view_badge_stats': True,
        'view_profiles': True,
        'view_data': True,
        'import_data': True,
        'export_data': True,
        'manage_users': True,
        'verification_queue': True
    },
    'manager': {
        'view_dashboard': True,
        'view_badge_stats': True,
        'view_profiles': True,
        'view_data': True,
        'import_data': True,
        'export_data': True,
        'manage_users': False,
        'verification_queue': True
    },
    'viewer': {
        'view_dashboard': True,
        'view_badge_stats': True,
        'view_profiles': True,
        'view_data': True,
        'import_data': False,
        'export_data': False,
        'manage_users': False,
        'verification_queue': False
    }
}


def get_current_user():
    """Get current logged-in user"""
    if 'user_id' not in session:
        return None
    
    db_session = db_manager.get_session()
    try:
        user = db_session.query(SystemUser).filter_by(
            user_id=session['user_id'],
            is_active=True
        ).first()
        
        if user:
            db_session.expunge(user)
        
        return user
    finally:
        db_manager.close_session(db_session)


def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        user = get_current_user()
        if not user:
            session.clear()
            flash('Session expired. Please login again.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission):
    """Decorator to require specific permission for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please login to access this page.', 'warning')
                return redirect(url_for('login', next=request.url))
            
            user = get_current_user()
            if not user:
                session.clear()
                flash('Session expired. Please login again.', 'warning')
                return redirect(url_for('login', next=request.url))
            
            if not user.has_permission(permission):
                flash(f'You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator to require admin role for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        user = get_current_user()
        if not user:
            session.clear()
            flash('Session expired. Please login again.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        if user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def authenticate_user(username, password):
    """Authenticate user with username and password"""
    db_session = db_manager.get_session()
    try:
        user = db_session.query(SystemUser).filter_by(
            username=username,
            is_active=True
        ).first()
        
        if user and user.check_password(password):
            # Update last login
            user.last_login = datetime.utcnow()
            db_session.commit()
            
            # Refresh and expunge to make independent
            db_session.refresh(user)
            db_session.expunge(user)
            
            return user
        
        return None
    finally:
        db_manager.close_session(db_session)


def create_user(username, password, email, full_name, role='viewer', permissions=None):
    """Create a new system user"""
    db_session = db_manager.get_session()
    try:
        # Check if username or email already exists
        existing = db_session.query(SystemUser).filter(
            (SystemUser.username == username) | (SystemUser.email == email)
        ).first()
        
        if existing:
            if existing.username == username:
                return None, "Username already exists"
            else:
                return None, "Email already exists"
        
        # Set default permissions based on role
        if permissions is None:
            permissions = DEFAULT_ROLE_PERMISSIONS.get(role, DEFAULT_ROLE_PERMISSIONS['viewer'])
        
        # Create new user
        new_user = SystemUser(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            permissions=permissions,
            is_active=True
        )
        new_user.set_password(password)
        
        db_session.add(new_user)
        db_session.commit()
        
        # Refresh to load all attributes before closing session
        db_session.refresh(new_user)
        
        # Make the object independent of the session
        db_session.expunge(new_user)
        
        return new_user, None
    except Exception as e:
        db_session.rollback()
        return None, str(e)
    finally:
        db_manager.close_session(db_session)


def update_user(user_id, **kwargs):
    """Update user information"""
    db_session = db_manager.get_session()
    try:
        user = db_session.query(SystemUser).filter_by(user_id=user_id).first()
        
        if not user:
            return None, "User not found"
        
        # Update allowed fields
        allowed_fields = ['full_name', 'email', 'role', 'permissions', 'is_active']
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        # Update password if provided
        if 'password' in kwargs and kwargs['password']:
            user.set_password(kwargs['password'])
        
        db_session.commit()
        
        # Refresh and expunge to make object independent
        db_session.refresh(user)
        db_session.expunge(user)
        
        return user, None
    except Exception as e:
        db_session.rollback()
        return None, str(e)
    finally:
        db_manager.close_session(db_session)


def delete_user(user_id):
    """Soft delete user (set is_active to False)"""
    db_session = db_manager.get_session()
    try:
        user = db_session.query(SystemUser).filter_by(user_id=user_id).first()
        
        if not user:
            return False, "User not found"
        
        if user.role == 'admin':
            # Check if this is the last admin
            admin_count = db_session.query(SystemUser).filter_by(
                role='admin',
                is_active=True
            ).count()
            
            if admin_count <= 1:
                return False, "Cannot delete the last admin user"
        
        user.is_active = False
        db_session.commit()
        return True, None
    except Exception as e:
        db_session.rollback()
        return False, str(e)
    finally:
        db_manager.close_session(db_session)


def get_all_users():
    """Get all system users"""
    db_session = db_manager.get_session()
    try:
        users = db_session.query(SystemUser).order_by(SystemUser.created_at.desc()).all()
        
        # Expunge all to make them independent of session
        for user in users:
            db_session.expunge(user)
        
        return users
    finally:
        db_manager.close_session(db_session)


def get_user_by_id(user_id):
    """Get user by ID"""
    db_session = db_manager.get_session()
    try:
        user = db_session.query(SystemUser).filter_by(user_id=user_id).first()
        
        if user:
            db_session.expunge(user)
        
        return user
    finally:
        db_manager.close_session(db_session)


"""
Database models and connection management
SQLAlchemy ORM models for all tables
"""
from sqlalchemy import create_engine, Column, String, Boolean, Integer, Date, Text, TIMESTAMP, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from config import Config

Base = declarative_base()


class UserPII(Base):
    """User Personal Information"""
    __tablename__ = 'user_pii'
    
    email = Column(String(255), primary_key=True)
    name = Column(String(255))
    phone_number = Column(String(50))
    gender = Column(String(50))
    country = Column(String(100))
    state = Column(String(100))
    city = Column(String(100))
    date_of_birth = Column(Date)
    designation = Column(String(255))
    class_stream = Column(String(100))
    degree_passout_year = Column(Text)  # Changed from Integer to Text to accommodate full degree info
    occupation = Column(String(255))
    linkedin = Column(String(500))
    participated_in_academy_1 = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    courses = relationship("Course", back_populates="user", cascade="all, delete-orphan")
    skillboost_profiles = relationship("SkillboostProfile", back_populates="user", cascade="all, delete-orphan")
    master_classes = relationship("MasterClass", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserPII(email='{self.email}', name='{self.name}')>"


class Course(Base):
    """Course Badge Submissions"""
    __tablename__ = 'courses'
    
    email = Column(String(255), ForeignKey('user_pii.email', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    problem_statement = Column(Text, primary_key=True)
    share_skill_badge_public_link = Column(Text)
    valid = Column(Boolean, default=None, nullable=True)
    remarks = Column(Text)
    completion_date = Column(Date, nullable=True)  # Date when badge was earned
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("UserPII", back_populates="courses")
    
    def __repr__(self):
        return f"<Course(email='{self.email}', problem_statement='{self.problem_statement}', valid={self.valid})>"


class SkillboostProfile(Base):
    """Skillboost Profile Links"""
    __tablename__ = 'skillboost_profile'
    
    email = Column(String(255), ForeignKey('user_pii.email', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    google_cloud_skills_boost_profile_link = Column(Text, primary_key=True)
    valid = Column(Boolean, default=None, nullable=True)
    remarks = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("UserPII", back_populates="skillboost_profiles")
    
    def __repr__(self):
        return f"<SkillboostProfile(email='{self.email}', valid={self.valid})>"


class MasterClass(Base):
    """Masterclass Attendance"""
    __tablename__ = 'master_classes'
    
    email = Column(String(255), ForeignKey('user_pii.email', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    master_class_name = Column(String(255), primary_key=True)
    platform = Column(String(100))
    link = Column(Text)
    total_duration = Column(Integer)  # in minutes
    time_watched = Column(String(50))  # Legacy field
    watch_time = Column(Integer)  # in minutes
    live = Column(Boolean, default=None, nullable=True)  # TRUE = verified live, FALSE = invalid, NULL = pending
    recorded = Column(Boolean, default=None, nullable=True)  # TRUE = verified recorded, FALSE = invalid, NULL = pending
    valid = Column(Boolean, default=True)  # Legacy field
    started_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    watched_duration_updated_at = Column(TIMESTAMP)
    
    # Relationships
    user = relationship("UserPII", back_populates="master_classes")
    
    def __repr__(self):
        return f"<MasterClass(email='{self.email}', master_class_name='{self.master_class_name}', live={self.live}, recorded={self.recorded})>"


class MasterLog(Base):
    """Audit Trail (populated automatically by database triggers)"""
    __tablename__ = 'master_log'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), nullable=False)
    record_identifier = Column(Text, nullable=False)
    action = Column(String(20), nullable=False)
    changed_fields = Column(JSONB)
    changed_at = Column(TIMESTAMP, default=datetime.utcnow)
    changed_by = Column(String(100), default='system')
    
    def __repr__(self):
        return f"<MasterLog(log_id={self.log_id}, table='{self.table_name}', action='{self.action}')>"


# Database Connection Management
class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self):
        self.engine = None
        self.Session = None
    
    def initialize(self):
        """Initialize database connection"""
        try:
            self.engine = create_engine(
                Config.SQLALCHEMY_DATABASE_URI,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=10,
                max_overflow=20
            )
            self.Session = sessionmaker(bind=self.engine)
            return True
        except Exception as e:
            print(f"Error initializing database: {e}")
            return False
    
    def get_session(self):
        """Get a new database session"""
        if self.Session is None:
            self.initialize()
        return self.Session()
    
    def close_session(self, session):
        """Close a database session"""
        if session:
            session.close()
    
    def test_connection(self):
        """Test database connectivity"""
        try:
            session = self.get_session()
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception as e:
            print(f"Database connection test failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


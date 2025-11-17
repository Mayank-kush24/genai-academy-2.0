"""
Configuration module for GenAI Academy 2.0 Records Management System
"""
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class"""
    
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'academy2_0')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # SQLAlchemy Database URI (with URL-encoded password for special characters)
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL query debugging
    
    # Flask Configuration
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # Verification Configuration
    RATE_LIMIT_DELAY = float(os.getenv('RATE_LIMIT_DELAY', 2.5))
    VERIFICATION_RETRY_ATTEMPTS = int(os.getenv('VERIFICATION_RETRY_ATTEMPTS', 3))
    VERIFICATION_TIMEOUT = int(os.getenv('VERIFICATION_TIMEOUT', 10))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # User Agents for Web Scraping (rotate to avoid blocking)
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    
    @staticmethod
    def get_db_connection_string():
        """Returns the database connection string"""
        return Config.SQLALCHEMY_DATABASE_URI
    
    @staticmethod
    def validate():
        """Validates that required configuration is present"""
        required_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True


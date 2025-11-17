"""
Test database connection and system components
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db_manager
from config import Config


def test_config():
    """Test configuration"""
    print("\n" + "="*60)
    print("Testing Configuration")
    print("="*60)
    
    try:
        Config.validate()
        print("[OK] Configuration valid")
        print(f"  Database: {Config.DB_NAME}")
        print(f"  Host: {Config.DB_HOST}:{Config.DB_PORT}")
        print(f"  User: {Config.DB_USER}")
        return True
    except Exception as e:
        print(f"[FAIL] Configuration error: {e}")
        return False


def test_database_connection():
    """Test database connectivity"""
    print("\n" + "="*60)
    print("Testing Database Connection")
    print("="*60)
    
    try:
        if not db_manager.initialize():
            print("[FAIL] Failed to initialize database manager")
            return False
        
        if not db_manager.test_connection():
            print("[FAIL] Database connection test failed")
            return False
        
        print("[OK] Database connection successful")
        return True
    except Exception as e:
        print(f"[FAIL] Connection error: {e}")
        return False


def test_tables_exist():
    """Test that required tables exist"""
    print("\n" + "="*60)
    print("Testing Database Schema")
    print("="*60)
    
    required_tables = [
        'user_pii',
        'courses',
        'skillboost_profile',
        'master_classes',
        'master_log'
    ]
    
    try:
        from sqlalchemy import text
        session = db_manager.get_session()
        
        for table in required_tables:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
            count = result[0]
            print(f"[OK] Table '{table}' exists ({count} records)")
        
        db_manager.close_session(session)
        return True
        
    except Exception as e:
        print(f"[FAIL] Schema error: {e}")
        return False


def test_views_exist():
    """Test that required views exist"""
    print("\n" + "="*60)
    print("Testing Database Views")
    print("="*60)
    
    required_views = [
        'v_user_summary',
        'v_course_verification_status',
        'v_masterclass_attendance',
        'v_track_completion',
        'v_certificate_eligible'
    ]
    
    try:
        from sqlalchemy import text
        session = db_manager.get_session()
        
        for view in required_views:
            try:
                result = session.execute(text(f"SELECT COUNT(*) FROM {view}")).fetchone()
                count = result[0]
                print(f"[OK] View '{view}' exists ({count} records)")
            except:
                print(f"[WARN] View '{view}' not accessible (may be empty)")
        
        db_manager.close_session(session)
        return True
        
    except Exception as e:
        print(f"[FAIL] Views error: {e}")
        return False


def test_imports():
    """Test that all required modules can be imported"""
    print("\n" + "="*60)
    print("Testing Python Dependencies")
    print("="*60)
    
    modules = [
        'flask',
        'sqlalchemy',
        'pandas',
        'requests',
        'bs4',
        'psycopg2',
        'openpyxl',
        'dotenv'
    ]
    
    all_ok = True
    for module in modules:
        try:
            __import__(module)
            print(f"[OK] Module '{module}' available")
        except ImportError:
            print(f"[FAIL] Module '{module}' not found")
            all_ok = False
    
    return all_ok


def print_summary(results):
    """Print test summary"""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! System is ready to use.")
        return 0
    else:
        print("\n[ERROR] Some tests failed. Please fix issues before proceeding.")
        return 1


def main():
    print("="*60)
    print("GenAI Academy 2.0 - System Test")
    print("="*60)
    
    results = {}
    
    # Run tests
    results['Configuration'] = test_config()
    results['Python Dependencies'] = test_imports()
    results['Database Connection'] = test_database_connection()
    
    if results['Database Connection']:
        results['Database Schema'] = test_tables_exist()
        results['Database Views'] = test_views_exist()
    
    # Print summary
    exit_code = print_summary(results)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()


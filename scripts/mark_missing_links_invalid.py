"""
Script to mark badge records with missing or "-" badge links as invalid
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db_manager, Course

def mark_missing_links_invalid():
    """Mark all badge records with "-" or empty badge links as invalid"""
    session = db_manager.get_session()
    
    try:
        # Find all records with "-" or empty badge links
        records_to_update = session.query(Course).filter(
            (Course.share_skill_badge_public_link == '-') |
            (Course.share_skill_badge_public_link == '') |
            (Course.share_skill_badge_public_link.is_(None))
        ).all()
        
        count = 0
        for record in records_to_update:
            if record.valid is None:  # Only update pending records
                record.valid = False
                record.remarks = 'No badge link provided'
                count += 1
        
        if count > 0:
            session.commit()
            print(f"✓ Marked {count} records with missing badge links as invalid")
        else:
            print("No records found with missing badge links that need updating")
        
        # Show summary
        total_with_dash = session.query(Course).filter(
            Course.share_skill_badge_public_link == '-'
        ).count()
        
        total_empty = session.query(Course).filter(
            (Course.share_skill_badge_public_link == '') |
            (Course.share_skill_badge_public_link.is_(None))
        ).count()
        
        print(f"\nSummary:")
        print(f"  Records with '-': {total_with_dash}")
        print(f"  Records with empty/null: {total_empty}")
        print(f"  Total records updated: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        db_manager.close_session(session)

if __name__ == '__main__':
    print("=" * 60)
    print("Mark Missing Badge Links as Invalid")
    print("=" * 60)
    mark_missing_links_invalid()


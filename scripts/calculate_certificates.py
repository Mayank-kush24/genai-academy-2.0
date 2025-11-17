"""
Track Certificate Calculation Script
Identifies users eligible for track certificates based on course completion
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db_manager
from sqlalchemy import text


def calculate_track_certificates():
    """Calculate and display users eligible for track certificates"""
    
    session = db_manager.get_session()
    
    try:
        print("="*60)
        print("Track Certificate Eligibility Calculator")
        print("="*60)
        
        # Query to get certificate-eligible users
        query = text("""
            SELECT 
                email,
                name,
                track_id,
                track_name,
                completed_courses,
                total_courses_in_track
            FROM v_certificate_eligible
            ORDER BY track_name, name
        """)
        
        results = session.execute(query).fetchall()
        
        if not results:
            print("\nNo users are currently eligible for track certificates.")
            print("Users must complete all courses in a track to be eligible.")
            return
        
        # Group by track
        tracks = {}
        for row in results:
            track_name = row.track_name
            if track_name not in tracks:
                tracks[track_name] = []
            tracks[track_name].append({
                'email': row.email,
                'name': row.name,
                'completed': row.completed_courses,
                'total': row.total_courses_in_track
            })
        
        # Display results
        total_certificates = 0
        for track_name, users in tracks.items():
            print(f"\n{'='*60}")
            print(f"Track: {track_name}")
            print(f"{'='*60}")
            print(f"Eligible Users: {len(users)}")
            print()
            
            for idx, user in enumerate(users, 1):
                print(f"{idx}. {user['name']} ({user['email']})")
                print(f"   Completed: {user['completed']}/{user['total']} courses")
            
            total_certificates += len(users)
        
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tracks: {len(tracks)}")
        print(f"Total Certificates to Issue: {total_certificates}")
        print(f"{'='*60}")
        
        # Save report
        save_report(tracks, total_certificates)
        
    except Exception as e:
        print(f"Error calculating certificates: {e}")
    finally:
        db_manager.close_session(session)


def save_report(tracks, total_certificates):
    """Save certificate report to file"""
    os.makedirs('reports', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join('reports', f'certificate_eligibility_{timestamp}.txt')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write(f"Track Certificate Eligibility Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        
        for track_name, users in tracks.items():
            f.write(f"Track: {track_name}\n")
            f.write(f"Eligible Users: {len(users)}\n")
            f.write("-"*60 + "\n")
            
            for idx, user in enumerate(users, 1):
                f.write(f"{idx}. {user['name']} ({user['email']})\n")
                f.write(f"   Completed: {user['completed']}/{user['total']} courses\n")
            
            f.write("\n")
        
        f.write("="*60 + "\n")
        f.write(f"SUMMARY\n")
        f.write(f"Total Tracks: {len(tracks)}\n")
        f.write(f"Total Certificates to Issue: {total_certificates}\n")
        f.write("="*60 + "\n")
    
    print(f"\n✓ Report saved to: {report_file}")


def get_track_progress(email):
    """Get track progress for a specific user"""
    session = db_manager.get_session()
    
    try:
        query = text("""
            SELECT 
                track_name,
                total_courses_in_track,
                completed_courses,
                track_completed
            FROM v_track_completion
            WHERE email = :email
            ORDER BY track_name
        """)
        
        results = session.execute(query, {'email': email}).fetchall()
        
        if not results:
            print(f"No data found for {email}")
            return
        
        print(f"\nTrack Progress for {email}")
        print("="*60)
        
        for row in results:
            status = "✓ COMPLETED" if row.track_completed else "In Progress"
            print(f"\n{row.track_name}")
            print(f"  Progress: {row.completed_courses}/{row.total_courses_in_track} courses")
            print(f"  Status: {status}")
        
    except Exception as e:
        print(f"Error retrieving track progress: {e}")
    finally:
        db_manager.close_session(session)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate track certificate eligibility')
    parser.add_argument('--email', '-e', help='Check progress for specific user')
    
    args = parser.parse_args()
    
    # Initialize database connection
    if not db_manager.initialize():
        print("✗ Failed to connect to database. Check your configuration.")
        sys.exit(1)
    
    if args.email:
        get_track_progress(args.email)
    else:
        calculate_track_certificates()


if __name__ == '__main__':
    main()


"""
CSV Import Script for GenAI Academy 2.0
Processes weekly CSV/Excel files and imports data into PostgreSQL
"""
import sys
import os
import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db_manager, UserPII, Course, SkillboostProfile, MasterClass
from config import Config


class CSVImporter:
    """Handles CSV/Excel import and data processing"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self.stats = {
            'users_inserted': 0,
            'users_updated': 0,
            'courses_inserted': 0,
            'skillboost_profiles_inserted': 0,
            'masterclasses_inserted': 0,
            'errors': []
        }
    
    def load_file(self):
        """Load CSV or Excel file"""
        try:
            file_ext = Path(self.file_path).suffix.lower()
            
            if file_ext == '.csv':
                self.df = pd.read_csv(self.file_path, encoding='utf-8')
            elif file_ext in ['.xlsx', '.xls']:
                self.df = pd.read_excel(self.file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            print(f"✓ Loaded {len(self.df)} rows from {self.file_path}")
            print(f"✓ Columns found: {len(self.df.columns)}")
            return True
            
        except Exception as e:
            print(f"✗ Error loading file: {e}")
            return False
    
    def normalize_email(self, email):
        """Normalize email address"""
        if pd.isna(email):
            return None
        return str(email).strip().lower()
    
    def validate_email(self, email):
        """Validate email format"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def parse_date(self, date_val):
        """Parse date from various formats"""
        if pd.isna(date_val):
            return None
        
        try:
            if isinstance(date_val, str):
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                    try:
                        return datetime.strptime(date_val, fmt).date()
                    except:
                        continue
            elif isinstance(date_val, datetime):
                return date_val.date()
            elif hasattr(date_val, 'date'):
                return date_val.date()
        except:
            pass
        
        return None
    
    def extract_user_pii(self, row):
        """Extract user PII data from row"""
        email = self.normalize_email(row.get('Email', row.get('email', '')))
        
        if not email or not self.validate_email(email):
            return None
        
        return {
            'email': email,
            'name': str(row.get('Name', row.get('name', ''))).strip() if pd.notna(row.get('Name', row.get('name', ''))) else None,
            'phone_number': str(row.get('Phone number', row.get('phone_number', ''))).strip() if pd.notna(row.get('Phone number', row.get('phone_number', ''))) else None,
            'gender': str(row.get('Gender', row.get('gender', ''))).strip() if pd.notna(row.get('Gender', row.get('gender', ''))) else None,
            'country': str(row.get('country', '')).strip() if pd.notna(row.get('country', '')) else None,
            'state': str(row.get('state', '')).strip() if pd.notna(row.get('state', '')) else None,
            'city': str(row.get('city', '')).strip() if pd.notna(row.get('city', '')) else None,
            'date_of_birth': self.parse_date(row.get('Date of birth', row.get('date_of_birth', ''))),
            'designation': str(row.get('designation', '')).strip() if pd.notna(row.get('designation', '')) else None,
            'class_stream': str(row.get('Class/stream', row.get('class_stream', ''))).strip() if pd.notna(row.get('Class/stream', row.get('class_stream', ''))) else None,
            'degree_passout_year': int(row.get('Degree (passout year)', row.get('degree_passout_year', 0))) if pd.notna(row.get('Degree (passout year)', row.get('degree_passout_year', 0))) else None,
            'occupation': str(row.get('Occupation', row.get('occupation', ''))).strip() if pd.notna(row.get('Occupation', row.get('occupation', ''))) else None,
            'linkedin': str(row.get('Linkedin', row.get('linkedin', ''))).strip() if pd.notna(row.get('Linkedin', row.get('linkedin', ''))) else None,
            'participated_in_academy_1': bool(row.get('Participated in Academy 1.0?', row.get('participated_in_academy_1', False)))
        }
    
    def import_data(self):
        """Import data into database"""
        if self.df is None:
            print("✗ No data loaded. Call load_file() first.")
            return False
        
        session = db_manager.get_session()
        
        try:
            print("\n" + "="*60)
            print("Starting Data Import...")
            print("="*60)
            
            for idx, row in self.df.iterrows():
                try:
                    # Extract and upsert user PII
                    user_data = self.extract_user_pii(row)
                    
                    if not user_data:
                        self.stats['errors'].append(f"Row {idx+2}: Invalid or missing email")
                        continue
                    
                    email = user_data['email']
                    
                    # Check if user exists
                    existing_user = session.query(UserPII).filter_by(email=email).first()
                    
                    if existing_user:
                        # Update existing user
                        for key, value in user_data.items():
                            if key != 'email' and value is not None:
                                setattr(existing_user, key, value)
                        existing_user.updated_at = datetime.utcnow()
                        self.stats['users_updated'] += 1
                    else:
                        # Insert new user
                        new_user = UserPII(**user_data)
                        session.add(new_user)
                        self.stats['users_inserted'] += 1
                    
                    # Process course badge submission
                    problem_statement = row.get('problemstatement', row.get('Problem statement', ''))
                    badge_link = row.get('Share the Skill Badge public link', row.get('share_skill_badge_public_link', ''))
                    
                    if pd.notna(problem_statement) and str(problem_statement).strip():
                        problem_statement = str(problem_statement).strip()
                        badge_link = str(badge_link).strip() if pd.notna(badge_link) else None
                        
                        existing_course = session.query(Course).filter_by(
                            email=email,
                            problem_statement=problem_statement
                        ).first()
                        
                        if not existing_course:
                            new_course = Course(
                                email=email,
                                problem_statement=problem_statement,
                                share_skill_badge_public_link=badge_link,
                                valid=None  # Will be verified later
                            )
                            session.add(new_course)
                            self.stats['courses_inserted'] += 1
                        elif badge_link and existing_course.share_skill_badge_public_link != badge_link:
                            # Update badge link if changed
                            existing_course.share_skill_badge_public_link = badge_link
                            existing_course.valid = None  # Reset validation
                            existing_course.updated_at = datetime.utcnow()
                    
                    # Process Skillboost profile link
                    profile_link = row.get('Share your Google Cloud Skills Boost public profile link', 
                                         row.get('google_cloud_skills_boost_profile_link', ''))
                    
                    if pd.notna(profile_link) and str(profile_link).strip():
                        profile_link = str(profile_link).strip()
                        
                        existing_profile = session.query(SkillboostProfile).filter_by(
                            email=email,
                            google_cloud_skills_boost_profile_link=profile_link
                        ).first()
                        
                        if not existing_profile:
                            new_profile = SkillboostProfile(
                                email=email,
                                google_cloud_skills_boost_profile_link=profile_link,
                                valid=None  # Will be verified later
                            )
                            session.add(new_profile)
                            self.stats['skillboost_profiles_inserted'] += 1
                    
                    # Process masterclass attendance (look for columns with masterclass names)
                    for col in self.df.columns:
                        if 'masterclass' in col.lower() or 'master class' in col.lower():
                            attendance = row.get(col, '')
                            if pd.notna(attendance) and str(attendance).strip().lower() in ['live', 'recorded', 'yes', 'attended']:
                                master_class_name = col
                                time_watched = 'live' if 'live' in str(attendance).lower() else 'recorded'
                                
                                existing_mc = session.query(MasterClass).filter_by(
                                    email=email,
                                    master_class_name=master_class_name
                                ).first()
                                
                                if not existing_mc:
                                    new_mc = MasterClass(
                                        email=email,
                                        master_class_name=master_class_name,
                                        time_watched=time_watched
                                    )
                                    session.add(new_mc)
                                    self.stats['masterclasses_inserted'] += 1
                    
                    # Commit every 100 rows for better performance
                    if (idx + 1) % 100 == 0:
                        session.commit()
                        print(f"  Processed {idx + 1} rows...")
                
                except Exception as e:
                    self.stats['errors'].append(f"Row {idx+2}: {str(e)}")
                    continue
            
            # Final commit
            session.commit()
            print("\n✓ Data import completed successfully!")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"\n✗ Error during import: {e}")
            return False
        finally:
            db_manager.close_session(session)
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Users Inserted:              {self.stats['users_inserted']}")
        print(f"Users Updated:               {self.stats['users_updated']}")
        print(f"Courses Inserted:            {self.stats['courses_inserted']}")
        print(f"Skillboost Profiles Added:   {self.stats['skillboost_profiles_inserted']}")
        print(f"Masterclasses Recorded:      {self.stats['masterclasses_inserted']}")
        print(f"Errors:                      {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print("\nErrors encountered:")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more errors")
        
        print("="*60)
    
    def save_report(self, output_dir='reports'):
        """Save import report to file"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(output_dir, f'import_report_{timestamp}.txt')
        
        with open(report_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write(f"Import Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n")
            f.write(f"Source File: {self.file_path}\n\n")
            f.write(f"Users Inserted:              {self.stats['users_inserted']}\n")
            f.write(f"Users Updated:               {self.stats['users_updated']}\n")
            f.write(f"Courses Inserted:            {self.stats['courses_inserted']}\n")
            f.write(f"Skillboost Profiles Added:   {self.stats['skillboost_profiles_inserted']}\n")
            f.write(f"Masterclasses Recorded:      {self.stats['masterclasses_inserted']}\n")
            f.write(f"Errors:                      {len(self.stats['errors'])}\n\n")
            
            if self.stats['errors']:
                f.write("\nErrors:\n")
                for error in self.stats['errors']:
                    f.write(f"  - {error}\n")
        
        print(f"\n✓ Report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description='Import CSV/Excel data into Academy database')
    parser.add_argument('--file', '-f', required=True, help='Path to CSV or Excel file')
    parser.add_argument('--verify', '-v', action='store_true', help='Run verification after import')
    
    args = parser.parse_args()
    
    # Initialize database connection
    if not db_manager.initialize():
        print("✗ Failed to connect to database. Check your configuration.")
        sys.exit(1)
    
    print("✓ Database connection established")
    
    # Create importer and process file
    importer = CSVImporter(args.file)
    
    if not importer.load_file():
        sys.exit(1)
    
    if not importer.import_data():
        sys.exit(1)
    
    importer.print_summary()
    importer.save_report()
    
    # Run verification if requested
    if args.verify:
        print("\n" + "="*60)
        print("Starting Skillboost Verification...")
        print("="*60)
        from verify_skillboost import run_verification
        run_verification()


if __name__ == '__main__':
    main()


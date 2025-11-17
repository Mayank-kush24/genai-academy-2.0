"""
CSV Import Module with Column Mapping
Similar to ESPO CRM import functionality
"""
import pandas as pd
import os
from datetime import datetime, date
from sqlalchemy import text
from app.database import db_manager, UserPII, Course, SkillboostProfile, MasterClass


class CSVImporter:
    """Handles CSV import with column mapping and operation modes"""
    
    def __init__(self, file_path, column_mapping, operation_mode='create', update_keys=None, auto_inject_columns=None):
        """
        Initialize CSV importer
        
        Args:
            file_path: Path to CSV file
            column_mapping: Dict mapping CSV columns to database columns
            operation_mode: 'create', 'update', or 'create_update'
            update_keys: List of columns to use as update keys (for matching existing records)
            auto_inject_columns: Dict of column_name: value to automatically inject into all rows
        """
        self.file_path = file_path
        self.column_mapping = column_mapping
        self.operation_mode = operation_mode
        self.update_keys = update_keys or ['email']
        self.auto_inject_columns = auto_inject_columns or {}
        
        self.stats = {
            'total_rows': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
    
    def load_csv(self):
        """Load CSV file"""
        try:
            self.df = pd.read_csv(self.file_path, encoding='utf-8')
            self.stats['total_rows'] = len(self.df)
            return True
        except Exception as e:
            self.stats['errors'].append(f"Error loading CSV: {str(e)}")
            return False
    
    def get_csv_preview(self, rows=5):
        """Get preview of CSV data"""
        if hasattr(self, 'df'):
            return self.df.head(rows).to_dict('records')
        return []
    
    def import_data(self, table_name='user_pii'):
        """Import data with mapping and operation mode"""
        if not hasattr(self, 'df'):
            if not self.load_csv():
                return False
        
        print(f"[DEBUG IMPORT] Starting import for table: {table_name}")
        print(f"[DEBUG IMPORT] Total rows in CSV: {len(self.df)}")
        
        session = db_manager.get_session()
        
        try:
            # Apply column mapping - rename CSV columns to database columns
            mapped_df = self.df.rename(columns=self.column_mapping)
            
            # Filter to only keep mapped columns that exist in target
            valid_columns = [col for col in mapped_df.columns if col in self.column_mapping.values()]
            mapped_df = mapped_df[valid_columns]
            
            print(f"[DEBUG IMPORT] Mapped columns: {valid_columns}")
            print(f"[DEBUG IMPORT] Operation mode: {self.operation_mode}")
            print(f"[DEBUG IMPORT] Update keys: {self.update_keys}")
            
            for idx, row in mapped_df.iterrows():
                try:
                    row_dict = row.to_dict()
                    
                    # Remove NaN values
                    row_dict = {k: v for k, v in row_dict.items() if pd.notna(v)}
                    
                    # Data type conversions
                    for key, value in row_dict.items():
                        if isinstance(value, str):
                            # Boolean conversion
                            if value.strip().lower() in ['yes', 'true', '1']:
                                row_dict[key] = True
                            elif value.strip().lower() in ['no', 'false', '0']:
                                row_dict[key] = False
                            # Time format conversion (MM:SS to minutes) for watch_time and total_duration
                            elif key in ['watch_time', 'total_duration', 'time_watched'] and ':' in value:
                                try:
                                    # Parse MM:SS or HH:MM:SS format and convert to total minutes
                                    parts = value.strip().split(':')
                                    if len(parts) == 2:  # MM:SS format
                                        minutes = int(parts[0])
                                        row_dict[key] = minutes
                                        print(f"[DEBUG IMPORT] Converted time {value} to {minutes} minutes for {key}")
                                    elif len(parts) == 3:  # HH:MM:SS format
                                        hours = int(parts[0])
                                        minutes = int(parts[1])
                                        total_minutes = (hours * 60) + minutes
                                        row_dict[key] = total_minutes
                                        print(f"[DEBUG IMPORT] Converted time {value} to {total_minutes} minutes for {key}")
                                except (ValueError, IndexError) as e:
                                    # If parsing fails, try to extract just the number before the colon
                                    try:
                                        row_dict[key] = int(value.split(':')[0])
                                        print(f"[DEBUG IMPORT] Fallback conversion: {value} to {row_dict[key]} for {key}")
                                    except:
                                        print(f"[DEBUG IMPORT] Failed to convert time format: {value} for {key}")
                                        pass
                            # Date/DateTime conversion for date_of_birth field
                            elif key == 'date_of_birth' and value:
                                try:
                                    # Try parsing ISO format date
                                    if 'T' in value:
                                        row_dict[key] = datetime.fromisoformat(value.replace('Z', '+00:00')).date()
                                    else:
                                        row_dict[key] = datetime.strptime(value, '%Y-%m-%d').date()
                                except:
                                    # If parsing fails, keep as string and let DB handle it
                                    pass
                    
                    # Inject auto columns (e.g., master_class_name)
                    if self.auto_inject_columns:
                        for col_name, col_value in self.auto_inject_columns.items():
                            row_dict[col_name] = col_value
                            print(f"[DEBUG IMPORT] Auto-injecting {col_name} = {col_value}")
                    
                    if table_name == 'user_pii':
                        self._import_user_pii(session, row_dict)
                    elif table_name == 'courses':
                        self._import_course(session, row_dict)
                    elif table_name == 'skillboost_profile':
                        self._import_skillboost_profile(session, row_dict)
                    elif table_name == 'master_classes':
                        self._import_masterclass(session, row_dict)
                    
                    # Commit after each successful row to avoid losing data on errors
                    try:
                        session.commit()
                        if (idx + 1) % 100 == 0:
                            print(f"[DEBUG IMPORT] Processed {idx + 1} rows... (Created: {self.stats['created']}, Updated: {self.stats['updated']}, Skipped: {self.stats['skipped']})")
                    except Exception as commit_error:
                        session.rollback()
                        self.stats['errors'].append(f"Row {idx + 2} commit failed: {str(commit_error)}")
                        self.stats['skipped'] += 1
                        if len(self.stats['errors']) <= 5:  # Print first 5 errors
                            print(f"[DEBUG IMPORT ERROR] Row {idx + 2} commit failed: {str(commit_error)}")
                
                except Exception as e:
                    # Rollback the failed row to allow processing to continue
                    session.rollback()
                    self.stats['errors'].append(f"Row {idx + 2}: {str(e)}")
                    self.stats['skipped'] += 1
                    if len(self.stats['errors']) <= 5:  # Print first 5 errors for debugging
                        print(f"[DEBUG IMPORT ERROR] Row {idx + 2}: {str(e)}")
                    continue
            
            # All rows are committed individually, so just print final stats
            print(f"[DEBUG IMPORT] Import completed! Created: {self.stats['created']}, Updated: {self.stats['updated']}, Skipped: {self.stats['skipped']}, Errors: {len(self.stats['errors'])}")
            return True
            
        except Exception as e:
            session.rollback()
            error_msg = f"Import error: {str(e)}"
            print(f"[DEBUG IMPORT ERROR] {error_msg}")
            self.stats['errors'].append(error_msg)
            return False
        finally:
            db_manager.close_session(session)
    
    def _import_user_pii(self, session, row_dict):
        """Import user PII data"""
        # Ensure email exists
        if 'email' not in row_dict or not row_dict['email']:
            self.stats['skipped'] += 1
            return
        
        # Normalize email
        row_dict['email'] = str(row_dict['email']).strip().lower()
        
        # Build filter for update keys
        filter_dict = {key: row_dict.get(key) for key in self.update_keys if key in row_dict}
        
        # Check if record exists based on update keys
        existing = session.query(UserPII).filter_by(**filter_dict).first()
        
        if existing:
            # Record exists
            if self.operation_mode == 'create':
                # Create only mode - skip
                self.stats['skipped'] += 1
                return
            elif self.operation_mode in ['update', 'create_update']:
                # Update existing record
                for key, value in row_dict.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                self.stats['updated'] += 1
        else:
            # Record doesn't exist
            if self.operation_mode == 'update':
                # Update only mode - skip
                self.stats['skipped'] += 1
                return
            elif self.operation_mode in ['create', 'create_update']:
                # Create new record
                new_user = UserPII(**row_dict)
                session.add(new_user)
                self.stats['created'] += 1
    
    def _import_course(self, session, row_dict):
        """
        Import course data with special logic:
        - Always check by composite primary key (email, problem_statement)
        - If existing record has valid=TRUE, do NOT update (keep verified record)
        - If existing record has valid=FALSE or NULL, allow update (keep latest)
        """
        if 'email' not in row_dict or 'problem_statement' not in row_dict:
            self.stats['skipped'] += 1
            return
        
        # Normalize email
        row_dict['email'] = str(row_dict['email']).strip().lower()
        
        # Always check by composite primary key (email + problem_statement)
        existing = session.query(Course).filter_by(
            email=row_dict['email'],
            problem_statement=row_dict['problem_statement']
        ).first()
        
        if existing:
            # Check if existing record is already verified
            if existing.valid is True:
                # Don't update verified records - keep the valid one
                self.stats['skipped'] += 1
                print(f"[DEBUG IMPORT] Skipped course badge for {row_dict['email']}: Already verified as valid")
                return
            
            # Existing record is FALSE or NULL - allow update
            if self.operation_mode in ['update', 'create_update']:
                # Reset validation status when updating with new link
                for key, value in row_dict.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                # Reset validation fields for re-verification
                existing.valid = None
                existing.remarks = None
                existing.updated_at = datetime.utcnow()
                self.stats['updated'] += 1
            else:
                self.stats['skipped'] += 1
        else:
            if self.operation_mode in ['create', 'create_update']:
                new_course = Course(**row_dict)
                session.add(new_course)
                self.stats['created'] += 1
            else:
                self.stats['skipped'] += 1
    
    def _import_skillboost_profile(self, session, row_dict):
        """
        Import Skillboost profile data with special logic:
        - Always check by composite primary key (email, google_cloud_skills_boost_profile_link)
        - If existing record has valid=TRUE, do NOT update (keep verified record)
        - If existing record has valid=FALSE or NULL, allow update (keep latest)
        """
        if 'email' not in row_dict or 'google_cloud_skills_boost_profile_link' not in row_dict:
            self.stats['skipped'] += 1
            return
        
        # Normalize email
        row_dict['email'] = str(row_dict['email']).strip().lower()
        
        # Always check by composite primary key (email + profile_link)
        existing = session.query(SkillboostProfile).filter_by(
            email=row_dict['email'],
            google_cloud_skills_boost_profile_link=row_dict['google_cloud_skills_boost_profile_link']
        ).first()
        
        if existing:
            # Check if existing record is already verified
            if existing.valid is True:
                # Don't update verified records - keep the valid one
                self.stats['skipped'] += 1
                print(f"[DEBUG IMPORT] Skipped skillboost profile for {row_dict['email']}: Already verified as valid")
                return
            
            # Existing record is FALSE or NULL - allow update
            if self.operation_mode in ['update', 'create_update']:
                # Reset validation status when updating with new link
                for key, value in row_dict.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                # Reset validation fields for re-verification
                existing.valid = None
                existing.remarks = None
                existing.updated_at = datetime.utcnow()
                self.stats['updated'] += 1
            else:
                self.stats['skipped'] += 1
        else:
            if self.operation_mode in ['create', 'create_update']:
                new_profile = SkillboostProfile(**row_dict)
                session.add(new_profile)
                self.stats['created'] += 1
            else:
                self.stats['skipped'] += 1
    
    def _import_masterclass(self, session, row_dict):
        """
        Import masterclass data with protection logic:
        - Always check by composite primary key (email, master_class_name)
        - If existing.live is TRUE, do NOT overwrite live field
        - If existing.recorded is TRUE, do NOT overwrite recorded field
        - If live is TRUE, recorded cannot also be TRUE (mutual exclusivity)
        - If live or recorded is FALSE or NULL, allow update
        """
        if 'email' not in row_dict or 'master_class_name' not in row_dict:
            self.stats['skipped'] += 1
            return
        
        # Normalize email
        row_dict['email'] = str(row_dict['email']).strip().lower()
        
        # Convert "-" to None for live and recorded fields
        if 'live' in row_dict:
            if isinstance(row_dict['live'], str) and row_dict['live'].strip() in ['-', '', 'null', 'none']:
                row_dict['live'] = None
        
        if 'recorded' in row_dict:
            if isinstance(row_dict['recorded'], str) and row_dict['recorded'].strip() in ['-', '', 'null', 'none']:
                row_dict['recorded'] = None
        
        # Enforce mutual exclusivity: if live is TRUE, recorded cannot be TRUE
        if row_dict.get('live') is True and row_dict.get('recorded') is True:
            row_dict['recorded'] = None  # Reset recorded if live is TRUE
            print(f"[DEBUG IMPORT] Master class for {row_dict['email']}: Both live and recorded are TRUE - setting recorded to NULL")
        
        # Always check by composite primary key (email + master_class_name)
        existing = session.query(MasterClass).filter_by(
            email=row_dict['email'],
            master_class_name=row_dict['master_class_name']
        ).first()
        
        if existing:
            # Protection logic
            protected_live = False
            protected_recorded = False
            
            # Check if live is protected (TRUE)
            if existing.live is True:
                protected_live = True
                print(f"[DEBUG IMPORT] Master class for {row_dict['email']}: Live attendance already verified - protecting live field")
            
            # Check if recorded is protected (TRUE)
            if existing.recorded is True:
                protected_recorded = True
                print(f"[DEBUG IMPORT] Master class for {row_dict['email']}: Recorded viewing already verified - protecting recorded field")
            
            # Update allowed?
            if self.operation_mode in ['update', 'create_update']:
                for key, value in row_dict.items():
                    if hasattr(existing, key):
                        # Skip updating live if it's already TRUE
                        if key == 'live' and protected_live:
                            continue
                        # Skip updating recorded if it's already TRUE
                        if key == 'recorded' and protected_recorded:
                            continue
                        # Apply update
                        setattr(existing, key, value)
                
                existing.updated_at = datetime.utcnow()
                self.stats['updated'] += 1
            else:
                self.stats['skipped'] += 1
        else:
            # Create new record
            if self.operation_mode in ['create', 'create_update']:
                new_mc = MasterClass(**row_dict)
                session.add(new_mc)
                self.stats['created'] += 1
            else:
                self.stats['skipped'] += 1
    
    def get_stats(self):
        """Get import statistics"""
        return self.stats


def get_table_columns(table_name):
    """Get available columns for a table"""
    columns_map = {
        'user_pii': [
            'email', 'name', 'phone_number', 'gender', 'country', 'state', 'city',
            'date_of_birth', 'designation', 'class_stream', 'degree_passout_year',
            'occupation', 'linkedin', 'participated_in_academy_1'
        ],
        'courses': [
            'email', 'problem_statement', 'share_skill_badge_public_link', 'valid', 'remarks'
        ],
        'skillboost_profile': [
            'email', 'google_cloud_skills_boost_profile_link', 'valid', 'remarks'
        ],
        'master_classes': [
            'email', 'master_class_name', 'platform', 'link', 'total_duration',
            'watch_time', 'live', 'recorded', 'watched_duration_updated_at',
            'time_watched', 'valid'
        ]
    }
    return columns_map.get(table_name, [])


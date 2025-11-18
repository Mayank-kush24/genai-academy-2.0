"""
Skillboost Verification Module
Automated verification of badge and profile links with parallel processing
"""
import sys
import os
import time
import random
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db_manager, Course, SkillboostProfile
from sqlalchemy import or_
from config import Config


class SkillboostVerifier:
    """Handles verification of Skillboost badges and profiles"""
    
    def __init__(self, max_workers=10):
        self.session = requests.Session()
        self.user_agents = Config.USER_AGENTS
        self.rate_limit_delay = Config.RATE_LIMIT_DELAY
        self.retry_attempts = Config.VERIFICATION_RETRY_ATTEMPTS
        self.timeout = Config.VERIFICATION_TIMEOUT
        self.max_workers = max_workers
        
        self.stats = {
            'profiles_verified': 0,
            'profiles_failed': 0,
            'badges_verified': 0,
            'badges_failed': 0,
            'badges_pending': 0
        }
        
        # Thread-safe lock for stats updates
        self.stats_lock = Lock()
    
    def get_random_user_agent(self):
        """Get random user agent for request"""
        return random.choice(self.user_agents)
    
    def make_request(self, url, retries=None):
        """Make HTTP request with retry logic"""
        if retries is None:
            retries = self.retry_attempts
        
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        for attempt in range(retries):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 404:
                    return None
                elif response.status_code == 429:  # Rate limited
                    wait_time = (attempt + 1) * self.rate_limit_delay
                    print(f"    Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    if attempt < retries - 1:
                        time.sleep(self.rate_limit_delay)
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    time.sleep(self.rate_limit_delay)
                    continue
                return None
            except Exception as e:
                print(f"    Request error: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(self.rate_limit_delay)
                    continue
                return None
        
        return None
    
    def extract_profile_name(self, profile_url):
        """Extract the name from a Skillboost profile page"""
        response = self.make_request(profile_url)
        
        if response is None:
            return None, "Profile page not accessible"
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Method 1: Look for profile name in common locations
            # Try to find the name in the profile header
            name_element = soup.find('h1', class_='profile-name')
            if name_element:
                return name_element.get_text().strip(), None
            
            # Method 2: Look for name in title tag
            title = soup.find('title')
            if title:
                title_text = title.get_text().strip()
                # Remove "Google Cloud Skills Boost", "Google Skills" and similar suffixes
                name = re.sub(r'\s*[-–|]\s*(Google|Cloud Skills Boost|Skills Boost|Google Skills).*$', '', title_text, flags=re.IGNORECASE)
                if name and len(name) > 2:
                    return name.strip(), None
            
            # Method 3: Look for meta tags with profile name
            meta_title = soup.find('meta', property='og:title')
            if meta_title and meta_title.get('content'):
                name = meta_title['content'].strip()
                # Remove "Google Cloud Skills Boost", "Google Skills" and similar suffixes
                name = re.sub(r'\s*[-–|]\s*(Google|Cloud Skills Boost|Skills Boost|Google Skills).*$', '', name, flags=re.IGNORECASE)
                if name and len(name) > 2:
                    return name.strip(), None
            
            # Method 4: Look for any h1 or h2 that might contain the name
            headers = soup.find_all(['h1', 'h2'])
            for header in headers:
                text = header.get_text().strip()
                if text and len(text) > 2 and len(text) < 100:  # Reasonable name length
                    return text, None
            
            return None, "Could not extract name from profile page"
            
        except Exception as e:
            return None, f"Error parsing profile page: {str(e)}"
    
    def fuzzy_match_names(self, name1, name2):
        """
        Fuzzy match two names to check if they're similar
        Returns (is_match, similarity_score)
        """
        if not name1 or not name2:
            return False, 0.0
        
        # Normalize names
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        # Exact match
        if name1 == name2:
            return True, 1.0
        
        # Split into words and create sets
        words1 = set(re.findall(r'\w+', name1))
        words2 = set(re.findall(r'\w+', name2))
        
        # Remove common short words that don't help matching
        common_words = {'mr', 'ms', 'mrs', 'dr', 'prof', 'sir', 'ma\'am'}
        words1 = words1 - common_words
        words2 = words2 - common_words
        
        if not words1 or not words2:
            return False, 0.0
        
        # Calculate word overlap
        intersection = words1 & words2
        union = words1 | words2
        
        jaccard_similarity = len(intersection) / len(union) if union else 0.0
        
        # Consider it a match if at least 60% of words overlap
        # Or if at least 2 significant words match (for longer names)
        is_match = jaccard_similarity >= 0.6 or (len(intersection) >= 2 and len(words1) >= 2)
        
        return is_match, jaccard_similarity
    
    def verify_profile_url(self, profile_url, expected_name=None):
        """
        Verify Skillboost profile URL - checks if profile is accessible
        Name matching is NOT performed - only URL validity and accessibility
        """
        # Clean the URL
        if not isinstance(profile_url, str) or not profile_url.strip():
            return False, "Empty or Invalid URL"
        
        profile_url = profile_url.strip()
        
        # Parse the URL
        try:
            parsed_url = urlparse(profile_url)
        except Exception as e:
            return False, f"URL parsing error: {str(e)}"
        
        # Check domain - must be www.cloudskillsboost.google or www.skills.google
        valid_domains = ["www.cloudskillsboost.google", "www.skills.google"]
        if parsed_url.netloc not in valid_domains:
            return False, f"Incorrect Domain (must be {' or '.join(valid_domains)})"
        
        # Check path - must start with /public_profiles/
        if not parsed_url.path.startswith("/public_profiles/"):
            return False, "Incorrect Path (must start with /public_profiles/)"
        
        # Make request to check if profile exists
        response = self.make_request(profile_url)
        
        if response is None:
            return False, "Profile not found or inaccessible"
        
        # Check basic validity - if profile opens and is accessible, it's valid
        if response.status_code == 200 and "public_profiles" in response.url:
            return True, "Valid Profile"
        else:
            return False, f"Invalid Profile (Status Code: {response.status_code})"
    
    def extract_completion_date(self, badge_url):
        """Extract completion date from badge page (supports both Google Skills Boost and Credly)"""
        response = self.make_request(badge_url)
        
        if response is None:
            return None, "Badge page not accessible"
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            parsed_url = urlparse(badge_url)
            
            # Check if it's a Credly badge
            if 'credly.com' in parsed_url.netloc:
                # Credly-specific date extraction
                # Look for date in various formats, including "Date issued:" prefix
                date_patterns = [
                    r'Date issued:\s*(\w+ \d{1,2}, \d{4})',  # "Date issued: August 31, 2025"
                    r'(\w+ \d{1,2}, \d{4})',  # "Nov 14, 2025" or "August 31, 2025"
                    r'(\d{1,2}/\d{1,2}/\d{4})',  # "11/14/2025"
                    r'(\d{4}-\d{2}-\d{2})',  # "2025-11-14"
                ]
                
                # Search in text content
                page_text = soup.get_text()
                for pattern in date_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        date_str = match.group(1).strip()
                        try:
                            # Try parsing different date formats
                            if ',' in date_str:
                                # Try full month name first (e.g., "August 31, 2025")
                                try:
                                    date_obj = datetime.strptime(date_str, '%B %d, %Y').date()
                                except ValueError:
                                    # Try abbreviated month (e.g., "Aug 31, 2025")
                                    try:
                                        date_obj = datetime.strptime(date_str, '%b %d, %Y').date()
                                    except ValueError:
                                        continue
                            elif '/' in date_str:
                                # Format: "11/14/2025"
                                date_obj = datetime.strptime(date_str, '%m/%d/%Y').date()
                            else:
                                # Format: "2025-11-14"
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                            return date_obj, None
                        except ValueError:
                            continue
                
                # Look for date in meta tags or structured data
                meta_date = soup.find('meta', property='article:published_time')
                if meta_date and meta_date.get('content'):
                    try:
                        date_obj = datetime.fromisoformat(meta_date['content'].replace('Z', '+00:00')).date()
                        return date_obj, None
                    except (ValueError, AttributeError):
                        pass
            
            else:
                # Google Cloud Skills Boost date extraction
                # Look for date patterns in the page, including formats like "Aug 30, 2025"
                date_patterns = [
                    r'(\w+ \d{1,2}, \d{4})',  # "Nov 14, 2025" or "August 31, 2025" or "Aug 30, 2025"
                    r'(\d{1,2}/\d{1,2}/\d{4})',  # "11/14/2025"
                    r'(\d{4}-\d{2}-\d{2})',  # "2025-11-14"
                ]
                
                # Search in text content
                page_text = soup.get_text()
                for pattern in date_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        date_str = match.group(1).strip()
                        try:
                            # Try parsing different date formats
                            if ',' in date_str:
                                # Try full month name first (e.g., "August 31, 2025")
                                try:
                                    date_obj = datetime.strptime(date_str, '%B %d, %Y').date()
                                except ValueError:
                                    # Try abbreviated month (e.g., "Aug 31, 2025")
                                    try:
                                        date_obj = datetime.strptime(date_str, '%b %d, %Y').date()
                                    except ValueError:
                                        continue
                            elif '/' in date_str:
                                # Format: "11/14/2025"
                                date_obj = datetime.strptime(date_str, '%m/%d/%Y').date()
                            else:
                                # Format: "2025-11-14"
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                            return date_obj, None
                        except ValueError:
                            continue
                
                # Look for date in time elements or structured data
                time_elem = soup.find('time')
                if time_elem and time_elem.get('datetime'):
                    try:
                        date_obj = datetime.fromisoformat(time_elem['datetime'].replace('Z', '+00:00')).date()
                        return date_obj, None
                    except (ValueError, AttributeError):
                        pass
            
            return None, "Could not extract completion date from badge page"
            
        except Exception as e:
            return None, f"Error parsing badge page for date: {str(e)}"
    
    def extract_course_from_badge(self, badge_url):
        """Extract course name from badge page (supports both Google Skills Boost and Credly)"""
        response = self.make_request(badge_url)
        
        if response is None:
            return None, "Badge page not accessible"
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            parsed_url = urlparse(badge_url)
            
            # Check if it's a Credly badge
            if 'credly.com' in parsed_url.netloc:
                # Credly-specific extraction methods
                
                # Method 1: Look for badge name/title (most common)
                badge_name = soup.find('h1', class_='badge-name')
                if badge_name:
                    return badge_name.get_text().strip(), None
                
                # Method 2: Look for data-name attribute
                badge_container = soup.find('div', {'data-name': True})
                if badge_container:
                    return badge_container['data-name'].strip(), None
                
                # Method 3: Meta tags (og:title)
                meta_title = soup.find('meta', property='og:title')
                if meta_title and meta_title.get('content'):
                    title_text = meta_title['content'].strip()
                    # Remove "Credly" suffix if present
                    course_name = re.sub(r'\s*[-–|]\s*Credly.*$', '', title_text, flags=re.IGNORECASE)
                    if course_name:
                        return course_name.strip(), None
                
                # Method 4: Page title
                title = soup.find('title')
                if title:
                    title_text = title.get_text().strip()
                    # Remove "Credly" and similar suffixes
                    course_name = re.sub(r'\s*[-–|]\s*Credly.*$', '', title_text, flags=re.IGNORECASE)
                    if course_name:
                        return course_name.strip(), None
                
                # Method 5: Look for any h1 tag
                h1_tag = soup.find('h1')
                if h1_tag:
                    return h1_tag.get_text().strip(), None
            
            else:
                # Google Cloud Skills Boost extraction methods
                
                # Method 1: Look for badge title
                badge_title = soup.find('h1', class_='badge-title')
                if badge_title:
                    return badge_title.get_text().strip(), None
                
                # Method 2: Look for page title
                title = soup.find('title')
                if title:
                    title_text = title.get_text().strip()
                    # Remove "Google Cloud Skills Boost", "Google Skills" and similar suffixes
                    course_name = re.sub(r'\s*[-–|]\s*(Google|Cloud Skills Boost|Skills Boost|Google Skills).*$', '', title_text, flags=re.IGNORECASE)
                    if course_name:
                        return course_name.strip(), None
                
                # Method 3: Look for meta tags
                meta_title = soup.find('meta', property='og:title')
                if meta_title and meta_title.get('content'):
                    return meta_title['content'].strip(), None
                
                # Method 4: Look for any h1 or h2 headers
                headers = soup.find_all(['h1', 'h2'])
                for header in headers:
                    text = header.get_text().strip()
                    if text and len(text) > 10:  # Reasonable course name length
                        return text, None
            
            return None, "Could not extract course name from badge page"
            
        except Exception as e:
            return None, f"Error parsing badge page: {str(e)}"
    
    def verify_badge_url(self, badge_url, expected_course):
        """Verify badge URL and match with expected course (supports Google Skills Boost and Credly)
        Also checks completion date >= 2025-10-27"""
        # Clean the URL
        if not isinstance(badge_url, str) or not badge_url.strip():
            return False, "Empty or Invalid URL", None
        
        badge_url = badge_url.strip()
        
        # Parse the URL
        try:
            parsed_url = urlparse(badge_url)
        except Exception as e:
            return False, f"URL parsing error: {str(e)}", None
        
        # Check domain - must be either www.cloudskillsboost.google, www.skills.google, or www.credly.com
        valid_google_domains = ["www.cloudskillsboost.google", "www.skills.google"]
        is_google_badge = parsed_url.netloc in valid_google_domains
        is_credly_badge = parsed_url.netloc == "www.credly.com"
        
        if not (is_google_badge or is_credly_badge):
            return False, f"Incorrect Domain (must be {', '.join(valid_google_domains)} or www.credly.com)", None
        
        # Validate path based on domain
        if is_google_badge:
            # Check path - must match /public_profiles/{id}/badges/{badge_id}
            if not re.match(r'^/public_profiles/[a-zA-Z0-9\-]+/badges/\d+', parsed_url.path):
                return False, "Incorrect Path (must be /public_profiles/{id}/badges/{badge_id})", None
        
        elif is_credly_badge:
            # Check path - must match /badges/{badge_id}
            if not re.match(r'^/badges/[a-zA-Z0-9\-]+', parsed_url.path):
                return False, "Incorrect Path (must be /badges/{badge_id})", None
        
        # Extract course name from badge page
        course_name, error = self.extract_course_from_badge(badge_url)
        
        if error:
            return None, error, None  # None means pending/retry later
        
        if not course_name:
            return None, "Could not extract course information", None
        
        # Extract completion date
        completion_date, date_error = self.extract_completion_date(badge_url)
        
        # Minimum required date: October 27, 2025
        MIN_REQUIRED_DATE = datetime(2025, 10, 27).date()
        
        # Check date requirement
        if completion_date is None:
            # If we can't extract date, we'll still verify the course but mark date as missing
            # The date check will be done separately in the verification logic
            # Note: This allows verification to proceed, but the badge will need to be re-verified
            # once the date is extracted to determine final validity
            pass
        elif completion_date < MIN_REQUIRED_DATE:
            # Date is before required date - mark as invalid immediately
            return False, f"Badge completion date ({completion_date}) is before required date (2025-10-27)", completion_date
        
        # Determine badge platform for better reporting
        platform = "Credly" if is_credly_badge else "Google Skills Boost"
        
        # Fuzzy match with expected course
        # Normalize both strings for comparison
        course_normalized = course_name.lower().strip()
        expected_normalized = expected_course.lower().strip()
        
        # Direct match
        if course_normalized == expected_normalized:
            return True, f"Course verified ({platform} - exact match)", completion_date
        
        # Contains match
        if expected_normalized in course_normalized or course_normalized in expected_normalized:
            return True, f"Course verified ({platform} - matched: {course_name})", completion_date
        
        # Partial word match (at least 60% of words match)
        course_words = set(course_normalized.split())
        expected_words = set(expected_normalized.split())
        
        if len(expected_words) > 0:
            match_ratio = len(course_words & expected_words) / len(expected_words)
            if match_ratio >= 0.6:
                return True, f"Course verified ({platform} - partial match: {course_name})", completion_date
        
        return False, f"Course mismatch ({platform}). Expected: '{expected_course}', Found: '{course_name}'", completion_date
    
    def verify_single_profile(self, profile_data):
        """Verify a single profile (worker function for parallel processing)"""
        email = profile_data['email']
        profile_link = profile_data['profile_link']
        user_name = profile_data.get('user_name')
        
        try:
            # Small random delay to distribute load
            time.sleep(random.uniform(0.1, 0.5))
            
            if not profile_link or profile_link.strip() == '':
                return {
                    'email': email,
                    'valid': False,
                    'remarks': 'No profile link provided'
                }
            
            # Verify profile with name matching
            valid, remarks = self.verify_profile_url(profile_link, user_name)
            
            return {
                'email': email,
                'valid': valid,
                'remarks': remarks
            }
        except Exception as e:
            return {
                'email': email,
                'valid': False,
                'remarks': f'Verification error: {str(e)}'
            }
    
    def verify_profiles(self, limit=None):
        """Verify all unverified Skillboost profiles using parallel processing"""
        db_session = db_manager.get_session()
        
        try:
            # Get profiles that need verification (valid is NULL)
            query = db_session.query(SkillboostProfile).filter(
                SkillboostProfile.valid.is_(None)
            )
            
            if limit:
                query = query.limit(limit)
            
            profiles = query.all()
            
            print(f"\nVerifying {len(profiles)} Skillboost profiles using {self.max_workers} parallel workers...")
            print(f"Estimated time: ~{len(profiles) // self.max_workers // 60} minutes")
            print(f"Note: Verification checks URL validity and accessibility only (no name matching)")
            
            # Prepare profile data for parallel processing
            profile_data_list = []
            for profile in profiles:
                profile_data_list.append({
                    'email': profile.email,
                    'profile_link': profile.google_cloud_skills_boost_profile_link,
                    'user_name': None  # Not used anymore
                })
            
            # Process profiles in parallel
            completed = 0
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_profile = {
                    executor.submit(self.verify_single_profile, profile_data): profile_data 
                    for profile_data in profile_data_list
                }
                
                # Process completed tasks
                for future in as_completed(future_to_profile):
                    completed += 1
                    result = future.result()
                    
                    # Update database
                    profile = db_session.query(SkillboostProfile).filter_by(
                        email=result['email']
                    ).first()
                    
                    if profile:
                        profile.valid = result['valid']
                        profile.remarks = result['remarks']
                        profile.updated_at = datetime.utcnow()
                        
                        with self.stats_lock:
                            if result['valid']:
                                self.stats['profiles_verified'] += 1
                                status = '✓'
                            else:
                                self.stats['profiles_failed'] += 1
                                status = f"✗ ({result['remarks'][:30]}...)"
                        
                        # Print progress
                        if completed % 10 == 0:
                            print(f"  Progress: {completed}/{len(profiles)} | Verified: {self.stats['profiles_verified']} | Failed: {self.stats['profiles_failed']}")
                        
                        # Commit every 50 records
                        if completed % 50 == 0:
                            db_session.commit()
            
            # Final commit
            db_session.commit()
            print(f"\n  Completed: {completed}/{len(profiles)}")
            
        except Exception as e:
            print(f"\nError during profile verification: {e}")
            db_session.rollback()
        finally:
            db_manager.close_session(db_session)
    
    def verify_single_badge(self, badge_data):
        """Verify a single badge (worker function for parallel processing)"""
        email = badge_data['email']
        problem_statement = badge_data['problem_statement']
        badge_link = badge_data['badge_link']
        
        try:
            # Small random delay to distribute load
            time.sleep(random.uniform(0.1, 0.5))
            
            if not badge_link or badge_link.strip() == '':
                return {
                    'email': email,
                    'problem_statement': problem_statement,
                    'valid': False,
                    'remarks': 'No badge link provided',
                    'completion_date': None
                }
            
            valid, remarks, completion_date = self.verify_badge_url(badge_link, problem_statement)
            
            # Additional date check if date was extracted but verification passed
            MIN_REQUIRED_DATE = datetime(2025, 10, 27).date()
            if valid is True and completion_date and completion_date < MIN_REQUIRED_DATE:
                valid = False
                remarks = f"Badge completion date ({completion_date}) is before required date (2025-10-27)"
            
            return {
                'email': email,
                'problem_statement': problem_statement,
                'valid': valid,
                'remarks': remarks,
                'completion_date': completion_date
            }
        except Exception as e:
            return {
                'email': email,
                'problem_statement': problem_statement,
                'valid': None,
                'remarks': f'Verification error: {str(e)}',
                'completion_date': None
            }
    
    def verify_badges(self, limit=None, force_reverify=False):
        """Verify all unverified course badges using parallel processing
        
        Args:
            limit: Maximum number of badges to verify
            force_reverify: If True, also reverify badges that are already verified but missing completion_date
        """
        db_session = db_manager.get_session()
        
        try:
            # Get badges that need verification
            if force_reverify:
                # Include badges that are verified but missing completion_date (need date extraction)
                query = db_session.query(Course).filter(
                    Course.share_skill_badge_public_link.isnot(None),
                    Course.completion_date.is_(None)  # Missing completion date
                )
            else:
                # Only get badges that are unverified (valid is NULL)
                query = db_session.query(Course).filter(
                    Course.valid.is_(None),
                    Course.share_skill_badge_public_link.isnot(None)
                )
            
            if limit:
                query = query.limit(limit)
            
            badges = query.all()
            
            print(f"\nVerifying {len(badges)} course badges using {self.max_workers} parallel workers...")
            print(f"Estimated time: ~{len(badges) // self.max_workers // 60} minutes")
            
            # Prepare badge data for parallel processing
            badge_data_list = []
            for badge in badges:
                badge_data_list.append({
                    'email': badge.email,
                    'problem_statement': badge.problem_statement,
                    'badge_link': badge.share_skill_badge_public_link
                })
            
            # Process badges in parallel
            completed = 0
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_badge = {
                    executor.submit(self.verify_single_badge, badge_data): badge_data 
                    for badge_data in badge_data_list
                }
                
                # Process completed tasks
                for future in as_completed(future_to_badge):
                    completed += 1
                    result = future.result()
                    
                    # Update database
                    badge = db_session.query(Course).filter_by(
                        email=result['email'],
                        problem_statement=result['problem_statement']
                    ).first()
                    
                    if badge:
                        # Always update completion_date if extracted
                        if result.get('completion_date'):
                            badge.completion_date = result['completion_date']
                        
                        if result['valid'] is not None:
                            # Check date requirement even if verification passed
                            MIN_REQUIRED_DATE = datetime(2025, 10, 27).date()
                            
                            # If we have a completion date, check if it's before the required date
                            if badge.completion_date and badge.completion_date < MIN_REQUIRED_DATE:
                                # Date is before required date - mark as invalid regardless of course match
                                badge.valid = False
                                badge.remarks = f"Badge completion date ({badge.completion_date}) is before required date (2025-10-27)"
                                with self.stats_lock:
                                    self.stats['badges_failed'] += 1
                                    status = f"✗ (Date {badge.completion_date} < 2025-10-27)"
                            elif result['valid'] is True:
                                # Course matches and date is valid (or no date extracted yet)
                                badge.valid = True
                                badge.remarks = result['remarks']
                                with self.stats_lock:
                                    self.stats['badges_verified'] += 1
                                    status = '✓'
                            else:
                                # Course doesn't match
                                badge.valid = False
                                badge.remarks = result['remarks']
                                with self.stats_lock:
                                    self.stats['badges_failed'] += 1
                                    status = f"✗ ({result['remarks'][:30]}...)"
                            badge.updated_at = datetime.utcnow()
                        else:
                            badge.remarks = result['remarks']
                            with self.stats_lock:
                                self.stats['badges_pending'] += 1
                            status = f"⚠ ({result['remarks'][:30]}...)"
                        
                        # Print progress
                        if completed % 10 == 0:
                            print(f"  Progress: {completed}/{len(badges)} | Verified: {self.stats['badges_verified']} | Failed: {self.stats['badges_failed']} | Pending: {self.stats['badges_pending']}")
                        
                        # Commit every 50 records
                        if completed % 50 == 0:
                            db_session.commit()
            
            # Final commit
            db_session.commit()
            print(f"\n  Completed: {completed}/{len(badges)}")
            
        except Exception as e:
            print(f"\nError during badge verification: {e}")
            db_session.rollback()
        finally:
            db_manager.close_session(db_session)
    
    def print_summary(self):
        """Print verification summary"""
        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)
        print(f"Profiles Verified:     {self.stats['profiles_verified']}")
        print(f"Profiles Failed:       {self.stats['profiles_failed']}")
        print(f"Badges Verified:       {self.stats['badges_verified']}")
        print(f"Badges Failed:         {self.stats['badges_failed']}")
        print(f"Badges Pending:        {self.stats['badges_pending']}")
        print("="*60)


def run_verification(profiles=True, badges=True, limit=None, max_workers=10, force_reverify=False):
    """Main verification function
    
    Args:
        profiles: Verify profiles
        badges: Verify badges
        limit: Limit number of records
        max_workers: Number of parallel workers
        force_reverify: If True, reverify badges missing completion_date even if already verified
    """
    verifier = SkillboostVerifier(max_workers=max_workers)
    
    if profiles:
        verifier.verify_profiles(limit=limit)
    
    if badges:
        verifier.verify_badges(limit=limit, force_reverify=force_reverify)
    
    verifier.print_summary()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify Skillboost badges and profiles with parallel processing')
    parser.add_argument('--profiles-only', action='store_true', help='Verify only profiles')
    parser.add_argument('--badges-only', action='store_true', help='Verify only badges')
    parser.add_argument('--limit', type=int, help='Limit number of records to verify')
    parser.add_argument('--workers', type=int, default=10, help='Number of parallel workers (default: 10, recommended: 5-20)')
    parser.add_argument('--force-reverify', action='store_true', help='Reverify badges missing completion_date even if already verified')
    
    args = parser.parse_args()
    
    # Initialize database connection
    if not db_manager.initialize():
        print("✗ Failed to connect to database. Check your configuration.")
        sys.exit(1)
    
    print("✓ Database connection established")
    print("="*60)
    print("Starting Skillboost Verification with Parallel Processing")
    print(f"Workers: {args.workers}")
    if args.force_reverify:
        print("Mode: Force re-verification (will extract dates from already-verified badges)")
    print("="*60)
    
    profiles = not args.badges_only
    badges = not args.profiles_only
    
    run_verification(profiles=profiles, badges=badges, limit=args.limit, max_workers=args.workers, force_reverify=args.force_reverify)


if __name__ == '__main__':
    main()


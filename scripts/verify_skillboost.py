"""
Skillboost Verification Module
Automated verification of badge and profile links with parallel processing
"""
import sys
import os
import time
import random
import re
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import threading
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Optional Selenium imports for Credly badge verification
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium not available. Credly badge date extraction will use fallback method.")

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
        
        # Selenium WebDriver management (for Credly badges)
        self.driver_lock = Lock()
        self.selenium_drivers = {}
    
    def get_random_user_agent(self):
        """Get random user agent for request"""
        return random.choice(self.user_agents)
    
    def get_selenium_driver(self):
        """Get or create a Selenium WebDriver instance for the current thread (for Credly badges)"""
        if not SELENIUM_AVAILABLE:
            return None
        
        thread_id = threading.get_ident()
        with self.driver_lock:
            if thread_id not in self.selenium_drivers:
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-infobars")
                options.add_argument("--disable-notifications")
                options.add_argument("--blink-settings=imagesEnabled=false")
                options.add_argument("--disable-features=NetworkService")
                options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
                options.add_argument("--disable-background-networking")
                options.add_argument("--disable-sync")
                options.add_argument("--disable-translate")
                
                try:
                    # Try to get ChromeDriver path with validation
                    driver_path = None
                    try:
                        driver_path = ChromeDriverManager().install()
                        # Verify the driver file exists and is valid
                        if os.path.exists(driver_path):
                            file_size = os.path.getsize(driver_path)
                            if file_size < 1000:  # Too small, likely corrupted
                                # Try to clear cache and re-download
                                cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
                                if os.path.exists(cache_path):
                                    try:
                                        import shutil
                                        shutil.rmtree(cache_path)
                                        driver_path = ChromeDriverManager().install()
                                    except Exception:
                                        pass  # Continue with original path
                    except Exception:
                        # ChromeDriverManager failed, will try system ChromeDriver
                        driver_path = None
                    
                    # Initialize driver with explicit path or fallback to system
                    if driver_path:
                        driver = webdriver.Chrome(service=Service(driver_path), options=options)
                    else:
                        # Fallback to system ChromeDriver
                        driver = webdriver.Chrome(options=options)
                    
                    driver.set_page_load_timeout(30)
                    driver.set_script_timeout(30)
                    self.selenium_drivers[thread_id] = driver
                except WebDriverException as e:
                    error_msg = str(e)
                    # If ChromeDriverManager failed with WinError 193, try system ChromeDriver
                    if "WinError 193" in error_msg or "not a valid Win32 application" in error_msg:
                        try:
                            # Try without explicit service (use system ChromeDriver)
                            driver = webdriver.Chrome(options=options)
                            driver.set_page_load_timeout(30)
                            driver.set_script_timeout(30)
                            self.selenium_drivers[thread_id] = driver
                        except Exception as e2:
                            print(f"Warning: Failed to initialize Selenium WebDriver (both methods failed): {str(e2)[:200]}")
                            return None
                    else:
                        print(f"Warning: Failed to initialize Selenium WebDriver: {error_msg[:200]}")
                        return None
                except Exception as e:
                    print(f"Warning: Unexpected error initializing Selenium WebDriver: {str(e)[:200]}")
                    return None
        return self.selenium_drivers.get(thread_id)
    
    def close_selenium_drivers(self):
        """Close all Selenium WebDrivers"""
        with self.driver_lock:
            for thread_id, driver in list(self.selenium_drivers.items()):
                try:
                    driver.quit()
                except Exception as e:
                    print(f"Warning: Error closing WebDriver: {str(e)}")
                finally:
                    self.selenium_drivers.pop(thread_id, None)
            self.selenium_drivers.clear()
    
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
    
    def parse_date_string(self, date_str):
        """
        Parse a date string in various formats and return a date object.
        Tries multiple date formats to handle different representations.
        Returns (date_object, None) on success, (None, error_message) on failure.
        """
        if not date_str or not isinstance(date_str, str):
            return None, "Invalid date string"
        
        date_str = date_str.strip()
        
        # List of date formats to try (in order of likelihood)
        date_formats = [
            # Full month name with comma: "August 31, 2025", "October 27, 2025"
            '%B %d, %Y',  # Full month name
            '%b %d, %Y',  # Abbreviated month name: "Aug 31, 2025", "Oct 27, 2025"
            
            # Full month name without comma: "27 October 2025", "31 August 2025"
            '%d %B %Y',  # Day month year (full month)
            '%d %b %Y',  # Day month year (abbreviated): "27 Oct 2025"
            
            # ISO format: "2025-10-27"
            '%Y-%m-%d',
            
            # Dash-separated formats: "27-10-2025" (DD-MM-YYYY) or "10-27-2025" (MM-DD-YYYY)
            '%d-%m-%Y',  # DD-MM-YYYY: "27-10-2025"
            '%m-%d-%Y',  # MM-DD-YYYY: "10-27-2025"
            
            # Slash-separated formats: "27/10/2025" (DD/MM/YYYY) or "10/27/2025" (MM/DD/YYYY)
            '%d/%m/%Y',  # DD/MM/YYYY: "27/10/2025"
            '%m/%d/%Y',  # MM/DD/YYYY: "10/27/2025"
            
            # Year first with slashes: "2025/10/27"
            '%Y/%m/%d',
            
            # Text formats with "of": "27th of October 2025", "27 of October 2025"
            '%d of %B %Y',
            '%dth of %B %Y',
            '%dst of %B %Y',
            '%dnd of %B %Y',
            '%drd of %B %Y',
        ]
        
        # Try each format
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt).date()
                return date_obj, None
            except ValueError:
                continue
        
        return None, f"Could not parse date string: {date_str}"
    
    def extract_credly_date_selenium(self, badge_url, retries=2):
        """Extract completion date from Credly badge using Selenium (exact match from reference file)"""
        if not SELENIUM_AVAILABLE:
            return None, "Selenium not available for Credly date extraction"
        
        for attempt in range(retries + 1):
            try:
                driver = self.get_selenium_driver()
                if driver is None:
                    return None, "Failed to initialize Selenium WebDriver"
                
                driver.get(badge_url)
                
                wait = WebDriverWait(driver, 20)  # Increased timeout
                # Wait for badge element to ensure page is fully loaded (like reference file)
                try:
                    badge_element = wait.until(EC.presence_of_element_located(
                        (By.XPATH, '//h1[contains(@class, "ac-heading--badge-name-hero")]')
                    ))
                    # Wait a bit more for dynamic content to load
                    time.sleep(1)
                    # Scroll to badge element to ensure it's in view
                    driver.execute_script("arguments[0].scrollIntoView(true);", badge_element)
                    time.sleep(0.5)
                except TimeoutException:
                    # If badge name element not found, try waiting for body and add delay
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    # Wait for page to be ready
                    driver.execute_script("return document.readyState") == "complete"
                    time.sleep(3)  # Give JavaScript more time to render
                
                issue_date = ""
                
                # Method 1: Exact match from reference file
                # XPath: '//div[contains(@class, "badge-banner-issued-to-text")]/p[contains(text(), "Date issued:")]'
                try:
                    date_element = wait.until(EC.presence_of_element_located(
                        (By.XPATH, '//div[contains(@class, "badge-banner-issued-to-text")]/p[contains(text(), "Date issued:")]')
                    ))
                    if date_element:
                        # Scroll to element to ensure it's visible
                        driver.execute_script("arguments[0].scrollIntoView(true);", date_element)
                        time.sleep(0.3)
                        issue_date = date_element.text.replace("Date issued:", "").strip()
                        print(f"    [DEBUG CREDLY SELENIUM] Method 1 found date: {issue_date}")
                except (NoSuchElementException, TimeoutException) as e:
                    print(f"    [DEBUG CREDLY SELENIUM] Method 1 failed: {str(e)[:100]}")
                
                # Method 1b: Try alternative XPath with different class variations
                if not issue_date:
                    try:
                        # Try with different class name variations
                        xpaths = [
                            '//p[contains(text(), "Date issued:")]',
                            '//div[contains(@class, "badge")]//p[contains(text(), "Date issued:")]',
                            '//div[contains(@class, "issued")]//p[contains(text(), "Date issued:")]',
                            '//*[contains(text(), "Date issued:")]'
                        ]
                        for xpath in xpaths:
                            try:
                                date_element = driver.find_element(By.XPATH, xpath)
                                if date_element:
                                    issue_date = date_element.text.replace("Date issued:", "").strip()
                                    if issue_date:
                                        print(f"    [DEBUG CREDLY SELENIUM] Method 1b (xpath: {xpath[:50]}) found date: {issue_date}")
                                        break
                            except NoSuchElementException:
                                continue
                    except Exception as e:
                        print(f"    [DEBUG CREDLY SELENIUM] Method 1b failed: {str(e)[:100]}")
                
                # Method 2: Following sibling approach (from reference file)
                if not issue_date:
                    try:
                        issue_date_element = driver.find_element(By.XPATH, '//div[text()="Date issued:"]/following-sibling::div[1]')
                        issue_date = issue_date_element.text.strip()
                        print(f"    [DEBUG CREDLY SELENIUM] Method 2 found date: {issue_date}")
                    except NoSuchElementException:
                        print(f"    [DEBUG CREDLY SELENIUM] Method 2 failed")
                
                # Method 3: Regex on page_source (exact match from reference file)
                if not issue_date:
                    page_source = driver.page_source
                    # Debug: Check if "Date issued" text exists in page source
                    if "Date issued" in page_source:
                        print(f"    [DEBUG CREDLY SELENIUM] 'Date issued' found in page source, trying regex patterns")
                        # Try to find a sample of HTML around "Date issued"
                        sample_match = re.search(r'.{0,200}Date issued.{0,200}', page_source)
                        if sample_match:
                            print(f"    [DEBUG CREDLY SELENIUM] Sample HTML: {sample_match.group()[:200]}")
                    else:
                        print(f"    [DEBUG CREDLY SELENIUM] 'Date issued' NOT found in page source")
                        # Try to find what date-related text IS in the page
                        date_related = re.search(r'.{0,300}(date|issued|completed).{0,300}', page_source, re.IGNORECASE)
                        if date_related:
                            print(f"    [DEBUG CREDLY SELENIUM] Found date-related text: {date_related.group()[:300]}")
                    
                    date_patterns = [
                        r"Date issued:\s*(\w+ \d{1,2}, \d{4})",
                        r"Date issued:\s*(\d{1,2}/\d{1,2}/\d{4})",
                        r"Date issued:\s*(\d{4}-\d{2}-\d{2})"
                    ]
                    for pattern in date_patterns:
                        matches = re.findall(pattern, page_source)
                        if matches:
                            issue_date = matches[0]
                            print(f"    [DEBUG CREDLY SELENIUM] Method 3 (regex) found date: {issue_date}")
                            break
                
                if issue_date:
                    # Parse the date string
                    date_obj, error = self.parse_date_string(issue_date)
                    if date_obj:
                        print(f"    [DEBUG CREDLY SELENIUM] Successfully parsed date: {date_obj}")
                        return date_obj, None
                    else:
                        print(f"    [DEBUG CREDLY SELENIUM] Failed to parse date string: {issue_date}, error: {error}")
                        return None, f"Could not parse extracted date: {issue_date}"
                else:
                    print(f"    [DEBUG CREDLY SELENIUM] All methods failed for {badge_url[:60]}...")
                    return None, "Could not extract date from Credly badge page"
                    
            except (TimeoutException, WebDriverException) as e:
                print(f"    [DEBUG CREDLY SELENIUM] Attempt {attempt + 1} failed: {str(e)[:100]}")
                if attempt < retries:
                    time.sleep(random.uniform(1, 3))  # Delay before retry
                    continue
                else:
                    return None, f"Selenium error after {retries + 1} attempts: {str(e)}"
            except Exception as e:
                print(f"    [DEBUG CREDLY SELENIUM] Unexpected error: {str(e)[:100]}")
                return None, f"Unexpected error in Selenium extraction: {str(e)}"
        
        return None, "Failed to extract date after all retries"
    
    def extract_completion_date(self, badge_url):
        """Extract completion date from badge page (supports both Google Skills Boost and Credly)
        Uses Selenium for Credly badges (like reference file), requests for Google Skills Boost"""
        parsed_url = urlparse(badge_url)
        is_credly = 'credly.com' in parsed_url.netloc
        
        # For Credly badges, use Selenium (exact match from reference file)
        if is_credly:
            if SELENIUM_AVAILABLE:
                date_obj, error = self.extract_credly_date_selenium(badge_url)
                if date_obj:
                    return date_obj, None
                # If Selenium fails, fall back to requests method below
                # (error will be logged but we'll try requests as backup)
            # If Selenium not available or failed, continue to requests method below
        
        # For Google Skills Boost (or Credly fallback), use requests method
        response = self.make_request(badge_url)
        
        if response is None:
            return None, "Badge page not accessible"
        
        try:
            # Ensure proper encoding (like reference file's driver.page_source)
            response.encoding = response.apparent_encoding if response.apparent_encoding else 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get page text and raw HTML for searching (like reference file uses page_source)
            page_text = soup.get_text()
            page_html = response.text  # Use raw response text (like reference file's page_source)
            
            # CREDLY FALLBACK EXTRACTION (only if Selenium failed or unavailable)
            # This is a fallback - Selenium should be used first for Credly badges
            if is_credly:
                # Only use requests method if Selenium wasn't available or failed
                # Try the same extraction methods as fallback
                # Method 1: Try to find the p element with XPath equivalent (like reference file)
                # Reference uses: '//div[contains(@class, "badge-banner-issued-to-text")]/p[contains(text(), "Date issued:")]'
                # In BeautifulSoup, this translates to finding div with class, then p with text
                badge_banner_divs = soup.find_all('div', class_=re.compile(r'badge-banner-issued-to-text', re.I))
                for banner_div in badge_banner_divs:
                    p_elements = banner_div.find_all('p')
                    for p_elem in p_elements:
                        # Get text without stripping first (to match reference behavior)
                        p_text = p_elem.get_text()
                        # Also try with string attribute (exact text content)
                        p_string = p_elem.string if p_elem.string else p_text
                        
                        # Check if p element contains "Date issued:" (like reference: contains(text(), "Date issued:"))
                        # Try both the full text and the string attribute
                        for text_to_check in [p_text, p_string]:
                            if text_to_check and 'Date issued:' in text_to_check:
                                # Extract date exactly like reference: text.replace("Date issued:", "").strip()
                                issue_date = text_to_check.replace("Date issued:", "").strip()
                                if issue_date:
                                    date_obj, error = self.parse_date_string(issue_date)
                                    if date_obj:
                                        return date_obj, None
                
                # Method 2: Try following sibling approach (like reference file)
                # Reference uses: '//div[text()="Date issued:"]/following-sibling::div[1]'
                date_issued_divs = soup.find_all('div', string=re.compile(r'Date issued:', re.I))
                for div in date_issued_divs:
                    next_sibling = div.find_next_sibling()
                    if next_sibling:
                        issue_date = next_sibling.get_text().strip()
                        if issue_date:
                            date_obj, error = self.parse_date_string(issue_date)
                            if date_obj:
                                return date_obj, None
                
                # Method 3: Use regex on page_source (exact match from reference file)
                # Reference uses: driver.page_source with these exact patterns
                date_patterns = [
                    r"Date issued:\s*(\w+ \d{1,2}, \d{4})",  # Exact pattern from reference: "Date issued: September 17, 2024"
                    r"Date issued:\s*(\d{1,2}/\d{1,2}/\d{4})",  # Exact pattern from reference
                    r"Date issued:\s*(\d{4}-\d{2}-\d{2})"  # Exact pattern from reference
                ]
                
                # Decode HTML entities in page_html (in case of &nbsp; or other entities)
                try:
                    from html import unescape
                    page_html_decoded = unescape(page_html)
                except:
                    page_html_decoded = page_html
                
                # Use page_html (equivalent to driver.page_source) - try both original and decoded
                for html_content in [page_html, page_html_decoded]:
                    for pattern in date_patterns:
                        matches = re.findall(pattern, html_content)  # No flags, exactly like reference
                        if matches:
                            issue_date = matches[0]  # Take first match, exactly like reference
                            date_obj, error = self.parse_date_string(issue_date)
                            if date_obj:
                                return date_obj, None
                
                # Also try on page_text as fallback
                for pattern in date_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        issue_date = matches[0]
                        date_obj, error = self.parse_date_string(issue_date)
                        if date_obj:
                            return date_obj, None
                
                
                # Method 4: Look for date in meta tags or structured data (Credly)
                meta_date = soup.find('meta', property='article:published_time')
                if meta_date and meta_date.get('content'):
                    try:
                        date_obj = datetime.fromisoformat(meta_date['content'].replace('Z', '+00:00')).date()
                        return date_obj, None
                    except (ValueError, AttributeError):
                        pass
                
                # Look for date in data attributes
                date_elem = soup.find(attrs={'data-date': True})
                if date_elem:
                    date_str = date_elem.get('data-date')
                    date_obj, error = self.parse_date_string(date_str)
                    if date_obj:
                        return date_obj, None
            
            # GOOGLE SKILLS BOOST EXTRACTION
            if not is_credly:
                # Method 1: Look for specific known elements
                # Skillboost: <span class="completed-at">Aug 30, 2025</span>
                completed_at_elem = soup.find('span', class_='completed-at')
                if completed_at_elem:
                    text = completed_at_elem.get_text().strip()
                    # Remove HTML comments and whitespace
                    text = re.sub(r'<!--.*?-->', '', text).strip()
                    if text:
                        date_obj, error = self.parse_date_string(text)
                        if date_obj:
                            return date_obj, None
                
                # Skillboost: Look for ql-badge element with JSON data (like reference file)
                # <ql-badge badge='{"completedAt":"Aug 30, 2025",...}'>
                ql_badge_elem = soup.find('ql-badge')
                if ql_badge_elem and ql_badge_elem.get('badge'):
                    try:
                        badge_attr = ql_badge_elem.get('badge')
                        # Replace HTML entities
                        badge_attr = badge_attr.replace('&quot;', '"')
                        badge_data = json.loads(badge_attr)
                        if "completedAt" in badge_data:
                            date_str = badge_data["completedAt"]
                            date_obj, error = self.parse_date_string(date_str)
                            if date_obj:
                                return date_obj, None
                    except (json.JSONDecodeError, AttributeError, KeyError):
                        pass
                
                # Skillboost: Look for div with class containing 'date' inside public-profile-badge (like reference file)
                public_badge_divs = soup.find_all('div', class_=re.compile(r'public-profile-badge', re.I))
                for badge_div in public_badge_divs:
                    date_divs = badge_div.find_all('div', class_=re.compile(r'date', re.I))
                    for date_div in date_divs:
                        text = date_div.get_text().strip()
                        if text:
                            date_obj, error = self.parse_date_string(text)
                            if date_obj:
                                return date_obj, None
            
            # Comprehensive date patterns to search for in page text (general fallback)
            # These patterns match various date formats
            date_patterns = [
                # General patterns (like reference file)
                r'(\w+ \d{1,2}, \d{4})',  # "Aug 30, 2025", "November 12, 2025"
                r'(\d{1,2}/\d{1,2}/\d{4})',  # "11/12/2025"
                r'(\d{4}-\d{2}-\d{2})',  # "2025-10-27"
                
                # Additional patterns for other formats
                r'Completed on:\s*([^\n\r<]+)',  # "Completed on: 27-10-2025"
                r'Date completed:\s*([^\n\r<]+)',  # "Date completed: 27/10/2025"
                r'Earned on:\s*([^\n\r<]+)',  # "Earned on: October 27, 2025"
                
                # Month name patterns without comma (day first)
                r'(\d{1,2} \w+ \d{4})',  # "27 October 2025", "31 Aug 2025"
                
                # Dash-separated formats (could be DD-MM-YYYY or MM-DD-YYYY)
                r'(\d{1,2}-\d{1,2}-\d{4})',  # "27-10-2025" or "10-27-2025"
            ]
            
            # Method 2: Look for time elements with datetime attribute
            time_elements = soup.find_all('time')
            for time_elem in time_elements:
                # Try datetime attribute first
                if time_elem.get('datetime'):
                    try:
                        date_obj = datetime.fromisoformat(time_elem['datetime'].replace('Z', '+00:00')).date()
                        return date_obj, None
                    except (ValueError, AttributeError):
                        pass
                
                # Try text content of time element
                time_text = time_elem.get_text().strip()
                if time_text:
                    date_obj, error = self.parse_date_string(time_text)
                    if date_obj:
                        return date_obj, None
            
            # Method 3: Look for elements with date-related class names
            date_class_pattern = re.compile(r'completed-at|date|issued|completed|earned', re.I)
            for tag_name in ['span', 'div', 'p', 'td', 'li']:
                date_elements = soup.find_all(tag_name, class_=date_class_pattern)
                for elem in date_elements:
                    text = elem.get_text().strip()
                    # Remove HTML comments
                    text = re.sub(r'<!--.*?-->', '', text).strip()
                    if text and len(text) < 50:  # Reasonable date length
                        date_obj, error = self.parse_date_string(text)
                        if date_obj:
                            return date_obj, None
            
            # Try each pattern in page HTML (like reference file uses page_source)
            # Search in HTML first, then fallback to text
            for search_content in [page_html, page_text]:
                for pattern in date_patterns:
                    matches = re.finditer(pattern, search_content, re.IGNORECASE)
                    for match in matches:
                        date_str = match.group(1).strip()
                        # Clean up common suffixes/prefixes
                        date_str = re.sub(r'^(Date issued|Completed on|Date completed|Earned on):\s*', '', date_str, flags=re.IGNORECASE)
                        date_str = date_str.strip()
                        
                        # Skip if too long (likely not a date)
                        if len(date_str) > 50:
                            continue
                        
                        # Try to parse the date string
                        date_obj, error = self.parse_date_string(date_str)
                        if date_obj:
                            return date_obj, None
            
            # Additional search in all text content for any missed dates
            # (platform-specific and time elements already checked above)
            
            # Debug: If we reach here, no date was found
            # For Credly badges, provide more detailed debugging info
            if is_credly:
                # Check if "Date issued" text exists in the page at all
                has_date_issued = 'Date issued' in page_html or 'Date issued' in page_text
                # Try to find a sample around "Date issued" if it exists
                debug_sample = ""
                if has_date_issued:
                    # Find position of "Date issued" and get surrounding text (more context)
                    match = re.search(r'Date\s+issued[^<]{0,100}', page_html, re.IGNORECASE)
                    if match:
                        debug_sample = match.group(0)
                    else:
                        match = re.search(r'Date\s+issued[^\n]{0,100}', page_text, re.IGNORECASE)
                        if match:
                            debug_sample = match.group(0)
                    
                    # Also try to find the badge-banner-issued-to-text div content
                    badge_div = soup.find('div', class_=re.compile(r'badge-banner-issued-to-text', re.I))
                    if badge_div:
                        div_text = badge_div.get_text()
                        debug_sample += f" | Div text: {div_text[:200]}"
                
                if has_date_issued:
                    return None, f"Could not extract completion date from Credly badge (found 'Date issued' but couldn't parse date. Sample: {debug_sample[:200]})"
                else:
                    return None, f"Could not extract completion date from Credly badge (no 'Date issued' text found in page. Page length: {len(page_html)} chars)"
            else:
                # For Google badges, use simpler message
                page_text_sample = page_text[:500] if 'page_text' in locals() else "N/A"
                return None, f"Could not extract completion date from badge page (page sample: {page_text_sample[:100]}...)"
            
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
                # Try Selenium first for Credly (more reliable for dynamic content)
                if SELENIUM_AVAILABLE:
                    try:
                        driver = self.get_selenium_driver()
                        if driver:
                            driver.get(badge_url)
                            wait = WebDriverWait(driver, 15)
                            # Wait for badge name element (same as date extraction)
                            try:
                                badge_element = wait.until(EC.presence_of_element_located(
                                    (By.XPATH, '//h1[contains(@class, "ac-heading--badge-name-hero")]')
                                ))
                                badge_name = badge_element.text.strip()
                                if badge_name:
                                    return badge_name, None
                            except (TimeoutException, NoSuchElementException):
                                pass
                    except Exception as e:
                        # Fall back to requests method if Selenium fails
                        pass
                
                # Credly-specific extraction methods (fallback to requests/BeautifulSoup)
                
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
    
    def normalize_course_name(self, course_name, is_credly=False):
        """Normalize course name for better matching by removing prefixes, suffixes, and extra text"""
        if not course_name:
            return ""
        
        # Convert to lowercase and strip
        normalized = course_name.lower().strip()
        
        # Remove trailing commas, periods, and extra whitespace
        normalized = re.sub(r'[,\.]+$', '', normalized).strip()
        
        # Remove content in square brackets like [Dev Ops], [Track Name], etc.
        normalized = re.sub(r'\[.*?\]', '', normalized).strip()
        
        # Remove content in parentheses (but keep it for now, might be useful)
        # normalized = re.sub(r'\(.*?\)', '', normalized).strip()
        
        # For Credly badges, remove common suffixes
        if is_credly:
            # Remove patterns like "Skill Badge was issued by..." or "was issued by..."
            normalized = re.sub(r'\s*skill\s*badge\s*was\s*issued\s*by.*$', '', normalized, flags=re.IGNORECASE).strip()
            normalized = re.sub(r'\s*was\s*issued\s*by.*$', '', normalized, flags=re.IGNORECASE).strip()
            # Remove "to [Name]" patterns
            normalized = re.sub(r'\s+to\s+[A-Z\s]+\.?\s*$', '', normalized, flags=re.IGNORECASE).strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def extract_core_course_name(self, course_name):
        """Extract the core course name by removing prefixes and suffixes"""
        if not course_name:
            return ""
        
        # Remove common prefixes
        prefixes = [
            r'^\[.*?\]\s*',  # [Track Name] prefix
            r'^track\s*:\s*',  # Track: prefix
        ]
        for prefix in prefixes:
            course_name = re.sub(prefix, '', course_name, flags=re.IGNORECASE).strip()
        
        return course_name.strip()
    
    def match_course_names(self, found_name, expected_name, is_credly=False):
        """Improved course name matching that handles prefixes, suffixes, and extra text"""
        # Normalize both names
        found_normalized = self.normalize_course_name(found_name, is_credly=is_credly)
        expected_normalized = self.normalize_course_name(expected_name, is_credly=False)
        
        # Extract core course names (remove prefixes)
        found_core = self.extract_core_course_name(found_normalized)
        expected_core = self.extract_core_course_name(expected_normalized)
        
        # Direct match on normalized names
        if found_normalized == expected_normalized:
            return True, "exact match"
        
        # Direct match on core names
        if found_core == expected_core and found_core:
            return True, "core name match"
        
        # Contains match (either direction)
        if expected_normalized in found_normalized or found_normalized in expected_normalized:
            return True, "contains match"
        
        # Check if core names appear in the full normalized names
        if expected_core and expected_core in found_normalized:
            return True, "expected core in found name"
        if found_core and found_core in expected_normalized:
            return True, "found core in expected name"
        
        # Word-based matching - split into words and remove empty strings and very short words
        def get_meaningful_words(text):
            words = [w for w in text.split() if len(w) > 2]  # Ignore words <= 2 chars
            return set(words)
        
        found_words = get_meaningful_words(found_normalized)
        expected_words = get_meaningful_words(expected_normalized)
        
        if len(expected_words) == 0:
            return False, "no meaningful words in expected name"
        
        # Calculate match ratio based on meaningful words
        common_words = found_words & expected_words
        match_ratio = len(common_words) / len(expected_words) if expected_words else 0
        
        # Also try with core names
        found_core_words = get_meaningful_words(found_core)
        expected_core_words = get_meaningful_words(expected_core)
        if expected_core_words:
            core_common_words = found_core_words & expected_core_words
            core_match_ratio = len(core_common_words) / len(expected_core_words)
            match_ratio = max(match_ratio, core_match_ratio)
        
        # Require at least 60% of meaningful words to match
        if match_ratio >= 0.6:
            return True, f"word match ({int(match_ratio * 100)}%)"
        
        return False, f"insufficient match ({int(match_ratio * 100)}%)"
    
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
        
        # Extract completion date (always try to extract, even if course verification might fail)
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
        
        # Improved fuzzy match with expected course
        is_match, match_type = self.match_course_names(course_name, expected_course, is_credly=is_credly_badge)
        
        if is_match:
            return True, f"Course verified ({platform} - {match_type})", completion_date
        
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
    
    def verify_profiles(self, limit=None, force_reverify=False):
        """Verify all unverified Skillboost profiles using parallel processing
        
        Args:
            limit: Maximum number of profiles to verify
            force_reverify: If True, reverify ALL profiles regardless of their current status
        """
        db_session = db_manager.get_session()
        
        try:
            # Get profiles that need verification
            if force_reverify:
                # Include ALL profiles (verified, failed, or pending) for re-verification
                # Exclude records with empty profile links
                query = db_session.query(SkillboostProfile).filter(
                    SkillboostProfile.google_cloud_skills_boost_profile_link.isnot(None),
                    SkillboostProfile.google_cloud_skills_boost_profile_link != '',
                    SkillboostProfile.google_cloud_skills_boost_profile_link != '-'
                )
            else:
                # Only get profiles that are unverified (valid is NULL)
                query = db_session.query(SkillboostProfile).filter(
                    SkillboostProfile.valid.is_(None),
                    SkillboostProfile.google_cloud_skills_boost_profile_link.isnot(None),
                    SkillboostProfile.google_cloud_skills_boost_profile_link != '',
                    SkillboostProfile.google_cloud_skills_boost_profile_link != '-'
                )
            
            if limit:
                query = query.limit(limit)
            
            profiles = query.all()
            
            print(f"\nVerifying {len(profiles)} Skillboost profiles using {self.max_workers} parallel workers...")
            print(f"Estimated time: ~{len(profiles) // self.max_workers // 60} minutes")
            print(f"Note: Verification checks URL validity and accessibility only (no name matching)")
            if force_reverify:
                print("Mode: Force re-verification - ALL profiles will be reverified")
            
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
            
            # Check for empty or invalid badge links (including "-")
            badge_link_clean = badge_link.strip() if badge_link else ''
            if not badge_link_clean or badge_link_clean == '' or badge_link_clean == '-':
                return {
                    'email': email,
                    'problem_statement': problem_statement,
                    'valid': False,
                    'remarks': 'No badge link provided',
                    'completion_date': None
                }
            
            # Check if it's a Credly badge for special debugging
            from urllib.parse import urlparse
            parsed_url = urlparse(badge_link)
            is_credly = 'credly.com' in parsed_url.netloc if parsed_url.netloc else False
            
            valid, remarks, completion_date = self.verify_badge_url(badge_link, problem_statement)
            
            # Debug: Log date extraction result (more verbose for Credly badges)
            # Use a simple counter stored in the result dict to track across workers
            debug_key = f"debug_{email}_{problem_statement}"
            if not hasattr(self, '_debug_logged'):
                self._debug_logged = set()
            
            # Always log Credly badges (to debug date extraction issues)
            if is_credly:
                if completion_date:
                    print(f"    [DEBUG CREDLY] ✓ Date extracted: {completion_date} for {email[:30]}...")
                else:
                    print(f"    [DEBUG CREDLY] ✗ No date extracted for {email[:30]}... (URL: {badge_link[:60]}...)")
            elif len(self._debug_logged) < 3 and debug_key not in self._debug_logged:
                self._debug_logged.add(debug_key)
                if completion_date:
                    print(f"    [DEBUG] ✓ Date extracted: {completion_date} for {email[:30]}...")
                else:
                    print(f"    [DEBUG] ✗ No date extracted for {email[:30]}... (URL: {badge_link[:60]}...)")
            
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
            force_reverify: If True, reverify ALL badges regardless of their current status (including date validation)
        """
        db_session = db_manager.get_session()
        
        try:
            # Get badges that need verification
            if force_reverify:
                # Include ALL badges (verified, failed, or pending) for re-verification
                # This will check both course match AND date requirement (>= 2025-10-27)
                # Exclude records with "-" or empty badge links
                query = db_session.query(Course).filter(
                    Course.share_skill_badge_public_link.isnot(None),
                    Course.share_skill_badge_public_link != '-',
                    Course.share_skill_badge_public_link != ''
                )
            else:
                # Only get badges that are unverified (valid is NULL)
                # Exclude records with "-" or empty badge links
                query = db_session.query(Course).filter(
                    Course.valid.is_(None),
                    Course.share_skill_badge_public_link.isnot(None),
                    Course.share_skill_badge_public_link != '-',
                    Course.share_skill_badge_public_link != ''
                )
            
            if limit:
                query = query.limit(limit)
            
            badges = query.all()
            
            print(f"\nVerifying {len(badges)} course badges using {self.max_workers} parallel workers...")
            print(f"Estimated time: ~{len(badges) // self.max_workers // 60} minutes")
            if force_reverify:
                print("Mode: Force re-verification - ALL badges will be reverified (including date validation >= 2025-10-27)")
            
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
                        # Always update completion_date if extracted (even if verification is pending)
                        if result.get('completion_date') is not None:
                            badge.completion_date = result['completion_date']
                            print(f"    [DEBUG] Saving completion_date {result['completion_date']} for {result['email'][:20]}...")
                        else:
                            print(f"    [DEBUG] No completion_date to save for {result['email'][:20]}... (valid={result.get('valid')})")
                        
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
                            # Verification pending, but still update date if extracted
                            badge.remarks = result['remarks']
                            with self.stats_lock:
                                self.stats['badges_pending'] += 1
                            status = f"⚠ ({result['remarks'][:30]}...)"
                            # Note: completion_date was already updated above if extracted
                        
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
            # Close Selenium drivers
            self.close_selenium_drivers()
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
        force_reverify: If True, reverify ALL badges regardless of status (including date validation)
    """
    verifier = SkillboostVerifier(max_workers=max_workers)
    
    if profiles:
        verifier.verify_profiles(limit=limit, force_reverify=force_reverify)
    
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
    parser.add_argument('--force-reverify', action='store_true', help='Reverify ALL badges regardless of status (will validate date >= 2025-10-27)')
    
    args = parser.parse_args()
    
    # Initialize database connection
    if not db_manager.initialize():
        print("✗ Failed to connect to database. Check your configuration.")
        sys.exit(1)
    
    print("✓ Database connection established")
    if SELENIUM_AVAILABLE:
        print("✓ Selenium available - Credly badges will use Selenium for date extraction")
    else:
        print("⚠ Selenium not available - Credly badges will use fallback method")
    print("="*60)
    print("Starting Skillboost Verification with Parallel Processing")
    print(f"Workers: {args.workers}")
    if args.force_reverify:
        print("Mode: Force re-verification (will reverify ALL badges and validate date >= 2025-10-27)")
    print("="*60)
    
    profiles = not args.badges_only
    badges = not args.profiles_only
    
    run_verification(profiles=profiles, badges=badges, limit=args.limit, max_workers=args.workers, force_reverify=args.force_reverify)


if __name__ == '__main__':
    main()


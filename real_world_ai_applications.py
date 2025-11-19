import requests
import pandas as pd
import time
import random
import os
import logging
import json
import re
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import lru_cache
from typing import Tuple, Dict, List, Optional, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading

# Optional imports
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
    logging.warning("Selenium packages not installed. Credly badge validation will be disabled.")
    SELENIUM_AVAILABLE = False

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

# Set up logging
def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"badge_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Thread-local storage for session objects
thread_local = threading.local()

# Results cache to avoid redundant validations
results_cache = {}
cache_lock = threading.Lock()

def get_session():
    """Get a requests session for the current thread with retry capabilities"""
    if not hasattr(thread_local, "session"):
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        thread_local.session = session
    return thread_local.session

def normalize_url(url: str) -> str:
    """Normalize URL format for consistency"""
    if not isinstance(url, str) or not url.strip():
        return ""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    parsed = urlparse(url)
    if parsed.netloc == "cloudskillsboost.google":
        url = url.replace("cloudskillsboost.google", "www.cloudskillsboost.google")
    return url

# Selenium WebDriver singleton
driver_lock = threading.Lock()
selenium_drivers = {}

def get_selenium_driver():
    """Get or create a Selenium WebDriver instance for the current thread"""
    thread_id = threading.get_ident()
    with driver_lock:
        if thread_id not in selenium_drivers:
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
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                driver.set_page_load_timeout(30)  # Increased timeout
                driver.set_script_timeout(30)     # Increased timeout
                selenium_drivers[thread_id] = driver
            except WebDriverException as e:
                logger.error(f"Failed to initialize WebDriver: {str(e)}")
                raise
    return selenium_drivers[thread_id]

def close_selenium_drivers():
    """Close all Selenium WebDrivers"""
    with driver_lock:
        for thread_id, driver in list(selenium_drivers.items()):
            try:
                driver.quit()
                logger.debug(f"Successfully closed WebDriver for thread {thread_id}")
            except Exception as e:
                logger.warning(f"Error closing WebDriver for thread {thread_id}: {str(e)}")
            finally:
                selenium_drivers.pop(thread_id, None)
        selenium_drivers.clear()
        logger.debug("All WebDrivers closed and resources released")

def is_date_valid(date_str: str, cutoff_date_str: str, is_credly: bool = False) -> bool:
    """Check if a date string is valid (on or after the cutoff date)"""
    if not date_str:
        return False
        
    try:
        date_formats = [
            "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d",
            "%d %b %Y", "%d %B %Y", "%B %d %Y", "%b %d %Y"
        ]
        
        issue_date = None
        for fmt in date_formats:
            try:
                issue_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
                
        if not issue_date:
            logger.warning(f"Could not parse date: {date_str}")
            return False
            
        cutoff_date = None
        for fmt in date_formats:
            try:
                cutoff_date = datetime.strptime(cutoff_date_str, fmt)
                break
            except ValueError:
                continue
                
        if not cutoff_date:
            logger.warning(f"Could not parse cutoff date: {cutoff_date_str}")
            return False
        
        return issue_date >= cutoff_date
        
    except Exception as e:
        logger.warning(f"Error validating date: {str(e)}")
        return False

def fallback_validate_url(url: str) -> Tuple[bool, str, str, str]:
    """Fallback validation using HTTP requests when Selenium fails"""
    try:
        session = get_session()
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        page_source = response.text
        badge_name = ""
        issue_date = ""
        
        # Extract badge name
        name_pattern = r'<h1[^>]*>(.*?)</h1>|<title[^>]*>(.*?)</title>|"name":"([^"]+)"'
        name_matches = re.findall(name_pattern, page_source)
        for match in name_matches:
            for group in match:
                if group.strip():
                    badge_name = group.strip()
                    break
            if badge_name:
                break
                
        # Extract issue date
        date_patterns = [
            r"(\w+ \d{1,2}, \d{4})",
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{4}-\d{2}-\d{2})"
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                issue_date = matches[0]
                break
        
        is_valid = bool(badge_name and issue_date)
        message = "Valid badge (fallback method)" if is_valid else "Invalid badge (fallback method)"
        
        return is_valid, message, url, issue_date
    except Exception as e:
        logger.warning(f"Fallback validation failed for {url}: {str(e)}")
        return False, f"Fallback validation error: {str(e)}", url, ""

def is_valid_badge_url(url: str, valid_domains: List[str], profile_path_prefix: str, expected_badge_name: str, retries: int = 2) -> Tuple[bool, str, str, str]:
    """Check if a Google Cloud Skills Boost badge URL is valid using Selenium with retries"""
    if not SELENIUM_AVAILABLE:
        return False, "Selenium not available for Google badge validation", url, ""
    
    with cache_lock:
        if url in results_cache:
            return results_cache[url]
    
    normalized_url = normalize_url(url)
    if not normalized_url:
        result = (False, "URL could not be normalized", url, "")
        with cache_lock:
            results_cache[url] = result
        return result

    parsed = urlparse(normalized_url)
    if parsed.netloc not in valid_domains:
        result = (False, f"Incorrect domain: {parsed.netloc}", normalized_url, "")
        with cache_lock:
            results_cache[url] = result
        return result

    if not parsed.path.startswith(profile_path_prefix) or "/badges/" not in parsed.path:
        result = (False, f"URL does not have a valid badge path: {parsed.path}", normalized_url, "")
        with cache_lock:
            results_cache[url] = result
        return result

    for attempt in range(retries + 1):
        try:
            driver = get_selenium_driver()
            driver.get(normalized_url)
            
            wait = WebDriverWait(driver, 15)  # Increased wait time
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            issue_date = ""
            badge_name = ""
            
            try:
                date_element = driver.find_element(By.XPATH, "//div[contains(@class, 'public-profile-badge')]/div[contains(@class, 'date')]")
                if date_element:
                    issue_date = date_element.text.strip()
            except NoSuchElementException:
                pass
            
            if not issue_date or not badge_name:
                try:
                    badge_element = driver.find_element(By.TAG_NAME, "ql-badge")
                    badge_attr = badge_element.get_attribute("badge")
                    if badge_attr:
                        badge_data = json.loads(badge_attr.replace("&quot;", '"'))
                        if "completedAt" in badge_data and not issue_date:
                            issue_date = badge_data["completedAt"]
                        possible_keys = ["name", "title", "badgeName", "badge_name"]
                        for key in possible_keys:
                            if key in badge_data and not badge_name:
                                badge_name = badge_data[key]
                                break
                except (NoSuchElementException, json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Could not extract data from badge element: {e}")
            
            if not issue_date:
                page_source = driver.page_source
                date_patterns = [
                    r"(\w+ \d{1,2}, \d{4})",
                    r"(\d{1,2}/\d{1,2}/\d{4})",
                    r"(\d{4}-\d{2}-\d{2})"
                ]
                for pattern in date_patterns:
                    matches = re.findall(pattern, page_source)
                    if matches:
                        issue_date = matches[0]
                        break
            
            if not badge_name:
                try:
                    name_element = driver.find_element(By.TAG_NAME, "h1")
                    if name_element:
                        badge_name = name_element.text.strip()
                except NoSuchElementException:
                    pass
            
            if not badge_name:
                try:
                    name_element = driver.find_element(By.XPATH, "//div[contains(@class, 'badge-title')]")
                    if name_element:
                        badge_name = name_element.text.strip()
                except NoSuchElementException:
                    pass
            
            if not badge_name:
                badge_name = "Unknown"
                logger.warning(f"Could not find badge name for URL: {normalized_url}")
            
            logger.info(f"Google Cloud badge: {badge_name} | Issued: {issue_date}")
            
            is_url_valid = driver.current_url and "public_profiles" in driver.current_url and "/badges/" in driver.current_url
            name_valid = badge_name == expected_badge_name
            date_valid = is_date_valid(issue_date, "Apr 1, 2025", is_credly=False)
            
            is_valid = is_url_valid and name_valid and date_valid
            
            message = "Valid badge URL"
            if not is_url_valid:
                message = "Invalid badge URL"
            elif not name_valid:
                message = f"Unexpected badge name: {badge_name}"
            elif not date_valid:
                message = f"Badge issued before April 1, 2025: {issue_date}"
            
            result = (is_valid, message, driver.current_url if is_url_valid else normalized_url, issue_date)
            with cache_lock:
                results_cache[url] = result
            return result
            
        except (TimeoutException, WebDriverException) as e:
            logger.warning(f"Attempt {attempt + 1} failed for {normalized_url}: {str(e)}")
            if attempt == Retries - 1:
                logger.error(f"All retries failed for {normalized_url}. Using fallback validation.")
                result = fallback_validate_url(normalized_url)
                with cache_lock:
                    results_cache[url] = result
                return result
            time.sleep(random.uniform(1, 3))  # Delay before retry

def is_valid_credly_badge_url(url: str, expected_badge_name: str, retries: int = 2) -> Tuple[bool, str, str, str]:
    """Check if a Credly badge URL is valid and matches the expected badge name with retries"""
    if not SELENIUM_AVAILABLE:
        return False, "Selenium not available for Credly validation", url, ""
    
    with cache_lock:
        if url in results_cache:
            return results_cache[url]
    
    for attempt in range(retries + 1):
        try:
            driver = get_selenium_driver()
            driver.get(url)
            
            wait = WebDriverWait(driver, 15)  # Increased wait time
            badge_element = wait.until(EC.presence_of_element_located(
                (By.XPATH, '//h1[contains(@class, "ac-heading--badge-name-hero")]')
            ))
            badge_name = badge_element.text.strip()

            try:
                user_element = driver.find_element(By.XPATH, '//a[starts-with(@aria-label, "View") and contains(@aria-label, "profile")]')
                user_name = user_element.text.strip()
            except:
                user_name = "Unknown"

            issue_date = ""
            try:
                date_element = driver.find_element(By.XPATH, '//div[contains(@class, "badge-banner-issued-to-text")]/p[contains(text(), "Date issued:")]')
                if date_element:
                    issue_date = date_element.text.replace("Date issued:", "").strip()
            except NoSuchElementException:
                pass
            
            if not issue_date:
                try:
                    issue_date_element = driver.find_element(By.XPATH, '//div[text()="Date issued:"]/following-sibling::div[1]')
                    issue_date = issue_date_element.text.strip()
                except NoSuchElementException:
                    pass
            
            if not issue_date:
                page_source = driver.page_source
                date_patterns = [
                    r"Date issued:\s*(\w+ \d{1,2}, \d{4})",
                    r"Date issued:\s*(\d{1,2}/\d{1,2}/\d{4})",
                    r"Date issued:\s*(\d{4}-\d{2}-\d{2})"
                ]
                for pattern in date_patterns:
                    matches = re.findall(pattern, page_source)
                    if matches:
                        issue_date = matches[0]
                        break
            
            logger.info(f"Credly badge: {badge_name} | User: {user_name} | Issued: {issue_date}")

            name_valid = badge_name == expected_badge_name
            date_valid = is_date_valid(issue_date, "April 01, 2025", is_credly=True)
            is_valid = name_valid and date_valid
            
            message = "Valid Credly badge"
            if not name_valid:
                message = f"Unexpected badge name: {badge_name}"
            elif not date_valid:
                message = f"Badge issued before April 1, 2025: {issue_date}"
            
            result = (is_valid, message, url, issue_date)
            with cache_lock:
                results_cache[url] = result
            return result

        except (TimeoutException, WebDriverException) as e:
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
            if attempt == retries - 1:
                logger.error(f"All retries failed for {url}. Using fallback validation.")
                result = fallback_validate_url(url)
                with cache_lock:
                    results_cache[url] = result
                return result
            time.sleep(random.uniform(1, 3))  # Delay before retry

def process_url_batch(urls: List[Tuple[int, str]], config: Dict) -> List[Tuple[int, bool, str, str, str]]:
    results = []
    
    try:
        with ThreadPoolExecutor(max_workers=config["max_workers"]) as executor:
            future_to_index = {}
            
            for idx, url in urls:
                if "credly.com" in url.lower():
                    future = executor.submit(
                        is_valid_credly_badge_url, 
                        url, 
                        config["credly_badge_name"],
                        retries=2
                    )
                else:
                    future = executor.submit(
                        is_valid_badge_url, 
                        url,
                        config["valid_domains"],
                        config["profile_path_prefix"],
                        config["google_badge_name"],
                        retries=2
                    )
                future_to_index[future] = idx
            
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    is_valid, message, final_url, issue_date = future.result()
                    results.append((idx, is_valid, final_url, message, issue_date))
                except Exception as e:
                    logger.error(f"Error processing index {idx}: {str(e)}")
                    results.append((idx, False, "", f"Processing error: {str(e)}", ""))
                
                time.sleep(random.uniform(0.1, 0.3))  # Adjusted delay
    finally:
        close_selenium_drivers()
    
    return results

def process_badge_urls(df: pd.DataFrame, url_column: str, config: Dict) -> pd.DataFrame:
    """Process all badge URLs in the DataFrame"""
    result_df = df.copy()
    verification_column = f"{config['badge_column_prefix']} Verification"
    link_column = f"{config['badge_column_prefix']} public view link" 
    message_column = f"{config['badge_column_prefix']} Message"
    date_column = f"{config['badge_column_prefix']} Issue Date"
    
    result_df[verification_column] = "FALSE"
    result_df[link_column] = ""
    result_df[message_column] = ""
    result_df[date_column] = ""

    url_data = []
    for idx, row in df.iterrows():
        url = str(row.get(url_column, "")).strip()
        if url and not pd.isna(url):
            url_data.append((idx, url))

    total = len(url_data)
    logger.info(f"Found {total} non-empty badge URLs to validate.")
    if not url_data:
        return result_df

    batch_size = min(config["batch_size"], 15)  # Reduced batch size for stability
    batches = [url_data[i:i + batch_size] for i in range(0, len(url_data), batch_size)]
    
    processed_count = 0
    valid_count = 0
    
    for batch_num, batch in enumerate(batches):
        logger.info(f"Processing batch {batch_num + 1}/{len(batches)} ({len(batch)} URLs)...")
        
        batch_results = process_url_batch(batch, config)
        
        for idx, is_valid, final_url, message, issue_date in batch_results:
            result_df.at[idx, verification_column] = "TRUE" if is_valid else "FALSE"
            result_df.at[idx, link_column] = final_url
            result_df.at[idx, message_column] = message
            result_df.at[idx, date_column] = issue_date
            
            if is_valid:
                valid_count += 1
                
        processed_count += len(batch)
        logger.info(f"Processed {processed_count}/{total} URLs. Valid badges so far: {valid_count}")
        
        if batch_num < len(batches) - 1:
            time.sleep(random.uniform(2, 5))  # Increased delay between batches

    logger.info(f"URL validation complete. Valid badges: {valid_count}/{total}")
    return result_df

def append_log_to_google_sheet(log_row: list, config: Dict) -> bool:
    """Append a log row to Google Sheets"""
    if not GSHEETS_AVAILABLE:
        logger.warning("Google Sheets logging unavailable. Install gspread package if needed.")
        return False

    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials_file = config.get("google_credentials", "")
        if not credentials_file or not os.path.exists(credentials_file):
            logger.error(f"Google credentials file not found: {credentials_file}")
            return False

        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(config["google_spreadsheet_id"])
        worksheet = spreadsheet.worksheet(config["google_worksheet"])
        worksheet.append_row(log_row)
        logger.info("Log successfully appended to Google Sheet.")
        return True
    except Exception as e:
        logger.error(f"Error logging to Google Sheets: {str(e)}")
        return False

def save_results(result_df: pd.DataFrame, config: Dict) -> str:
    """Save results to Excel file"""
    output_dir = config.get("output_dir", "badge_verification_results")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    badge_name_simplified = config["badge_column_prefix"].lower().replace(" ", "_")
    
    output_file = os.path.join(
        output_dir, 
        f"{badge_name_simplified}_verification_{timestamp}.xlsx"
    )
    result_df.to_excel(output_file, index=False)
    logger.info(f"Results saved to {output_file}")
    
    csv_file = os.path.join(
        output_dir, 
        f"{badge_name_simplified}_verification_{timestamp}.csv"
    )
    result_df.to_csv(csv_file, index=False)
    logger.info(f"CSV backup saved to {csv_file}")
    
    return output_file

def optimize_thread_pool():
    """Configure thread pool settings for Threadripper performance"""
    import concurrent.futures
    import os
    
    os.environ["PYTHONTHREADDEBUG"] = "0"
    os.environ["PYTHONTRACEMALLOC"] = "0"
    
    try:
        import threading
        threading.stack_size(2 * 1024 * 1024)
    except (ImportError, RuntimeError):
        pass
    
    return

def get_config():
    """Return configuration settings for the badge verification script"""
    return {
        "input_file": r"D:\DOWNLOADS\Build Real World AI Applications with Gemini and Imagen - 12-09-25.csv",
        "url_column": "Share the Skill Bagde link for 'Build Real World AI Applications with Gemini and Imagen' course.",
        "output_dir": "Real_World_AI_Applications_with_Gemini_badge",
        "google_badge_name": "Build Real World AI Applications with Gemini and Imagen",
        "badge_column_prefix": "real world ai applications with gemini  ",
        "credly_badge_name": "Build Real World AI Applications with Gemini and Imagen Skill Badge",
        "valid_domains": ["www.cloudskillsboost.google", "cloudskillsboost.google", "partner.cloudskillsboost.google"],
        "profile_path_prefix": "/public_profiles/",
        "batch_size": 15,  # Reduced for stability
        "max_workers": 10,  # Reduced to prevent resource exhaustion
        "output_columns": [
            "Leader Name",
            "Leader Email",
            "Share the Skill Bagde link for 'Build Real World AI Applications with Gemini and Imagen' course."
        ],
        "google_logging_enabled": True,
        "google_credentials": r"D:\Gen-ai_master_tracker\vision-playground-423507-d37e0741a307.json",
        "google_spreadsheet_id": "1UIVQ1KA91QpvcPFK6Aoc6JnaddZc5xLO5GYHGjISni4",
        "google_worksheet": "Sheet2"
    }

def main():
    """Main function to execute badge verification"""
    optimize_thread_pool()
    config = get_config()
    
    try:
        logger.info(f"Starting badge verification using file: {config['input_file']}")
        logger.info(f"Verifying badge: {config['badge_column_prefix']}")
        logger.info(f"Using optimized settings for Threadripper 7970X: {config['max_workers']} workers")
        
        if not os.path.exists(config['input_file']):
            raise FileNotFoundError(f"Input file not found: {config['input_file']}")
        
        try:
            df = pd.read_csv(config['input_file'])
            logger.info(f"Successfully loaded CSV file: {config['input_file']}")
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            raise ValueError(f"Failed to read CSV: {config['input_file']}")
        
        if df.empty:
            raise ValueError(f"The CSV file is empty!")
            
        logger.info(f"Loaded {len(df)} rows from CSV.")
        logger.info(f"Available columns: {', '.join(df.columns)}")
        
        if config["url_column"] not in df.columns:
            raise ValueError(f"Could not find URL column: {config['url_column']} in the CSV.")
            
        processed_df = process_badge_urls(df, config["url_column"], config)
        
        output_columns = [
            col for col in config["output_columns"] if col in processed_df.columns
        ]
        
        verification_column = f"{config['badge_column_prefix']} Verification"
        link_column = f"{config['badge_column_prefix']} public view link" 
        message_column = f"{config['badge_column_prefix']} Message"
        date_column = f"{config['badge_column_prefix']} Issue Date"
        
        output_columns.extend([
            verification_column,
            link_column,
            message_column,
            date_column
        ])
        
        result_df = processed_df[output_columns]
        output_file = save_results(result_df, config)
        
        verified_count = result_df[verification_column].value_counts().get("TRUE", 0)
        logger.info(f"Verified badge URLs: {verified_count} / {len(result_df)}")
        
        if config.get("google_logging_enabled", False) and os.path.exists(config.get('google_credentials', '')):
            log_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_row = [log_timestamp, config['input_file'], output_file, str(verified_count)]
            append_log_to_google_sheet(log_row, config)
        
        logger.info(f"{config['badge_column_prefix']} URL validation completed successfully.")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
    finally:
        close_selenium_drivers()
        logger.info("Resources cleaned up. Verification process complete.")

if __name__ == "__main__":
    main()
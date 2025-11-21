"""
Test script for Credly badge date extraction
Tests Selenium-based date extraction from Credly badge URLs
"""
import sys
import os
import re
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Selenium imports
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
    print("✓ Selenium is available")
except ImportError as e:
    SELENIUM_AVAILABLE = False
    print(f"✗ Selenium not available: {e}")
    sys.exit(1)

import time


def parse_date_string(date_str):
    """Parse various date string formats"""
    if not date_str:
        return None, "Empty date string"
    
    date_str = date_str.strip()
    
    # Common date formats
    date_formats = [
        '%B %d, %Y',      # January 15, 2025
        '%b %d, %Y',      # Jan 15, 2025
        '%d %B %Y',       # 15 January 2025
        '%d %b %Y',       # 15 Jan 2025
        '%Y-%m-%d',       # 2025-01-15
        '%m/%d/%Y',       # 01/15/2025
        '%d/%m/%Y',       # 15/01/2025
        '%m-%d-%Y',       # 01-15-2025
        '%d-%m-%Y',       # 15-01-2025
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date(), None
        except ValueError:
            continue
    
    return None, f"Could not parse date: {date_str}"


def extract_credly_date_selenium(badge_url, retries=2):
    """Extract completion date from Credly badge using Selenium"""
    if not SELENIUM_AVAILABLE:
        return None, "Selenium not available"
    
    driver = None
    for attempt in range(retries + 1):
        try:
            print(f"\n[Attempt {attempt + 1}] Initializing WebDriver...")
            
            # Try to get ChromeDriver path
            try:
                print(f"[Attempt {attempt + 1}] Getting ChromeDriver...")
                driver_path = ChromeDriverManager().install()
                print(f"[Attempt {attempt + 1}] ChromeDriver path: {driver_path}")
                
                # Verify the driver file exists and is valid
                if not os.path.exists(driver_path):
                    raise Exception(f"ChromeDriver not found at: {driver_path}")
                
                file_size = os.path.getsize(driver_path)
                print(f"[Attempt {attempt + 1}] ChromeDriver size: {file_size} bytes")
                
                if file_size < 1000:  # Too small, likely corrupted
                    print(f"[Attempt {attempt + 1}] ⚠ ChromeDriver file seems too small, may be corrupted")
                    # Try to clear cache and re-download
                    cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
                    if os.path.exists(cache_path):
                        print(f"[Attempt {attempt + 1}] Clearing ChromeDriver cache...")
                        import shutil
                        try:
                            shutil.rmtree(cache_path)
                            print(f"[Attempt {attempt + 1}] Cache cleared, re-downloading...")
                            driver_path = ChromeDriverManager().install()
                        except Exception as e:
                            print(f"[Attempt {attempt + 1}] Could not clear cache: {e}")
                
            except Exception as e:
                print(f"[Attempt {attempt + 1}] ⚠ ChromeDriverManager error: {e}")
                print(f"[Attempt {attempt + 1}] Trying to use system ChromeDriver...")
                driver_path = None  # Will try without explicit path
            
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
            
            # Try with explicit path first, then fallback
            try:
                if driver_path:
                    driver = webdriver.Chrome(service=Service(driver_path), options=options)
                else:
                    driver = webdriver.Chrome(options=options)
            except Exception as e:
                if "WinError 193" in str(e) or "not a valid Win32 application" in str(e):
                    print(f"[Attempt {attempt + 1}] ⚠ ChromeDriver architecture mismatch detected")
                    print(f"[Attempt {attempt + 1}] Trying to use system Chrome (chromedriver in PATH)...")
                    # Try without explicit service
                    try:
                        driver = webdriver.Chrome(options=options)
                    except Exception as e2:
                        raise Exception(f"Both ChromeDriverManager and system ChromeDriver failed. "
                                      f"ChromeDriverManager error: {e}. System error: {e2}")
                else:
                    raise
            
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            
            print(f"[Attempt {attempt + 1}] Navigating to: {badge_url}")
            driver.get(badge_url)
            
            wait = WebDriverWait(driver, 20)
            
            # Wait for badge element to ensure page is fully loaded
            print(f"[Attempt {attempt + 1}] Waiting for badge element...")
            try:
                badge_element = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//h1[contains(@class, "ac-heading--badge-name-hero")]')
                ))
                print(f"[Attempt {attempt + 1}] ✓ Badge element found")
                time.sleep(1)
                driver.execute_script("arguments[0].scrollIntoView(true);", badge_element)
                time.sleep(0.5)
            except TimeoutException:
                print(f"[Attempt {attempt + 1}] ⚠ Badge element not found, waiting for body...")
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                driver.execute_script("return document.readyState") == "complete"
                time.sleep(3)
            
            issue_date = ""
            
            # Method 1: XPath from reference file
            print(f"[Attempt {attempt + 1}] Trying Method 1: XPath for date element...")
            try:
                date_element = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[contains(@class, "badge-banner-issued-to-text")]/p[contains(text(), "Date issued:")]')
                ))
                if date_element:
                    driver.execute_script("arguments[0].scrollIntoView(true);", date_element)
                    time.sleep(0.3)
                    issue_date = date_element.text.replace("Date issued:", "").strip()
                    print(f"[Attempt {attempt + 1}] ✓ Method 1 found: '{issue_date}'")
            except (NoSuchElementException, TimeoutException) as e:
                print(f"[Attempt {attempt + 1}] ✗ Method 1 failed: {str(e)[:100]}")
            
            # Method 1b: Alternative XPaths
            if not issue_date:
                print(f"[Attempt {attempt + 1}] Trying Method 1b: Alternative XPaths...")
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
                                print(f"[Attempt {attempt + 1}] ✓ Method 1b found (xpath: {xpath[:50]}): '{issue_date}'")
                                break
                    except NoSuchElementException:
                        continue
            
            # Method 2: Following sibling approach
            if not issue_date:
                print(f"[Attempt {attempt + 1}] Trying Method 2: Following sibling...")
                try:
                    issue_date_element = driver.find_element(By.XPATH, '//div[text()="Date issued:"]/following-sibling::div[1]')
                    issue_date = issue_date_element.text.strip()
                    print(f"[Attempt {attempt + 1}] ✓ Method 2 found: '{issue_date}'")
                except NoSuchElementException:
                    print(f"[Attempt {attempt + 1}] ✗ Method 2 failed")
            
            # Method 3: Regex on page_source
            if not issue_date:
                print(f"[Attempt {attempt + 1}] Trying Method 3: Regex on page source...")
                page_source = driver.page_source
                
                # Debug: Check if "Date issued" exists
                if "Date issued" in page_source:
                    print(f"[Attempt {attempt + 1}] ✓ 'Date issued' found in page source")
                    # Find sample HTML around "Date issued"
                    sample_match = re.search(r'.{0,300}Date issued.{0,300}', page_source)
                    if sample_match:
                        sample = sample_match.group()
                        print(f"[Attempt {attempt + 1}] Sample HTML around 'Date issued':")
                        print(f"    {sample[:400]}")
                else:
                    print(f"[Attempt {attempt + 1}] ✗ 'Date issued' NOT found in page source")
                    # Try to find date-related text
                    date_related = re.search(r'.{0,300}(date|issued|completed).{0,300}', page_source, re.IGNORECASE)
                    if date_related:
                        print(f"[Attempt {attempt + 1}] Found date-related text:")
                        print(f"    {date_related.group()[:400]}")
                
                date_patterns = [
                    r"Date issued:\s*(\w+ \d{1,2}, \d{4})",
                    r"Date issued:\s*(\d{1,2}/\d{1,2}/\d{4})",
                    r"Date issued:\s*(\d{4}-\d{2}-\d{2})"
                ]
                for pattern in date_patterns:
                    matches = re.findall(pattern, page_source)
                    if matches:
                        issue_date = matches[0]
                        print(f"[Attempt {attempt + 1}] ✓ Method 3 (regex) found: '{issue_date}'")
                        break
                
                if not issue_date:
                    print(f"[Attempt {attempt + 1}] ✗ Method 3 failed - no regex matches")
            
            # Parse the date
            if issue_date:
                print(f"[Attempt {attempt + 1}] Parsing date: '{issue_date}'")
                date_obj, error = parse_date_string(issue_date)
                if date_obj:
                    print(f"[Attempt {attempt + 1}] ✓ Successfully parsed date: {date_obj}")
                    if driver:
                        driver.quit()
                    return date_obj, None
                else:
                    print(f"[Attempt {attempt + 1}] ✗ Failed to parse date: {error}")
                    if driver:
                        driver.quit()
                    return None, f"Could not parse extracted date: {issue_date}"
            else:
                print(f"[Attempt {attempt + 1}] ✗ All methods failed - no date extracted")
                # Save page source for debugging
                if driver:
                    page_source = driver.page_source
                    debug_file = f"credly_debug_{int(time.time())}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    print(f"[Attempt {attempt + 1}] Saved page source to: {debug_file}")
                    driver.quit()
                return None, "Could not extract date from Credly badge page"
                
        except (TimeoutException, WebDriverException) as e:
            print(f"[Attempt {attempt + 1}] ✗ Selenium error: {str(e)[:200]}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            if attempt < retries:
                wait_time = 2
                print(f"[Attempt {attempt + 1}] Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                return None, f"Selenium error after {retries + 1} attempts: {str(e)}"
        except Exception as e:
            print(f"[Attempt {attempt + 1}] ✗ Unexpected error: {str(e)[:200]}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return None, f"Unexpected error: {str(e)}"
    
    return None, "Failed to extract date after all retries"


def main():
    """Main test function"""
    if len(sys.argv) < 2:
        print("Usage: python test_credly_date_extraction.py <credly_badge_url>")
        print("\nExample:")
        print("  python test_credly_date_extraction.py https://www.credly.com/badges/abc123")
        print("\nTroubleshooting ChromeDriver issues:")
        print("  If you get 'WinError 193' or 'not a valid Win32 application':")
        print("  1. Make sure you have Google Chrome installed")
        print("  2. Try: pip install --upgrade webdriver-manager")
        print("  3. Clear cache: Delete ~/.wdm folder")
        print("  4. Or manually download ChromeDriver from https://chromedriver.chromium.org/")
        sys.exit(1)
    
    badge_url = sys.argv[1].strip()
    
    # Validate URL
    parsed = urlparse(badge_url)
    if 'credly.com' not in parsed.netloc:
        print(f"⚠ Warning: URL doesn't appear to be a Credly badge URL: {badge_url}")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    print("=" * 80)
    print("Credly Badge Date Extraction Test")
    print("=" * 80)
    print(f"URL: {badge_url}")
    print("=" * 80)
    
    date_obj, error = extract_credly_date_selenium(badge_url)
    
    print("\n" + "=" * 80)
    if date_obj:
        print(f"✓ SUCCESS: Extracted date: {date_obj}")
        print(f"  Date string: {date_obj.strftime('%B %d, %Y')}")
    else:
        print(f"✗ FAILED: {error}")
    print("=" * 80)


if __name__ == "__main__":
    main()


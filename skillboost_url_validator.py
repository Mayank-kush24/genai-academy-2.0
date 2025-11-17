import requests
import pandas as pd
import time
import random
import os
import logging
import sys
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Google Sheets logging imports
import gspread
from google.oauth2.service_account import Credentials

# Setup logging
def setup_logging(log_dir="logs"):
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    log_file = os.path.join(log_dir, f"skillboost_validator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configure handlers
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Set format for handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return log_file

def is_valid_google_skillboost_url(url, retries=3, timeout=5):
    """
    Validates if a URL is a valid Google Skillboost profile URL.
    Returns a tuple (is_valid, status_message).
    """
    # Handle empty or non-string URLs
    if not isinstance(url, str) or not url.strip():
        logging.warning(f"Received empty or non-string URL: {url}")
        return False, "Empty or Invalid URL"
    
    parsed_url = urlparse(url)
    
    # Log the URL being validated
    logging.info(f"Validating URL: {url}")
    
    # Check domain
    if parsed_url.netloc != "www.cloudskillsboost.google":
        logging.warning(f"Invalid domain for URL: {url}")
        return False, "Incorrect Domain"
    
    # Check path
    if not parsed_url.path.startswith("/public_profiles/"):
        logging.warning(f"Invalid path for URL: {url}")
        return False, "Incorrect Path"
    
    # Try to access the URL with retries
    for attempt in range(retries):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, timeout=timeout, headers=headers)
            
            logging.debug(f"Attempt {attempt+1}: URL {url} returned status code {response.status_code}")
            
            if response.status_code == 200 and "public_profiles" in response.url:
                logging.info(f"Validated URL successfully: {url}")
                return True, "Valid Profile"
            elif response.status_code == 429:
                # Handle rate limiting with exponential backoff
                wait_time = min(30, (2 ** attempt) * random.uniform(2, 5))
                logging.warning(f"Rate limited (429) for {url}. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                logging.warning(f"Invalid profile URL {url}: Status Code: {response.status_code}")
                return False, f"Invalid Profile (Status Code: {response.status_code})"
                
        except requests.RequestException as e:
            logging.error(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
            wait_time = min(30, (2 ** attempt) * random.uniform(1, 3))
            time.sleep(wait_time)  # Exponential backoff
    
    logging.error(f"Request failed after {retries} retries for URL: {url}")
    return False, "Request Failed After Retries"

def process_url(url_data):
    """Process a single URL with a random delay and return result details"""
    idx, url = url_data
    time.sleep(random.uniform(0.5, 2))
    
    try:
        valid, message = is_valid_google_skillboost_url(url)
        return idx, valid, message
    except Exception as e:
        logging.exception(f"Unexpected error processing URL {url}: {str(e)}")
        return idx, False, f"Processing Error: {str(e)}"

def append_log_to_google_sheet(log_row, credentials_file="google_credentials.json",
                               spreadsheet_id="YOUR_SPREADSHEET_ID", worksheet_name="Sheet1"):
    """
    Appends a log row to the specified Google Sheet.
    The log_row should be a list containing [Timestamp, Input file, Output file, Verified count, etc.].
    """
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        
        logging.info(f"Connecting to Google Sheets using credentials from {credentials_file}")
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        client = gspread.authorize(creds)
        
        # Open spreadsheet using its ID
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        # Append the log row to the worksheet
        worksheet.append_row(log_row)
        logging.info(f"Successfully appended log row to Google Sheet: {log_row}")
        return True
    
    except FileNotFoundError:
        logging.error(f"Credentials file not found: {credentials_file}")
        return False
    except Exception as e:
        logging.error(f"Failed to log to Google Sheet: {str(e)}")
        return False

def find_column_by_similar_name(df, column_names):
    """Find the most similar column name from the dataframe"""
    for possible_name in column_names:
        for col in df.columns:
            if possible_name.lower() in col.lower():
                return col
    return None

def ensure_output_directory(directory="output"):
    """Ensure the output directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created output directory: {directory}")
    return directory

def get_backup_filename(original_file):
    """Create a backup filename for the input file"""
    dirname, filename = os.path.split(original_file)
    name, ext = os.path.splitext(filename)
    backup_file = os.path.join(dirname, f"{name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
    return backup_file

def format_timestamp(timestamp_str):
    """Format ISO timestamp to YYYY-MM-DD HH:MM:SS format"""
    try:
        # Parse ISO format timestamp and return formatted string
        dt = pd.to_datetime(timestamp_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.warning(f"Failed to parse timestamp '{timestamp_str}': {str(e)}")
        return ""

def main():
    # Setup logging first
    log_file = setup_logging()
    
    try:
        # Default input file path
        default_input_file = r"D:\Genai_master_tracker_v2\Action_center\skillboost_profile\Share your Skills Boost public profile and get credits - 31-08-25.csv"
        
        # Allow command-line override
        input_file = sys.argv[1] if len(sys.argv) > 1 else default_input_file
        
        logging.info(f"Starting validation process for {input_file}")
        
        # Ensure the input file exists
        if not os.path.exists(input_file):
            logging.error(f"Input file not found: {input_file}")
            sys.exit(1)
        
        # Make a backup of the input file
        backup_file = get_backup_filename(input_file)
        try:
            import shutil
            shutil.copy2(input_file, backup_file)
            logging.info(f"Created backup of input file at {backup_file}")
        except Exception as e:
            logging.error(f"Failed to create backup: {str(e)}")
        
        # Read the input CSV file
        try:
            df = pd.read_csv(input_file)
            logging.info(f"Successfully read input file with {len(df)} rows")
        except Exception as e:
            logging.error(f"Failed to read input file: {str(e)}")
            sys.exit(1)
        
        # Print column names for debugging
        logging.info("Available columns in input file:")
        for col in df.columns:
            logging.info(f"  - {col}")
        
        # Define possible column mappings
        name_columns = ["Leader Name"]
        email_columns = ["Leader Email"]
        profile_columns = ["Share your Google Cloud Skills Boost public profile link"]
        timestamp_columns_updated = ["Timestamp (Updated At)"] 
        timestamp_columns_created = ["Timestamp (Created At)"] # Look for timestamp column (typically column B)
        
        # Find the best matching columns
        name_column = find_column_by_similar_name(df, name_columns)
        email_column = find_column_by_similar_name(df, email_columns)
        profile_column = find_column_by_similar_name(df, profile_columns)
        timestamp_column_updated = find_column_by_similar_name(df, timestamp_columns_updated)
        timestamp_column_created = find_column_by_similar_name(df, timestamp_columns_created)
        # Log column detection results
        if name_column:
            logging.info(f"Name column detected: '{name_column}'")
        else:
            logging.warning("Name column not found in the input file")
        
        if email_column:
            logging.info(f"Email column detected: '{email_column}'")
        else:
            logging.warning("Email column not found in the input file")
        
        if profile_column:
            logging.info(f"Profile link column detected: '{profile_column}'")
        else:
            logging.error("Couldn't find the profile link column in the input file")
            sys.exit(1)
            
        if timestamp_column_updated:
            logging.info(f"Timestamp column detected: '{timestamp_column_updated}'")
        else:
            logging.warning("Timestamp column not found in the input file")


        if timestamp_column_created:
            logging.info(f"Timestamp column detected: '{timestamp_column_created}'")
        else:
            logging.warning("Timestamp column not found in the input file")
        
        # Validate URLs in parallel with proper tracking
        urls = df[profile_column].tolist()
        logging.info(f"Starting validation of {len(urls)} URLs...")
        
        # Create a list of (index, url) tuples
        url_data = list(enumerate(urls))
        
        # Processing configuration
        max_workers = min(10, len(urls))  # Limit number of workers
        chunk_size = 50                   # Process in chunks for better logging
        
        # Process in chunks to avoid overwhelming resources
        results = [None] * len(urls)
        status_messages = [None] * len(urls)
        
        for i in range(0, len(url_data), chunk_size):
            chunk = url_data[i:i+chunk_size]
            logging.info(f"Processing chunk {i//chunk_size + 1}/{(len(url_data) + chunk_size - 1)//chunk_size} ({len(chunk)} URLs)")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                chunk_results = list(executor.map(process_url, chunk))
            
            # Store results at the correct indices
            for idx, valid, message in chunk_results:
                results[idx] = valid
                status_messages[idx] = message
            
            # Add a small delay between chunks
            time.sleep(2)
        
        # Add validation results to the dataframe
        df["Isverified"] = ["TRUE" if valid else "FALSE" for valid in results]
        df["Verification_status"] = status_messages
        df["Verification_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Define the output columns in the specified order
        output_columns = [
            "Name",
            "Email",
            "Occupation",
            "Skillboost public view link",
            "Isverified",
            "Verification_status", 
            "Verification_timestamp",
            "Created_at",
            "Updated_at",
            "credits_remark"  # New column for the formatted timestamp from column B
            
        ]
        
        # Create a new DataFrame with these columns
        new_df = pd.DataFrame(columns=output_columns)
        
        # Populate the new DataFrame
        for idx, row in df.iterrows():
            new_row = {}
            
            # Map name from detected name column
            if name_column:
                new_row["Name"] = row[name_column]
            else:
                new_row["Name"] = ""
            
            # Map email from detected email column
            if email_column:
                new_row["Email"] = row[email_column]
            else:
                new_row["Email"] = ""
            
            # Map profile link and verification status
            new_row["Skillboost public view link"] = row[profile_column] if profile_column in row else ""
            new_row["Isverified"] = row["Isverified"] if "Isverified" in row else ""
            new_row["Verification_status"] = row["Verification_status"] if "Verification_status" in row else ""
            new_row["Verification_timestamp"] = row["Verification_timestamp"] if "Verification_timestamp" in row else ""

            
            if new_row["Isverified"] == "TRUE":
                new_row["credits_remark"] = "Complete two free courses and submit them to claim credits"
            else:
                new_row["credits_remark"] = ""

            
            # Add the formatted timestamp from column B
            if timestamp_column_updated and timestamp_column_updated in row:
                new_row["Updated_at"] = format_timestamp(row[timestamp_column_updated])
            else:
                new_row["Updated_at"] = ""

            if timestamp_column_created and timestamp_column_created in row:
                new_row["Created_at"] = format_timestamp(row[timestamp_column_created])
            else:
                new_row["Created_at"] = ""
            
            # Map other columns or initialize them as empty
            for col in output_columns:
                if col not in new_row:
                    if col in row:
                        new_row[col] = row[col]
                    else:
                        new_row[col] = ""
            
            new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Create output directory if it doesn't exist
        output_dir = ensure_output_directory()
        
        # Create output filename with current date and time
        current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"verification_results_{current_datetime}.csv")
        
        # Save to CSV with error handling
        try:
            new_df.to_csv(output_file, index=False)
            logging.info(f"Validation results saved as {output_file}")
        except Exception as e:
            logging.error(f"Failed to save output file: {str(e)}")
            # Try to save to a different location
            alt_output = f"verification_results_{current_datetime}.csv"
            try:
                new_df.to_csv(alt_output, index=False)
                logging.info(f"Saved results to alternate location: {alt_output}")
                output_file = alt_output
            except Exception as e2:
                logging.error(f"Also failed to save to alternate location: {str(e2)}")
        
        # Print summary statistics
        verified_count = (new_df["Isverified"] == "TRUE").sum()
        not_verified_count = (new_df["Isverified"] == "FALSE").sum()
        
        summary = f"\nValidation summary:\n"
        summary += f"  Verified profiles: {verified_count}\n"
        summary += f"  Failed profiles: {not_verified_count}\n"
        summary += f"  Total processed: {len(new_df)}\n"
        summary += f"  Success rate: {verified_count/len(new_df)*100:.2f}%"
        
        logging.info(summary)
        
        # Group by verification status
        status_counts = {}
        for status in status_messages:
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
        
        logging.info("Breakdown by verification status:")
        for status, count in status_counts.items():
            logging.info(f"  {status}: {count}")
        
        # Log summary details to Google Sheet by appending a row
        log_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_row = [
            log_timestamp,
            input_file,
            output_file,
            str(verified_count),
            str(not_verified_count),
            f"{verified_count/len(new_df)*100:.2f}%",
            log_file  # Include path to log file
        ]
        
        credentials_file = r"D:\Gen-ai_master_tracker\vision-playground-423507-d37e0741a307.json"
        spreadsheet_id = "1UIVQ1KA91QpvcPFK6Aoc6JnaddZc5xLO5GYHGjISni4"
        
        # Log to Google Sheet with error handling
        sheet_log_success = append_log_to_google_sheet(
            log_row,
            credentials_file=credentials_file,
            spreadsheet_id=spreadsheet_id,
            worksheet_name="Sheet1"
        )
        
        if not sheet_log_success:
            logging.warning("Failed to log to Google Sheet - check the log for details")
        
        logging.info("Validation process completed successfully")
        return 0
    
    except Exception as e:
        logging.exception(f"Unhandled exception in main process: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
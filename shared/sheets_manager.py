"""
Google Sheets management with smart validation for all export types
"""

import pandas as pd
import gspread
import logging
import time
import random
import requests
from google.oauth2.service_account import Credentials
from .data_validator import DataValidator
from .config import ExportConfig

class SheetsManager:
    """Manages Google Sheets operations with smart validation"""
    
    def __init__(self, export_type: str):
        self.export_type = export_type
        self.export_config = ExportConfig.get_export_config(export_type)
        self.logger = logging.getLogger(__name__)

        # Get retry configuration
        self.retry_config = ExportConfig.GOOGLE_SHEETS_RETRY_CONFIG

        # Initialize Google Sheets client
        self._setup_google_client()
    
    def _setup_google_client(self):
        """Setup Google Sheets API client using environment variable or file"""
        import os

        # TEMPORARY: Skip Google Sheets setup to test backend automation
        if os.getenv('SKIP_GOOGLE_SHEETS') == 'true':
            self.logger.info(f"TEMPORARY: Skipping Google Sheets setup for {self.export_config['name']} - backend testing mode")
            self.gc = None
            return

        try:
            # Get service account info (supports both environment variable and file)
            service_account_info = ExportConfig.get_service_account_info()

            # Create credentials from the service account info
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=ExportConfig.GOOGLE_API_SCOPES
            )
            self.gc = gspread.authorize(credentials)
            self.logger.info(f"Google Sheets client initialized for {self.export_config['name']} (credentials from {'environment' if 'GOOGLE_SERVICE_ACCOUNT_JSON' in __import__('os').environ else 'file'})")
        except Exception as e:
            self.logger.error(f"Failed to setup Google Sheets client: {str(e)}")
            raise

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff with optional jitter"""
        base_delay = self.retry_config["base_delay"]
        exponential_base = self.retry_config["exponential_base"]
        max_delay = self.retry_config["max_delay"]

        # Calculate exponential backoff delay
        delay = base_delay * (exponential_base ** attempt)
        delay = min(delay, max_delay)

        # Add jitter if enabled
        if self.retry_config["jitter"]:
            # Add random jitter ±25% of the delay
            jitter = delay * 0.25 * (2 * random.random() - 1)
            delay += jitter

        return max(0, delay)

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable based on configuration"""
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            return error.response.status_code in self.retry_config["retry_status_codes"]

        # Check for specific gspread errors that indicate temporary issues
        error_str = str(error).lower()
        retryable_errors = [
            'service unavailable',
            'temporarily unavailable',
            'rate limit exceeded',
            'quota exceeded',
            'internal error',
            'timeout',
            'connection error',
            'temporary failure'
        ]

        return any(retryable_msg in error_str for retryable_msg in retryable_errors)

    def _execute_with_retry(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute a Google Sheets operation with retry mechanism"""
        max_retries = self.retry_config["max_retries"]

        for attempt in range(max_retries + 1):
            try:
                # Add rate limiting delay before each API call
                if attempt > 0:
                    delay = self._calculate_retry_delay(attempt - 1)
                    self.logger.info(f"{operation_name}: Attempt {attempt + 1}/{max_retries + 1} after {delay:.2f}s delay")
                    time.sleep(delay)
                else:
                    # Small delay even on first attempt to prevent rate limiting
                    time.sleep(self.retry_config["rate_limit_delay"])

                # Execute the operation
                result = operation_func(*args, **kwargs)

                if attempt > 0:
                    self.logger.info(f"{operation_name}: Succeeded on attempt {attempt + 1}")

                return result

            except Exception as e:
                is_last_attempt = attempt == max_retries
                is_retryable = self._is_retryable_error(e)

                self.logger.warning(f"{operation_name}: Attempt {attempt + 1} failed: {str(e)}")

                if is_last_attempt or not is_retryable:
                    if is_last_attempt and is_retryable:
                        self.logger.error(f"{operation_name}: All {max_retries + 1} attempts failed. Last error: {str(e)}")
                    else:
                        self.logger.error(f"{operation_name}: Non-retryable error: {str(e)}")
                    raise

                self.logger.info(f"{operation_name}: Retryable error detected, will retry...")

        # This should never be reached, but just in case
        raise Exception(f"{operation_name}: Unexpected retry loop exit")
    
    def upload_with_smart_validation(self, file_path, use_smart_validation=True):
        """Upload data with smart validation and duplicate detection"""
        self.logger.info(f"Uploading {self.export_config['name']} with smart validation...")

        # TEMPORARY: Skip Google Sheets upload to test backend automation
        import os
        if os.getenv('SKIP_GOOGLE_SHEETS') == 'true':
            self.logger.info(f"TEMPORARY: Skipping Google Sheets upload for {self.export_config['name']} - backend testing mode")
            self.logger.info(f"File downloaded successfully: {file_path}")
            # Verify file exists and get record count
            from pathlib import Path
            if Path(file_path).exists():
                file_size = Path(file_path).stat().st_size
                self.logger.info(f"✅ SUCCESS: Downloaded {file_size} bytes to {file_path}")

                # Get record count from file
                try:
                    df = pd.read_excel(file_path)
                    record_count = len(df)
                    self.logger.info(f"File contains {record_count} data rows")
                    return {"success": True, "records": record_count}
                except Exception as e:
                    self.logger.warning(f"Could not count records in file: {e}")
                    return {"success": True, "records": 0}
            else:
                self.logger.error(f"❌ FAILED: File not found at {file_path}")
                return {"success": False, "records": 0}

        try:
            # Open Google Sheet with retry mechanism
            sheet = self._execute_with_retry(
                "Open Google Sheet",
                lambda: self.gc.open_by_url(self.export_config["google_sheet_url"]).sheet1
            )
            
            # Read Excel file
            new_df = pd.read_excel(file_path)
            
            # Debug file content
            self.logger.info(f"File analysis: {len(new_df)} rows, {len(new_df.columns)} columns")
            if len(new_df.columns) > 0:
                self.logger.info(f"Column names: {list(new_df.columns)}")
            if len(new_df) > 0:
                self.logger.info(f"First row sample: {new_df.iloc[0].to_dict() if len(new_df) > 0 else 'No data rows'}")
            else:
                self.logger.warning("DataFrame has no data rows - only headers or completely empty")
            
            # Enhanced empty data handling with better validation
            if new_df.empty or len(new_df) == 0:
                if len(new_df.columns) > 0:
                    # File has headers but no data - this is valid (no transactions for this date)
                    self.logger.info(f"HEADERS ONLY: {self.export_config['name']} - no data for this date range (valid state)")
                    self.logger.info(f"Header columns found: {list(new_df.columns)}")
                    return {"success": True, "records": 0}  # Treat as successful - no data to upload
                else:
                    # Completely empty file - this is an error
                    self.logger.error(f"CRITICAL ERROR: File is completely empty (no headers or data) for {self.export_config['name']}")
                    raise Exception("Downloaded file is completely empty (no headers or data)!")
            
            self.logger.info(f"New data loaded: {len(new_df)} rows, {len(new_df.columns)} columns")
            
            # Clean data for JSON compliance
            new_df = self._clean_data_for_json(new_df)
            
            if use_smart_validation:
                # Initialize data validator with export-specific unique key and composite columns
                unique_key = self.export_config.get("unique_key", "ID")
                composite_key_columns = self.export_config.get("composite_key_columns", None)
                validator = DataValidator(unique_key=unique_key, composite_key_columns=composite_key_columns)
                
                # Read existing sheet data with retry mechanism
                existing_df = self._execute_with_retry(
                    "Read existing sheet data",
                    lambda: validator.read_existing_sheet_data(sheet)
                )
                
                if not existing_df.empty:
                    # Prepare smart upload data
                    upload_plan = validator.prepare_smart_upload_data(
                        new_df, existing_df, handle_duplicates="skip"
                    )
                    
                    # Log upload plan
                    self.logger.info("Smart upload plan:")
                    for operation in upload_plan["operations"]:
                        self.logger.info(f"  - {operation}")
                    
                    # Execute smart upload with retry mechanism
                    self._execute_with_retry(
                        "Execute smart upload",
                        lambda: self._execute_smart_upload(sheet, upload_plan, existing_df)
                    )
                else:
                    # Empty sheet - do normal upload
                    self.logger.info("Sheet is empty - performing initial upload")
                    self._execute_with_retry(
                        "Initial upload to empty sheet",
                        lambda: self._upload_all_data(sheet, new_df)
                    )
            else:
                # SAFETY CHANGE: Warn before destructive operation
                self.logger.warning("DESTRUCTIVE MODE: This will clear all existing data!")
                self.logger.warning("Consider using smart validation to preserve data")
                # Only proceed if explicitly requested (this should be rare in production)
                self._execute_with_retry(
                    "Clear sheet (destructive)",
                    lambda: sheet.clear()
                )
                self._execute_with_retry(
                    "Upload all data (destructive)",
                    lambda: self._upload_all_data(sheet, new_df)
                )
            
            self.logger.info(f"Data uploaded to Google Sheets successfully for {self.export_config['name']}!")
            return {"success": True, "records": len(new_df)}

        except Exception as e:
            self.logger.error(f"Google Sheets upload failed for {self.export_config['name']}: {str(e)}")
            # CRITICAL FIX: Do NOT use destructive fallback to prevent data loss
            if use_smart_validation:
                self.logger.error("SMART VALIDATION FAILED - Preserving existing data to prevent data loss")
                self.logger.error("Manual intervention required - check logs and retry manually")
                # Return failure status instead of wiping data
                return {"success": False, "records": 0, "error": str(e)}
            else:
                raise
    
    def _clean_data_for_json(self, df):
        """Clean dataframe for JSON compliance"""
        # Replace NaN, inf, -inf values
        df = df.fillna('')  # Replace NaN with empty string
        df = df.replace([float('inf'), float('-inf')], '')  # Replace inf values
        
        # Convert problematic numeric columns to strings
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            df[col] = df[col].astype(str).replace('nan', '').replace('inf', '').replace('-inf', '')
        
        return df
    
    def _upload_all_data(self, sheet, df):
        """Upload all data to sheet (original method) with built-in rate limiting"""
        # Check and expand sheet if needed before uploading
        total_rows_needed = len(df) + 1  # +1 for header
        self.logger.info(f"Checking sheet capacity for {total_rows_needed} total rows...")
        self._check_and_expand_sheet_if_needed(sheet, total_rows_needed)

        data_to_upload = [df.columns.values.tolist()] + df.values.tolist()

        if len(data_to_upload) > 1000:
            self.logger.info("Large dataset detected, uploading in batches...")
            # Upload headers with rate limiting delay
            sheet.update('A1', [data_to_upload[0]])
            time.sleep(self.retry_config["batch_delay"])

            # Upload in chunks with rate limiting
            chunk_size = 1000
            for i in range(1, len(data_to_upload), chunk_size):
                chunk = data_to_upload[i:i+chunk_size]
                range_name = f'A{i+1}'
                sheet.update(range_name, chunk)
                self.logger.info(f"Uploaded chunk {i//chunk_size + 1}")
                time.sleep(self.retry_config["batch_delay"])  # Enhanced rate limiting for batches
        else:
            sheet.update('A1', data_to_upload)
    
    def _execute_smart_upload(self, sheet, upload_plan, existing_df):
        """Execute smart upload plan"""
        # Check and expand sheet if needed before uploading
        total_new_rows = len(upload_plan["append_data"]) if not upload_plan["append_data"].empty else 0
        if total_new_rows > 0:
            self.logger.info(f"Checking sheet capacity for {total_new_rows} new rows...")
            self._check_and_expand_sheet_if_needed(sheet, total_new_rows)

        # Append new records
        if not upload_plan["append_data"].empty:
            self.logger.info(f"Appending {len(upload_plan['append_data'])} new records...")

            # Find the last row with data
            last_row = len(existing_df) + 2  # +1 for header, +1 for next row

            # Append new data
            new_data_values = upload_plan["append_data"].values.tolist()
            if new_data_values:
                range_name = f'A{last_row}'
                sheet.update(range_name, new_data_values)
                time.sleep(self.retry_config["rate_limit_delay"])  # Rate limiting between operations
        
        # Update existing records (simplified - just log for now)
        if not upload_plan["update_data"].empty:
            self.logger.info(f"Found {len(upload_plan['update_data'])} records to update")
            self.logger.info("Note: Individual row updates not implemented yet - consider re-running with fresh data")
        
        # Log skipped records
        if not upload_plan["skip_data"].empty:
            self.logger.info(f"Skipped {len(upload_plan['skip_data'])} unchanged records")
        
        self.logger.info("Smart upload completed!")

    def _check_and_expand_sheet_if_needed(self, sheet, data_rows_to_add):
        """Check if sheet has enough space and expand if needed"""
        try:
            # Get current sheet properties
            spreadsheet = sheet.spreadsheet
            worksheet_properties = None

            # Find the current worksheet properties
            for ws in spreadsheet.worksheets():
                if ws.id == sheet.id:
                    worksheet_properties = {
                        'sheetId': sheet.id,
                        'gridProperties': {
                            'rowCount': ws.row_count,
                            'columnCount': ws.col_count
                        }
                    }
                    break

            if not worksheet_properties:
                self.logger.warning("Could not get worksheet properties")
                return False

            current_rows = worksheet_properties['gridProperties']['rowCount']
            current_cols = worksheet_properties['gridProperties']['columnCount']

            # Check how many rows we have data in
            all_values = sheet.get_all_values()
            used_rows = len([row for row in all_values if any(cell.strip() for cell in row)])

            # Calculate space needed (with buffer)
            space_needed = used_rows + data_rows_to_add + 100  # Add 100 row buffer

            self.logger.info(f"Sheet capacity check: {used_rows} used rows, {current_rows} total rows, need space for {data_rows_to_add} new rows")

            if space_needed > current_rows:
                # Need to expand the sheet
                new_row_count = max(space_needed, current_rows * 2)  # At least double current size
                new_row_count = min(new_row_count, 10000000)  # Google Sheets limit is 10M cells

                self.logger.info(f"Expanding sheet from {current_rows} to {new_row_count} rows")

                # Prepare the expansion request
                expansion_request = {
                    'requests': [{
                        'updateSheetProperties': {
                            'properties': {
                                'sheetId': sheet.id,
                                'gridProperties': {
                                    'rowCount': new_row_count,
                                    'columnCount': current_cols
                                }
                            },
                            'fields': 'gridProperties.rowCount'
                        }
                    }]
                }

                # Execute the expansion with retry
                self._execute_with_retry(
                    "Expand sheet rows",
                    lambda: spreadsheet.batch_update(expansion_request)
                )

                self.logger.info(f"✅ Sheet expanded successfully to {new_row_count} rows")
                return True
            else:
                self.logger.info("Sheet has sufficient space - no expansion needed")
                return True

        except Exception as e:
            self.logger.error(f"Failed to check/expand sheet: {str(e)}")
            # Don't fail the upload for expansion issues - try to continue
            return False

    def get_sheet_info(self):
        """Get basic information about the Google Sheet with retry mechanism"""
        try:
            # Open sheet with retry
            sheet = self._execute_with_retry(
                "Open sheet for info",
                lambda: self.gc.open_by_url(self.export_config["google_sheet_url"]).sheet1
            )

            # Get all records with retry
            all_records = self._execute_with_retry(
                "Get all sheet records",
                lambda: sheet.get_all_records()
            )

            info = {
                "title": sheet.title,
                "rows": len(all_records),
                "columns": len(all_records[0]) if all_records else 0,
                "last_updated": "N/A"  # Could add timestamp tracking later
            }

            self.logger.info(f"Sheet info for {self.export_config['name']}: {info}")
            return info

        except Exception as e:
            self.logger.error(f"Failed to get sheet info: {str(e)}")
            return None
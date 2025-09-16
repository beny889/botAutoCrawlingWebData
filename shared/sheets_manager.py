"""
Google Sheets management with smart validation for all export types
"""

import pandas as pd
import gspread
import logging
import time
from google.oauth2.service_account import Credentials
from .data_validator import DataValidator
from .config import ExportConfig

class SheetsManager:
    """Manages Google Sheets operations with smart validation"""
    
    def __init__(self, export_type: str):
        self.export_type = export_type
        self.export_config = ExportConfig.get_export_config(export_type)
        self.logger = logging.getLogger(__name__)
        
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
                    import pandas as pd
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
            # Open Google Sheet
            sheet = self.gc.open_by_url(self.export_config["google_sheet_url"]).sheet1
            
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
                    return True  # Treat as successful - no data to upload
                else:
                    # Completely empty file - this is an error
                    self.logger.error(f"CRITICAL ERROR: File is completely empty (no headers or data) for {self.export_config['name']}")
                    raise Exception("Downloaded file is completely empty (no headers or data)!")
            
            self.logger.info(f"New data loaded: {len(new_df)} rows, {len(new_df.columns)} columns")
            
            # Clean data for JSON compliance
            new_df = self._clean_data_for_json(new_df)
            
            if use_smart_validation:
                # Initialize data validator with export-specific unique key
                unique_key = self.export_config.get("unique_key", "ID")
                validator = DataValidator(unique_key=unique_key)
                
                # Read existing sheet data
                existing_df = validator.read_existing_sheet_data(sheet)
                
                if not existing_df.empty:
                    # Prepare smart upload data
                    upload_plan = validator.prepare_smart_upload_data(
                        new_df, existing_df, handle_duplicates="skip"
                    )
                    
                    # Log upload plan
                    self.logger.info("Smart upload plan:")
                    for operation in upload_plan["operations"]:
                        self.logger.info(f"  - {operation}")
                    
                    # Execute smart upload
                    self._execute_smart_upload(sheet, upload_plan, existing_df)
                else:
                    # Empty sheet - do normal upload
                    self.logger.info("Sheet is empty - performing initial upload")
                    self._upload_all_data(sheet, new_df)
            else:
                # Fallback to original method
                self.logger.info("Using original upload method (destructive)")
                sheet.clear()
                self._upload_all_data(sheet, new_df)
            
            self.logger.info(f"Data uploaded to Google Sheets successfully for {self.export_config['name']}!")
            
        except Exception as e:
            self.logger.error(f"Google Sheets upload failed for {self.export_config['name']}: {str(e)}")
            # Fallback to original method if smart upload fails
            if use_smart_validation:
                self.logger.info("Falling back to original upload method...")
                self.upload_with_smart_validation(file_path, use_smart_validation=False)
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
        """Upload all data to sheet (original method)"""
        data_to_upload = [df.columns.values.tolist()] + df.values.tolist()
        
        if len(data_to_upload) > 1000:
            self.logger.info("Large dataset detected, uploading in batches...")
            # Upload headers
            sheet.update('A1', [data_to_upload[0]])
            
            # Upload in chunks
            chunk_size = 1000
            for i in range(1, len(data_to_upload), chunk_size):
                chunk = data_to_upload[i:i+chunk_size]
                range_name = f'A{i+1}'
                sheet.update(range_name, chunk)
                self.logger.info(f"Uploaded chunk {i//chunk_size + 1}")
                time.sleep(1)  # Rate limiting
        else:
            sheet.update('A1', data_to_upload)
    
    def _execute_smart_upload(self, sheet, upload_plan, existing_df):
        """Execute smart upload plan"""
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
                time.sleep(1)
        
        # Update existing records (simplified - just log for now)
        if not upload_plan["update_data"].empty:
            self.logger.info(f"Found {len(upload_plan['update_data'])} records to update")
            self.logger.info("Note: Individual row updates not implemented yet - consider re-running with fresh data")
        
        # Log skipped records
        if not upload_plan["skip_data"].empty:
            self.logger.info(f"Skipped {len(upload_plan['skip_data'])} unchanged records")
        
        self.logger.info("Smart upload completed!")
    
    def get_sheet_info(self):
        """Get basic information about the Google Sheet"""
        try:
            sheet = self.gc.open_by_url(self.export_config["google_sheet_url"]).sheet1
            all_records = sheet.get_all_records()
            
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
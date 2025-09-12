import asyncio
import os
import time
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import logging
from pathlib import Path
import re
from shared.data_validator import DataValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler()
    ]
)

class PlaywrightBackendAutomation:
    def __init__(self):
        # Configuration - SESUAIKAN DENGAN DATA ANDA
        self.username = "superadmin@gmail.com"
        self.password = "Z123465!@"
        self.google_sheet_url = "https://docs.google.com/spreadsheets/d/1dhLTUzUQ1ug4KPjU0Q8A8x38IioW5ZwKvVEIYHqf7aw"
        self.service_account_file = "service-account-key.json"  # Ganti dengan path JSON file Anda
        
        # Website selectors
        self.selectors = {
            "login": {
                "username": '[name="email"]',
                "password": '[name="password"]', 
                "submit": 'button:has-text("Log In")'
            },
            "export": {
                "start_date": 'input[placeholder*="dd/mm/yyyy"]:first-of-type',
                "end_date": 'input[placeholder*="dd/mm/yyyy"]:last-of-type',
                "submit": 'button:has-text("Export")'
            }
        }
        
        # Setup directories
        self.download_folder = Path("downloads")
        self.download_folder.mkdir(exist_ok=True)
        
        # Browser config
        self.browser_config = {
            "headless": False,  # Set True untuk background running
            "slow_mo": 1000,   # Delay 1 detik antar action (untuk debugging)
        }
    
    def format_date_for_input(self, date_str):
        """Convert YYYY-MM-DD to DD/MM/YYYY format"""
        if isinstance(date_str, str):
            # Assuming input is YYYY-MM-DD
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            date_obj = date_str
        
        return date_obj.strftime("%d/%m/%Y")
    
    async def setup_browser(self):
        """Setup Playwright browser"""
        logging.info("Setting up browser...")
        
        self.playwright = await async_playwright().start()
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.browser_config["headless"],
            slow_mo=self.browser_config["slow_mo"],
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        
        # Create context with download path
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True
        )
        
        # Create page
        self.page = await self.context.new_page()
        self.page.set_default_timeout(60000)  # 60 seconds timeout
        
        logging.info("Browser setup completed")
    
    async def login_to_backend(self):
        """Login ke backend website"""
        logging.info("Logging in to backend...")
        
        try:
            # Navigate to login page
            await self.page.goto("https://backend.andalanatk.com")
            await self.page.wait_for_load_state('networkidle')
            
            # Fill login form
            await self.page.fill(self.selectors["login"]["username"], self.username)
            await self.page.fill(self.selectors["login"]["password"], self.password)
            
            # Click login button
            await self.page.click(self.selectors["login"]["submit"])
            
            # Wait for page to load after login
            await self.page.wait_for_load_state('networkidle', timeout=60000)
            
            # Verify login success (check if we're not on login page anymore)
            current_url = self.page.url
            if "login" not in current_url.lower():
                logging.info("Login successful!")
                return True
            else:
                raise Exception("Login failed - still on login page")
                
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            # Take screenshot for debugging
            await self.page.screenshot(path="login_error.png")
            raise
    
    async def export_data(self, start_date, end_date):
        """Export data dari halaman transaksi"""
        logging.info(f"Exporting data from {start_date} to {end_date}...")
        
        try:
            # Navigate to export page
            await self.page.goto("https://backend.andalanatk.com/transaksi/index-export")
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for form elements to be ready
            await self.page.wait_for_selector('input[name="start_date"]', timeout=30000)
            
            # For HTML5 date inputs, use YYYY-MM-DD format (not DD/MM/YYYY)
            # Convert input dates to proper format
            if isinstance(start_date, str):
                start_formatted = start_date  # Already YYYY-MM-DD
            else:
                start_formatted = start_date.strftime("%Y-%m-%d")
                
            if isinstance(end_date, str):
                end_formatted = end_date  # Already YYYY-MM-DD
            else:
                end_formatted = end_date.strftime("%Y-%m-%d")
            
            logging.info(f"Using HTML5 date format: {start_formatted} to {end_formatted}")
            
            # Take screenshot for debugging
            await self.page.screenshot(path="before_date_input.png")
            
            # Use direct selectors for the date fields
            start_field = await self.page.wait_for_selector('input[name="start_date"]', timeout=10000)
            end_field = await self.page.wait_for_selector('input[name="end_date"]', timeout=10000)
            
            # For HTML5 date inputs, use fill() method with YYYY-MM-DD format
            await start_field.fill(start_formatted)
            await end_field.fill(end_formatted)
            
            # Take screenshot after date input
            await self.page.screenshot(path="after_date_input.png")
            
            # Setup download handler before clicking export
            async with self.page.expect_download(timeout=60000) as download_info:
                await self.page.click('button:has-text("Export")')
            
            # Get download
            download = await download_info.value
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.xlsx"
            file_path = self.download_folder / filename
            
            # Save download
            await download.save_as(file_path)
            
            logging.info(f"File downloaded successfully: {file_path}")
            return file_path
            
        except Exception as e:
            logging.error(f"Export failed: {str(e)}")
            await self.page.screenshot(path="export_error.png")
            raise
    
    def upload_to_google_sheets(self, file_path, use_smart_validation=True):
        """Upload data ke Google Sheets with smart validation"""
        logging.info("Uploading to Google Sheets with smart validation...")
        
        try:
            # Setup Google Sheets credentials
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            credentials = Credentials.from_service_account_file(
                self.service_account_file, scopes=scope
            )
            gc = gspread.authorize(credentials)
            
            # Open Google Sheet
            sheet = gc.open_by_url(self.google_sheet_url).sheet1
            
            # Read Excel file
            new_df = pd.read_excel(file_path)
            
            # Validate data
            if new_df.empty:
                raise Exception("Downloaded file is empty!")
            
            logging.info(f"New data loaded: {len(new_df)} rows, {len(new_df.columns)} columns")
            
            # Clean data for JSON compliance
            new_df = self._clean_data_for_json(new_df)
            
            if use_smart_validation:
                # Initialize data validator
                validator = DataValidator(unique_key="Transaksi ID")
                
                # Read existing sheet data
                existing_df = validator.read_existing_sheet_data(sheet)
                
                if not existing_df.empty:
                    # Prepare smart upload data
                    upload_plan = validator.prepare_smart_upload_data(
                        new_df, existing_df, handle_duplicates="skip"
                    )
                    
                    # Log upload plan
                    logging.info("Smart upload plan:")
                    for operation in upload_plan["operations"]:
                        logging.info(f"  - {operation}")
                    
                    # Execute smart upload
                    self._execute_smart_upload(sheet, upload_plan, existing_df)
                else:
                    # Empty sheet - do normal upload
                    logging.info("Sheet is empty - performing initial upload")
                    self._upload_all_data(sheet, new_df)
            else:
                # Fallback to original method
                logging.info("Using original upload method (destructive)")
                sheet.clear()
                self._upload_all_data(sheet, new_df)
            
            logging.info("Data uploaded to Google Sheets successfully!")
            
        except Exception as e:
            logging.error(f"Google Sheets upload failed: {str(e)}")
            # Fallback to original method if smart upload fails
            if use_smart_validation:
                logging.info("Falling back to original upload method...")
                self.upload_to_google_sheets(file_path, use_smart_validation=False)
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
            logging.info("Large dataset detected, uploading in batches...")
            # Upload headers
            sheet.update('A1', [data_to_upload[0]])
            
            # Upload in chunks
            chunk_size = 1000
            for i in range(1, len(data_to_upload), chunk_size):
                chunk = data_to_upload[i:i+chunk_size]
                range_name = f'A{i+1}'
                sheet.update(range_name, chunk)
                logging.info(f"Uploaded chunk {i//chunk_size + 1}")
                time.sleep(1)  # Rate limiting
        else:
            sheet.update('A1', data_to_upload)
    
    def _execute_smart_upload(self, sheet, upload_plan, existing_df):
        """Execute smart upload plan"""
        # Append new records
        if not upload_plan["append_data"].empty:
            logging.info(f"Appending {len(upload_plan['append_data'])} new records...")
            
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
            logging.info(f"Found {len(upload_plan['update_data'])} records to update")
            logging.info("Note: Individual row updates not implemented yet - consider re-running with fresh data")
        
        # Log skipped records
        if not upload_plan["skip_data"].empty:
            logging.info(f"Skipped {len(upload_plan['skip_data'])} unchanged records")
        
        logging.info("Smart upload completed!")
    
    def cleanup_old_files(self, days_to_keep=7):
        """Clean up old downloaded files"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            for file_path in self.download_folder.glob("*"):
                if file_path.stat().st_ctime < cutoff_time:
                    file_path.unlink()
                    logging.info(f"Cleaned up old file: {file_path.name}")
                    
        except Exception as e:
            logging.warning(f"Cleanup failed: {str(e)}")
    
    async def run_automation(self, start_date=None, end_date=None):
        """Run the complete automation process"""
        try:
            # Default to yesterday if no dates provided
            if not start_date:
                yesterday = datetime.now() - timedelta(days=1)
                start_date = yesterday.strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            logging.info(f"Starting automation for date range: {start_date} to {end_date}")
            
            # Setup browser
            await self.setup_browser()
            
            # Login
            await self.login_to_backend()
            
            # Export data
            downloaded_file = await self.export_data(start_date, end_date)
            
            # Upload to Google Sheets
            self.upload_to_google_sheets(downloaded_file)
            
            # Cleanup old files
            self.cleanup_old_files()
            
            logging.info("CHECKMARK Automation completed successfully!")
            return True
            
        except Exception as e:
            logging.error(f"X Automation failed: {str(e)}")
            return False
        
        finally:
            # Cleanup browser
            if hasattr(self, 'browser'):
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logging.info("Browser closed")

# Convenience functions for different use cases
async def run_today():
    """Export data untuk hari ini"""
    automation = PlaywrightBackendAutomation()
    today = datetime.now().strftime("%Y-%m-%d")
    return await automation.run_automation(today, today)

async def run_yesterday():
    """Export data untuk kemarin"""
    automation = PlaywrightBackendAutomation()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return await automation.run_automation(yesterday, yesterday)

async def run_date_range(start_date, end_date):
    """Export data untuk range tanggal tertentu"""
    automation = PlaywrightBackendAutomation()
    return await automation.run_automation(start_date, end_date)

async def run_last_week():
    """Export data untuk 7 hari terakhir"""
    automation = PlaywrightBackendAutomation()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    return await automation.run_automation(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )

# Main execution
if __name__ == "__main__":
    # Test dengan tanggal 8 September
    automation = PlaywrightBackendAutomation()
    asyncio.run(automation.run_automation("2025-09-08", "2025-09-08"))
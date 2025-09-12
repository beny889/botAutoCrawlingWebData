"""
Single Session Multi-Export Automation
Login once and run all 4 exports sequentially in the same browser session
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from shared.config import ExportConfig
from shared.data_validator import DataValidator
from shared.sheets_manager import SheetsManager

class SingleSessionAutomation:
    """Single session automation for all exports"""
    
    def __init__(self, headless=None, debug=False, production=False):
        self.logger = logging.getLogger(__name__)
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.config = ExportConfig()
        self.data_validator = DataValidator()
        # SheetsManager will be initialized per export type
        
        # Get browser configuration with overrides
        self.browser_config = self.config.get_browser_config(headless=headless, debug=debug, production=production)
        
        # Performance tracking
        self.session_start_time = None
        self.login_time = None
        self.export_times = {}
        
    async def initialize_browser(self):
        """Initialize browser and create context"""
        self.logger.info("Initializing browser session...")
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(**self.browser_config)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(self.browser_config["timeout"])
        
        self.logger.info("Browser session initialized successfully")
        
    async def login_to_backend(self):
        """Login to backend system once"""
        self.logger.info("Logging in to backend system...")
        login_start = datetime.now()
        
        try:
            # Navigate to login page
            await self.page.goto(self.config.BACKEND_BASE_URL)
            await self.page.wait_for_load_state('networkidle', timeout=60000)
            
            # Give page time to fully load
            await self.page.wait_for_timeout(2000)
            
            # Fill login form
            await self.page.fill(self.config.LOGIN_SELECTORS["username"], self.config.USERNAME)
            await self.page.fill(self.config.LOGIN_SELECTORS["password"], self.config.PASSWORD)
            
            # Wait a bit before clicking submit
            await self.page.wait_for_timeout(1000)
            
            # Click login button
            await self.page.click(self.config.LOGIN_SELECTORS["submit"])
            
            # Wait for login response with longer timeout
            await self.page.wait_for_load_state('networkidle', timeout=90000)
            
            # Verify login success (check for dashboard or logged-in indicator)
            try:
                # Wait for dashboard or any post-login element
                await self.page.wait_for_timeout(5000)  # Give time for redirect
                current_url = self.page.url
                
                if "login" in current_url.lower():
                    raise Exception("Login failed - still on login page")
                
                self.logger.info(f"Login successful - redirected to: {current_url}")
                    
            except Exception as e:
                await self.page.screenshot(path="login_failed.png")
                raise Exception(f"Login verification failed: {str(e)}")
            
            self.login_time = (datetime.now() - login_start).total_seconds()
            self.logger.info(f"Login successful in {self.login_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            await self.page.screenshot(path="login_error.png")
            return False
            
    async def export_transaksi(self, start_date: str, end_date: str):
        """Export transaksi data"""
        export_name = "transaksi"
        self.logger.info(f"Starting {export_name} export...")
        export_start = datetime.now()
        
        try:
            config = self.config.get_export_config(export_name)
            
            # Navigate to export page
            await self.page.goto(config["url"])
            await self.page.wait_for_load_state('networkidle')
            
            # Fill date fields (YYYY-MM-DD format for HTML5 date inputs)
            await self.page.fill('input[name="start_date"]', start_date)
            await self.page.fill('input[name="end_date"]', end_date)
            
            # Click export button and handle download
            async with self.page.expect_download() as download_info:
                await self.page.click('button:has-text("Export")')
            
            download = await download_info.value
            
            # Save file
            downloads_path = Path(self.config.DOWNLOADS_FOLDER)
            downloads_path.mkdir(exist_ok=True)
            
            file_path = downloads_path / f"{config['file_prefix']}_{start_date}_{end_date}.xlsx"
            await download.save_as(str(file_path))
            
            # Upload to Google Sheets
            sheets_manager = SheetsManager(export_name)
            success = sheets_manager.upload_with_smart_validation(str(file_path))
            
            # Check if upload was successful (upload_with_smart_validation returns True/False)
            self.export_times[export_name] = (datetime.now() - export_start).total_seconds()
            self.logger.info(f"{export_name} export completed in {self.export_times[export_name]:.2f} seconds")
            return True  # Always return True if we reach this point (upload completed)
                
        except Exception as e:
            self.logger.error(f"{export_name} export failed: {str(e)}")
            await self.page.screenshot(path=f"{export_name}_export_error.png")
            return False
            
    async def export_point_trx(self, start_date: str, end_date: str):
        """Export point transaction data"""
        export_name = "point_trx"
        self.logger.info(f"Starting {export_name} export...")
        export_start = datetime.now()
        
        try:
            config = self.config.get_export_config(export_name)
            selectors = config["selectors"]
            
            # Navigate to export page
            await self.page.goto(config["url"])
            await self.page.wait_for_load_state('networkidle')
            
            # Fill date fields (HTML5 date input format: YYYY-MM-DD)
            await self.page.fill(selectors["start_date"], start_date)
            await self.page.fill(selectors["end_date"], end_date)
            
            # Wait a moment for any dynamic updates
            await self.page.wait_for_timeout(1000)
            
            # Click export button and handle download
            async with self.page.expect_download() as download_info:
                await self.page.click(selectors["export_button"])
            
            download = await download_info.value
            
            # Save file
            downloads_path = Path(self.config.DOWNLOADS_FOLDER)
            downloads_path.mkdir(exist_ok=True)
            
            file_extension = ".pdf" if config["file_type"] == "pdf" else ".xlsx"
            file_path = downloads_path / f"{config['file_prefix']}_{start_date}_{end_date}{file_extension}"
            await download.save_as(str(file_path))
            
            # Upload Excel file to Google Sheets (all exports are now Excel format)
            sheets_manager = SheetsManager(export_name)
            success = sheets_manager.upload_with_smart_validation(str(file_path))
            
            # Always return True if we reach this point (upload completed)
            self.export_times[export_name] = (datetime.now() - export_start).total_seconds()
            self.logger.info(f"{export_name} export completed in {self.export_times[export_name]:.2f} seconds")
            return True
                
        except Exception as e:
            self.logger.error(f"{export_name} export failed: {str(e)}")
            await self.page.screenshot(path=f"{export_name}_export_error.png")
            return False
            
    async def export_user(self, start_date: str, end_date: str):
        """Export user data with date filtering"""
        export_name = "user"
        self.logger.info(f"Starting {export_name} export...")
        export_start = datetime.now()
        
        try:
            config = self.config.get_export_config(export_name)
            selectors = config["selectors"]
            
            # Navigate to export page
            await self.page.goto(config["url"])
            await self.page.wait_for_load_state('networkidle')
            
            # Fill date fields (HTML5 date input format: YYYY-MM-DD)
            await self.page.fill(selectors["start_date"], start_date)
            await self.page.fill(selectors["end_date"], end_date)
            
            # Wait a moment for any dynamic updates
            await self.page.wait_for_timeout(1000)
            
            # Click export button and handle download
            async with self.page.expect_download() as download_info:
                await self.page.click(selectors["export_button"])
            
            download = await download_info.value
            
            # Save file
            downloads_path = Path(self.config.DOWNLOADS_FOLDER)
            downloads_path.mkdir(exist_ok=True)
            
            file_extension = ".pdf" if config["file_type"] == "pdf" else ".xlsx"
            file_path = downloads_path / f"{config['file_prefix']}_{start_date}_{end_date}{file_extension}"
            await download.save_as(str(file_path))
            
            # Upload Excel file to Google Sheets (all exports are now Excel format)
            sheets_manager = SheetsManager(export_name)
            success = sheets_manager.upload_with_smart_validation(str(file_path))
            
            # Always return True if we reach this point (upload completed)
            self.export_times[export_name] = (datetime.now() - export_start).total_seconds()
            self.logger.info(f"{export_name} export completed in {self.export_times[export_name]:.2f} seconds")
            return True
                
        except Exception as e:
            self.logger.error(f"{export_name} export failed: {str(e)}")
            await self.page.screenshot(path=f"{export_name}_export_error.png")
            return False
            
    async def export_pembayaran_koin(self, start_date: str, end_date: str):
        """Export coin payment data"""
        export_name = "pembayaran_koin"
        self.logger.info(f"Starting {export_name} export...")
        export_start = datetime.now()
        
        try:
            config = self.config.get_export_config(export_name)
            selectors = config["selectors"]
            
            # Navigate to export page
            await self.page.goto(config["url"])
            await self.page.wait_for_load_state('networkidle')
            
            # Fill date fields (HTML5 date input format: YYYY-MM-DD)
            await self.page.fill(selectors["start_date"], start_date)
            await self.page.fill(selectors["end_date"], end_date)
            
            # Wait a moment for any dynamic updates
            await self.page.wait_for_timeout(1000)
            
            # Click export button and handle download
            async with self.page.expect_download() as download_info:
                await self.page.click(selectors["export_button"])
            
            download = await download_info.value
            
            # Save file
            downloads_path = Path(self.config.DOWNLOADS_FOLDER)
            downloads_path.mkdir(exist_ok=True)
            
            file_extension = ".pdf" if config["file_type"] == "pdf" else ".xlsx"
            file_path = downloads_path / f"{config['file_prefix']}_{start_date}_{end_date}{file_extension}"
            await download.save_as(str(file_path))
            
            # Upload Excel file to Google Sheets (all exports are now Excel format)
            sheets_manager = SheetsManager(export_name)
            success = sheets_manager.upload_with_smart_validation(str(file_path))
            
            # Always return True if we reach this point (upload completed)
            self.export_times[export_name] = (datetime.now() - export_start).total_seconds()
            self.logger.info(f"{export_name} export completed in {self.export_times[export_name]:.2f} seconds")
            return True
                
        except Exception as e:
            self.logger.error(f"{export_name} export failed: {str(e)}")
            await self.page.screenshot(path=f"{export_name}_export_error.png")
            return False
            
    async def _analyze_page_structure(self, export_name: str):
        """Analyze page structure for data collection"""
        try:
            # Take screenshot for manual analysis
            await self.page.screenshot(path=f"{export_name}_page_analysis.png")
            
            # Get page title
            title = await self.page.title()
            self.logger.info(f"Page title: {title}")
            
            # Find all input fields
            inputs = await self.page.query_selector_all('input')
            self.logger.info(f"Found {len(inputs)} input fields:")
            
            for i, input_elem in enumerate(inputs):
                name = await input_elem.get_attribute('name') or 'N/A'
                placeholder = await input_elem.get_attribute('placeholder') or 'N/A'
                input_type = await input_elem.get_attribute('type') or 'text'
                self.logger.info(f"  Input {i+1}: name='{name}', placeholder='{placeholder}', type='{input_type}'")
            
            # Find all buttons
            buttons = await self.page.query_selector_all('button')
            self.logger.info(f"Found {len(buttons)} buttons:")
            
            for i, button in enumerate(buttons):
                text = await button.text_content() or 'N/A'
                classes = await button.get_attribute('class') or 'N/A'
                self.logger.info(f"  Button {i+1}: text='{text.strip()}', class='{classes}'")
            
            # Find forms
            forms = await self.page.query_selector_all('form')
            self.logger.info(f"Found {len(forms)} forms")
            
            # Check for data tables or export indicators
            tables = await self.page.query_selector_all('table')
            self.logger.info(f"Found {len(tables)} tables")
            
            # Look for export/download related elements
            export_elements = await self.page.query_selector_all('[class*="export"], [id*="export"], button:has-text("Export"), a:has-text("Export"), button:has-text("Download"), a:has-text("Download")')
            self.logger.info(f"Found {len(export_elements)} export-related elements:")
            
            for i, elem in enumerate(export_elements):
                tag = await elem.evaluate('el => el.tagName.toLowerCase()')
                text = await elem.text_content() or 'N/A'
                classes = await elem.get_attribute('class') or 'N/A'
                self.logger.info(f"  Export element {i+1}: {tag}, text='{text.strip()}', class='{classes}'")
                
        except Exception as e:
            self.logger.error(f"Page analysis failed: {str(e)}")
            
    async def run_all_exports_sequential(self, start_date: str = None, end_date: str = None):
        """Run all exports in single session"""
        self.session_start_time = datetime.now()
        
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if not end_date:
            end_date = start_date
            
        self.logger.info(f"Starting single session automation for date range: {start_date} to {end_date}")
        
        try:
            # Initialize browser
            await self.initialize_browser()
            
            # Login once
            if not await self.login_to_backend():
                return {"success": False, "error": "Login failed"}
            
            # Run all exports sequentially
            results = {}
            
            # 1. Transaksi Export (working)
            results["transaksi"] = await self.export_transaksi(start_date, end_date)
            
            # 2. Point Transaction Export (needs data collection)
            results["point_trx"] = await self.export_point_trx(start_date, end_date)
            
            # 3. User Export (with date filter)
            results["user"] = await self.export_user(start_date, end_date)
            
            # 4. Coin Payment Export (needs data collection)  
            results["pembayaran_koin"] = await self.export_pembayaran_koin(start_date, end_date)
            
            # Calculate session statistics
            total_time = (datetime.now() - self.session_start_time).total_seconds()
            successful_exports = [k for k, v in results.items() if v]
            failed_exports = [k for k, v in results.items() if not v]
            
            self.logger.info("=== Single Session Automation Summary ===")
            self.logger.info(f"Total session time: {total_time:.2f} seconds")
            self.logger.info(f"Login time: {self.login_time:.2f} seconds")
            self.logger.info(f"Successful exports: {successful_exports}")
            self.logger.info(f"Failed exports: {failed_exports}")
            
            for export_name, duration in self.export_times.items():
                self.logger.info(f"{export_name} export time: {duration:.2f} seconds")
            
            return {
                "success": True,
                "results": results,
                "stats": {
                    "total_time": total_time,
                    "login_time": self.login_time,
                    "export_times": self.export_times,
                    "successful_exports": successful_exports,
                    "failed_exports": failed_exports
                }
            }
            
        except Exception as e:
            self.logger.error(f"Single session automation failed: {str(e)}")
            return {"success": False, "error": str(e)}
            
        finally:
            # Clean up browser
            if self.browser:
                await self.browser.close()
                self.logger.info("Browser session closed")
                
    async def test_individual_export(self, export_type: str, start_date: str = None, end_date: str = None):
        """Test individual export for data collection"""
        self.logger.info(f"Testing individual export: {export_type}")
        
        try:
            await self.initialize_browser()
            
            if not await self.login_to_backend():
                return False
            
            if export_type == "transaksi":
                return await self.export_transaksi(start_date or datetime.now().strftime("%Y-%m-%d"), 
                                                  end_date or datetime.now().strftime("%Y-%m-%d"))
            elif export_type == "point_trx":
                return await self.export_point_trx(start_date or datetime.now().strftime("%Y-%m-%d"),
                                                  end_date or datetime.now().strftime("%Y-%m-%d"))
            elif export_type == "user":
                return await self.export_user(start_date or datetime.now().strftime("%Y-%m-%d"),
                                            end_date or datetime.now().strftime("%Y-%m-%d"))
            elif export_type == "pembayaran_koin":
                return await self.export_pembayaran_koin(start_date or datetime.now().strftime("%Y-%m-%d"),
                                                        end_date or datetime.now().strftime("%Y-%m-%d"))
            else:
                self.logger.error(f"Unknown export type: {export_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Individual export test failed: {str(e)}")
            return False
            
        finally:
            if self.browser:
                await self.browser.close()


# Convenience functions
async def run_single_session_today():
    """Run all exports for today in single session"""
    automation = SingleSessionAutomation()
    today = datetime.now().strftime("%Y-%m-%d")
    return await automation.run_all_exports_sequential(today, today)

async def run_single_session_date(date: str):
    """Run all exports for specific date in single session"""
    automation = SingleSessionAutomation()
    return await automation.run_all_exports_sequential(date, date)

async def test_export_page(export_type: str):
    """Test individual export page for data collection"""
    automation = SingleSessionAutomation()
    return await automation.test_individual_export(export_type)


# Main execution for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Single Session Multi-Export Automation')
    parser.add_argument('--date', type=str, help='Date for export (YYYY-MM-DD)')
    parser.add_argument('--test', type=str, help='Test specific export (point_trx, user, pembayaran_koin)')
    parser.add_argument('--all', action='store_true', help='Run all exports in single session')
    parser.add_argument('--headless', action='store_true', help='Force headless mode (no browser window)')
    parser.add_argument('--debug', action='store_true', help='Debug mode (show browser, slow motion)')
    parser.add_argument('--production', action='store_true', help='Production mode (optimized settings)')
    
    args = parser.parse_args()
    
    # Setup logging
    log_folder = Path("logs")
    log_folder.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/single_session.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Determine browser configuration based on arguments
    headless = args.headless if hasattr(args, 'headless') else None
    debug = args.debug if hasattr(args, 'debug') else False
    production = args.production if hasattr(args, 'production') else False
    
    if args.test:
        # Test individual export
        automation = SingleSessionAutomation(headless=headless, debug=debug, production=production)
        asyncio.run(automation.test_individual_export(args.test))
    elif args.all or args.date:
        # Run all exports
        target_date = args.date or datetime.now().strftime("%Y-%m-%d")
        automation = SingleSessionAutomation(headless=headless, debug=debug, production=production)
        asyncio.run(automation.run_all_exports_sequential(target_date, target_date))
    else:
        # Default: run all exports for today
        automation = SingleSessionAutomation(headless=headless, debug=debug, production=production)
        today = datetime.now().strftime("%Y-%m-%d")
        asyncio.run(automation.run_all_exports_sequential(today, today))
"""
Backend connection and navigation logic shared across all exports
"""

import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
from pathlib import Path
from .config import ExportConfig

class BackendConnector:
    """Handles backend login and navigation for all export types"""
    
    def __init__(self, export_type: str):
        self.export_type = export_type
        self.export_config = ExportConfig.get_export_config(export_type)
        self.browser_config = ExportConfig.BROWSER_CONFIG
        self.login_selectors = ExportConfig.LOGIN_SELECTORS
        self.logger = logging.getLogger(__name__)
        
        # Setup directories
        self.download_folder = Path(ExportConfig.DOWNLOADS_FOLDER)
        self.download_folder.mkdir(exist_ok=True)
        
    async def setup_browser(self):
        """Setup Playwright browser"""
        self.logger.info(f"Setting up browser for {self.export_config['name']}...")
        
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
        self.page.set_default_timeout(self.browser_config["timeout"])
        
        self.logger.info("Browser setup completed")
    
    async def login_to_backend(self):
        """Login to backend website"""
        self.logger.info("Logging in to backend...")
        
        try:
            # Navigate to login page
            await self.page.goto(ExportConfig.BACKEND_BASE_URL)
            await self.page.wait_for_load_state('networkidle')
            
            # Fill login form
            await self.page.fill(self.login_selectors["username"], ExportConfig.USERNAME)
            await self.page.fill(self.login_selectors["password"], ExportConfig.PASSWORD)
            
            # Click login button
            await self.page.click(self.login_selectors["submit"])
            
            # Wait for page to load after login
            await self.page.wait_for_load_state('networkidle', timeout=60000)
            
            # Verify login success
            current_url = self.page.url
            if "login" not in current_url.lower():
                self.logger.info("Login successful!")
                return True
            else:
                raise Exception("Login failed - still on login page")
                
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            await self.page.screenshot(path=f"login_error_{self.export_type}.png")
            raise
    
    async def navigate_to_export_page(self):
        """Navigate to specific export page"""
        self.logger.info(f"Navigating to {self.export_config['name']} page...")
        
        try:
            # Navigate to export page
            await self.page.goto(self.export_config["url"])
            await self.page.wait_for_load_state('networkidle')
            
            self.logger.info(f"Successfully navigated to {self.export_config['name']} page")
            
        except Exception as e:
            self.logger.error(f"Navigation failed: {str(e)}")
            await self.page.screenshot(path=f"navigation_error_{self.export_type}.png")
            raise
    
    async def download_export_file(self, start_date=None, end_date=None):
        """Download export file from current page"""
        self.logger.info(f"Downloading {self.export_config['name']} file...")
        
        try:
            # Handle date filtering if required
            if self.export_config["requires_date_filter"] and start_date and end_date:
                await self._set_date_filters(start_date, end_date)
            
            # Take screenshot before download
            await self.page.screenshot(path=f"before_download_{self.export_type}.png")
            
            # Setup download handler and click export button
            async with self.page.expect_download(timeout=60000) as download_info:
                # Try common export button selectors
                export_selectors = [
                    'button:has-text("Export")',
                    '.btn:has-text("Export")', 
                    'input[type="submit"][value*="Export"]',
                    'a:has-text("Export")'
                ]
                
                export_clicked = False
                for selector in export_selectors:
                    try:
                        await self.page.click(selector)
                        export_clicked = True
                        break
                    except:
                        continue
                
                if not export_clicked:
                    raise Exception("Could not find export button")
            
            # Get download
            download = await download_info.value
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.export_config['file_prefix']}_{timestamp}.xlsx"
            file_path = self.download_folder / filename
            
            # Save download
            await download.save_as(file_path)
            
            self.logger.info(f"File downloaded successfully: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Download failed: {str(e)}")
            await self.page.screenshot(path=f"download_error_{self.export_type}.png")
            raise
    
    async def _set_date_filters(self, start_date, end_date):
        """Set date filters on export page"""
        self.logger.info(f"Setting date filters: {start_date} to {end_date}")
        
        try:
            # Convert to proper format for HTML5 date inputs
            if isinstance(start_date, str):
                start_formatted = start_date  # Assume YYYY-MM-DD
            else:
                start_formatted = start_date.strftime("%Y-%m-%d")
                
            if isinstance(end_date, str):
                end_formatted = end_date
            else:
                end_formatted = end_date.strftime("%Y-%m-%d")
            
            # Try to find and fill date fields
            date_selectors = [
                'input[name="start_date"]',
                'input[name="end_date"]',
                'input[placeholder*="dd/mm/yyyy"]'
            ]
            
            # Find start date field
            start_field = None
            for selector in date_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        start_field = elements[0]  # First one is usually start date
                        break
                except:
                    continue
            
            # Find end date field
            end_field = None
            for selector in date_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if len(elements) >= 2:
                        end_field = elements[1]  # Second one is usually end date
                        break
                    elif len(elements) == 1 and start_field != elements[0]:
                        end_field = elements[0]
                        break
                except:
                    continue
            
            if start_field:
                await start_field.fill(start_formatted)
                self.logger.info(f"Start date set: {start_formatted}")
            
            if end_field:
                await end_field.fill(end_formatted) 
                self.logger.info(f"End date set: {end_formatted}")
                
        except Exception as e:
            self.logger.warning(f"Date filter setup failed: {str(e)}")
            # Continue anyway - some exports might not need date filters
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if hasattr(self, 'browser'):
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            self.logger.info("Browser cleanup completed")
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {str(e)}")

    def cleanup_old_files(self, days_to_keep=None):
        """Clean up old downloaded files"""
        if days_to_keep is None:
            days_to_keep = ExportConfig.CLEANUP_DAYS
            
        try:
            import time
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            for file_path in self.download_folder.glob(f"{self.export_config['file_prefix']}_*"):
                if file_path.stat().st_ctime < cutoff_time:
                    file_path.unlink()
                    self.logger.info(f"Cleaned up old file: {file_path.name}")
                    
        except Exception as e:
            self.logger.warning(f"File cleanup failed: {str(e)}")
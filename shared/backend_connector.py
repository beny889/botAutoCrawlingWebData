"""
Backend connection and navigation logic shared across all exports
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from .config import ExportConfig

class BackendConnector:
    """Handles backend login and navigation for all export types"""
    
    def __init__(self, export_type: str):
        self.export_type = export_type
        self.export_config = ExportConfig.get_export_config(export_type)
        self.browser_config = ExportConfig.BROWSER_CONFIG
        self.login_selectors = ExportConfig.LOGIN_SELECTORS
        self.logger = logging.getLogger(__name__)
        self.driver = None
        self.wait = None
        
        # Setup directories
        self.download_folder = Path(ExportConfig.DOWNLOADS_FOLDER)
        self.download_folder.mkdir(exist_ok=True)
        
    def setup_browser(self):
        """Setup Selenium WebDriver with robust Chrome detection"""
        self.logger.info(f"Setting up browser for {self.export_config['name']}...")
        
        try:
            # Setup Chrome options
            chrome_options = Options()
            
            if self.browser_config["headless"]:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            
            # Download preferences
            prefs = {
                "download.default_directory": str(self.download_folder.absolute()),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # For cloud deployment, try to find Chrome/Chromium binary
            import os
            chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome", 
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/snap/bin/chromium",  # Snap-installed Chromium
                "/var/lib/snapd/snap/bin/chromium"  # Alternative snap path
            ]
            
            chrome_found = False
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    chrome_options.binary_location = chrome_path
                    self.logger.info(f"Using browser binary at: {chrome_path}")
                    chrome_found = True
                    break
            
            if not chrome_found:
                self.logger.warning("No Chrome/Chromium binary found, using system default")
            
            # Use ChromeDriverManager with enhanced error handling
            driver_initialized = False
            
            # Strategy 1: Try with detected browser binary
            if chrome_found:
                try:
                    self.logger.info("Attempting ChromeDriver setup with detected browser binary...")
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    driver_initialized = True
                    self.logger.info("Chrome WebDriver initialized successfully with binary location")
                except Exception as e:
                    self.logger.warning(f"Failed with binary location: {str(e)}")
            
            # Strategy 2: Try without explicit binary location (system PATH)
            if not driver_initialized:
                try:
                    self.logger.info("Attempting ChromeDriver setup without explicit binary...")
                    chrome_options_system = Options()
                    
                    # Re-add all options without binary location
                    if self.browser_config["headless"]:
                        chrome_options_system.add_argument("--headless")
                    
                    chrome_options_system.add_argument("--no-sandbox")
                    chrome_options_system.add_argument("--disable-dev-shm-usage")
                    chrome_options_system.add_argument("--disable-gpu")
                    chrome_options_system.add_argument("--window-size=1920,1080")
                    chrome_options_system.add_argument("--disable-extensions")
                    chrome_options_system.add_argument("--disable-plugins")
                    chrome_options_system.add_argument("--disable-web-security")
                    chrome_options_system.add_argument("--allow-running-insecure-content")
                    chrome_options_system.add_experimental_option("prefs", prefs)
                    
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options_system)
                    driver_initialized = True
                    self.logger.info("Chrome WebDriver initialized successfully without binary location")
                except Exception as e:
                    self.logger.warning(f"Failed without binary location: {str(e)}")
            
            # Strategy 3: Try with specific Chrome versions and manual ChromeDriver
            if not driver_initialized:
                try:
                    self.logger.info("Attempting manual ChromeDriver setup...")
                    # Try to use ChromeDriver that might be pre-installed
                    service = Service()  # Use system ChromeDriver if available
                    self.driver = webdriver.Chrome(service=service, options=chrome_options_system)
                    driver_initialized = True
                    self.logger.info("Chrome WebDriver initialized with system ChromeDriver")
                except Exception as e:
                    self.logger.error(f"All Chrome WebDriver strategies failed: {str(e)}")
                    raise RuntimeError(f"Unable to initialize Chrome WebDriver. Browser installation may have failed. Last error: {str(e)}")
            
            if not driver_initialized:
                raise RuntimeError("Chrome WebDriver could not be initialized after all attempts")
            
            # Setup wait
            self.wait = WebDriverWait(self.driver, self.browser_config["timeout"] // 1000)
            
            # Set implicit wait
            self.driver.implicitly_wait(10)
            
            self.logger.info("Browser setup completed")
            
        except Exception as e:
            self.logger.error(f"Browser setup failed: {str(e)}")
            raise
    
    def login_to_backend(self):
        """Login to backend website"""
        self.logger.info("Logging in to backend...")
        
        try:
            # Navigate to login page
            self.driver.get(ExportConfig.BACKEND_BASE_URL)
            time.sleep(3)  # Wait for page to load
            
            # Fill login form
            username_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.login_selectors["username"])))
            username_field.clear()
            username_field.send_keys(ExportConfig.USERNAME)
            
            password_field = self.driver.find_element(By.CSS_SELECTOR, self.login_selectors["password"])
            password_field.clear()
            password_field.send_keys(ExportConfig.PASSWORD)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, self.login_selectors["submit"])
            login_button.click()
            
            # Wait for page to load after login
            time.sleep(5)
            
            # Verify login success
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                self.logger.info("Login successful!")
                return True
            else:
                raise Exception("Login failed - still on login page")
                
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            self.driver.save_screenshot(f"login_error_{self.export_type}.png")
            raise
    
    def navigate_to_export_page(self):
        """Navigate to specific export page"""
        self.logger.info(f"Navigating to {self.export_config['name']} page...")
        
        try:
            # Navigate to export page
            self.driver.get(self.export_config["url"])
            time.sleep(3)  # Wait for page to load
            
            self.logger.info(f"Successfully navigated to {self.export_config['name']} page")
            
        except Exception as e:
            self.logger.error(f"Navigation failed: {str(e)}")
            self.driver.save_screenshot(f"navigation_error_{self.export_type}.png")
            raise
    
    def download_export_file(self, start_date=None, end_date=None):
        """Download export file from current page"""
        self.logger.info(f"Downloading {self.export_config['name']} file...")
        
        try:
            # Handle date filtering if required
            if self.export_config["requires_date_filter"] and start_date and end_date:
                self._set_date_filters(start_date, end_date)
            
            # Take screenshot before download
            self.driver.save_screenshot(f"before_download_{self.export_type}.png")
            
            # Get initial file count
            initial_files = list(self.download_folder.glob("*.xlsx"))
            
            # Try export button selectors from config first, then fallbacks
            config_selector = self.export_config["selectors"].get("export_button")
            export_selectors = []
            
            # Add config selector first if exists
            if config_selector:
                export_selectors.append(config_selector)
            
            # Add specific selectors found in logs for different export types  
            export_selectors.extend([
                '//button[text()="Export"]',  # Direct XPath for button with exact text "Export"
                '//button[contains(text(), "Export")]',  # XPath for button containing "Export"
                'button.btn.btn-success.m3.expot-pdf',  # For pembayaran_koin, user, point_trx
                'button.expot-pdf',  # Alternative selector for expot-pdf class
                'button.btn.btn-success',  # More general btn-success selector
                'button.btn.btn-primary',  # For transaksi export
                'button:contains("Export")',
                'button[type="submit"]',
                '.btn:contains("Export")', 
                'input[type="submit"][value*="Export"]',
                'a:contains("Export")',
                '.btn-primary'
            ])
            
            export_clicked = False
            clicked_selector = None
            
            for selector in export_selectors:
                try:
                    self.logger.info(f"Trying export button selector: {selector}")
                    
                    # Determine selector type and find element accordingly
                    if selector.startswith('//'):
                        # Direct XPath selector
                        element = self.driver.find_element(By.XPATH, selector)
                    elif ":contains(" in selector:
                        # Convert CSS selector to XPath for contains functionality
                        text = selector.split(':contains("')[1].split('")')[0]
                        element_type = selector.split(':contains(')[0]
                        if element_type == 'button':
                            xpath = f"//button[contains(text(), '{text}')]"
                        elif element_type == '.btn':
                            xpath = f"//*[contains(@class, 'btn') and contains(text(), '{text}')]"
                        else:
                            xpath = f"//{element_type}[contains(text(), '{text}')]"
                        
                        element = self.driver.find_element(By.XPATH, xpath)
                    else:
                        # Standard CSS selector
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Log button details before clicking
                    button_text = element.text or element.get_attribute("value") or "No text"
                    self.logger.info(f"Found export button with text: '{button_text}' using selector: {selector}")
                    
                    # Scroll to element and ensure it's clickable
                    self.driver.execute_script("arguments[0].scrollIntoView();", element)
                    time.sleep(1)
                    
                    element.click()
                    export_clicked = True
                    clicked_selector = selector
                    self.logger.info(f"Successfully clicked export button: {selector}")
                    
                    # Give the system time to process the export request
                    time.sleep(3)
                    break
                    
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {str(e)}")
                    continue
            
            if not export_clicked:
                self.logger.error("Export button search failed - taking screenshot for debugging")
                self.driver.save_screenshot(f"export_button_not_found_{self.export_type}.png")
                
                # List all buttons for debugging
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                self.logger.error(f"Found {len(all_buttons)} buttons on page:")
                for i, btn in enumerate(all_buttons):
                    btn_text = btn.text or btn.get_attribute("value") or "No text"
                    btn_class = btn.get_attribute("class") or "No class"
                    btn_type = btn.get_attribute("type") or "No type"
                    self.logger.error(f"Button {i}: text='{btn_text}', class='{btn_class}', type='{btn_type}'")
                
                raise Exception("Could not find export button")
            
            self.logger.info(f"Export initiated using selector: {clicked_selector}")
            
            # Wait for download to complete with enhanced detection
            self.logger.info("Waiting for download to complete...")
            timeout = 60  # 60 seconds timeout
            start_time = time.time()
            
            downloaded_file = None
            while time.time() - start_time < timeout:
                current_files = list(self.download_folder.glob("*.xlsx"))
                
                # Check for new files
                new_files = [f for f in current_files if f not in initial_files]
                if new_files:
                    # Found new file, check if it's complete and not empty
                    newest_file = max(new_files, key=lambda x: x.stat().st_mtime)
                    file_size = newest_file.stat().st_size
                    
                    self.logger.info(f"Found new file: {newest_file.name}, size: {file_size} bytes")
                    
                    # Wait for file to stabilize (stop growing)
                    stable_count = 0
                    last_size = 0
                    
                    for _ in range(10):  # Check for 10 seconds
                        time.sleep(1)
                        current_size = newest_file.stat().st_size
                        
                        if current_size == last_size and current_size > 0:
                            stable_count += 1
                            if stable_count >= 3:  # File stable for 3 seconds
                                downloaded_file = newest_file
                                break
                        else:
                            stable_count = 0
                        
                        last_size = current_size
                        self.logger.info(f"File size: {current_size} bytes, stable count: {stable_count}")
                    
                    if downloaded_file:
                        break
                
                time.sleep(1)
            else:
                raise Exception("Download timeout - no valid file appeared within timeout")
            
            if not downloaded_file:
                raise Exception("Download failed - no valid file found")
            
            # Verify file is not empty
            file_size = downloaded_file.stat().st_size
            if file_size == 0:
                raise Exception(f"Downloaded file is empty! File: {downloaded_file.name}")
            
            self.logger.info(f"Download completed - File size: {file_size} bytes")
            
            # Generate new filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{self.export_config['file_prefix']}_{timestamp}.xlsx"
            new_file_path = self.download_folder / new_filename
            
            # Rename file
            downloaded_file.rename(new_file_path)
            
            self.logger.info(f"File downloaded successfully: {new_file_path} ({file_size} bytes)")
            return new_file_path
            
        except Exception as e:
            self.logger.error(f"Download failed: {str(e)}")
            self.driver.save_screenshot(f"download_error_{self.export_type}.png")
            raise
    
    def _set_date_filters(self, start_date, end_date):
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
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        start_field = elements[0]  # First one is usually start date
                        break
                except:
                    continue
            
            # Find end date field
            end_field = None
            for selector in date_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) >= 2:
                        end_field = elements[1]  # Second one is usually end date
                        break
                    elif len(elements) == 1 and start_field != elements[0]:
                        end_field = elements[0]
                        break
                except:
                    continue
            
            if start_field:
                start_field.clear()
                start_field.send_keys(start_formatted)
                self.logger.info(f"Start date set: {start_formatted}")
            
            if end_field:
                end_field.clear()
                end_field.send_keys(end_formatted)
                self.logger.info(f"End date set: {end_formatted}")
                
        except Exception as e:
            self.logger.warning(f"Date filter setup failed: {str(e)}")
            # Continue anyway - some exports might not need date filters
    
    def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.driver:
                self.driver.quit()
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
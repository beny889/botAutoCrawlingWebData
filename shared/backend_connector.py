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
        """Download export file from current page with enhanced validation"""
        self.logger.info(f"ENHANCED DOWNLOAD: {self.export_config['name']} for dates {start_date} to {end_date}")
        
        try:
            # Clear download folder first to avoid confusion
            self._clear_download_folder()
            
            # Handle date filtering if required
            if self.export_config["requires_date_filter"] and start_date and end_date:
                self._set_date_filters_enhanced(start_date, end_date)
            
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
                    
                    # Check if element is actually clickable
                    if not element.is_enabled():
                        self.logger.warning(f"Element with selector {selector} is not enabled/clickable")
                        continue
                    
                    # Try clicking the element
                    try:
                        element.click()
                        export_clicked = True
                        clicked_selector = selector
                        self.logger.info(f"Successfully clicked export button: {selector}")
                        
                        # Give the system time to process the export request
                        time.sleep(3)
                        break
                        
                    except Exception as click_error:
                        self.logger.warning(f"Click failed for selector {selector}: {str(click_error)}")
                        # Try JavaScript click as fallback
                        try:
                            self.driver.execute_script("arguments[0].click();", element)
                            export_clicked = True
                            clicked_selector = selector
                            self.logger.info(f"Successfully clicked export button using JavaScript: {selector}")
                            
                            # Give the system time to process the export request
                            time.sleep(3)
                            break
                            
                        except Exception as js_click_error:
                            self.logger.error(f"Both regular and JavaScript click failed for {selector}: {str(js_click_error)}")
                            continue
                    
                except Exception as e:
                    self.logger.warning(f"Selector {selector} failed during element finding: {str(e)}")
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
            
            # Enhanced download detection with longer wait and better validation
            downloaded_file = self._wait_for_download_completion_enhanced(initial_files)
            
            # Comprehensive file validation
            file_size = downloaded_file.stat().st_size
            self.logger.info(f"DOWNLOAD VALIDATION: File size: {file_size} bytes")
            
            if file_size == 0:
                # Take screenshot for debugging empty files
                self.driver.save_screenshot(f"empty_file_debug_{self.export_type}_{start_date}.png")
                raise Exception(f"CRITICAL: Downloaded file is EMPTY! File: {downloaded_file.name}, Export: {self.export_type}")
            
            # Additional validation for suspiciously small files
            if file_size < 1000:  # Less than 1KB is suspicious for Excel files
                self.logger.warning(f"WARNING: Very small file size ({file_size} bytes) - may contain headers only")
                
                # Try to read the file to check content
                try:
                    import pandas as pd
                    test_df = pd.read_excel(downloaded_file)
                    if len(test_df) == 0:
                        self.logger.warning(f"File contains headers but no data rows - this may be expected for date {start_date}")
                    else:
                        self.logger.info(f"File validation: {len(test_df)} data rows found")
                except Exception as read_error:
                    self.logger.error(f"Could not validate file content: {read_error}")
            
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
    
    def _clear_download_folder(self):
        """Clear download folder of any existing Excel files"""
        try:
            for file_path in self.download_folder.glob("*.xlsx"):
                file_path.unlink()
                self.logger.info(f"Cleared existing file: {file_path.name}")
        except Exception as e:
            self.logger.warning(f"Could not clear download folder: {str(e)}")
    
    def _validate_and_format_date(self, date_input):
        """Validate and format date input to YYYY-MM-DD"""
        if isinstance(date_input, str):
            # Assume already in YYYY-MM-DD format, validate it
            try:
                from datetime import datetime
                datetime.strptime(date_input, "%Y-%m-%d")
                return date_input
            except ValueError:
                self.logger.error(f"Invalid date format: {date_input}. Expected YYYY-MM-DD")
                raise
        else:
            return date_input.strftime("%Y-%m-%d")
    
    def _find_date_field_enhanced(self, selector, field_type):
        """Enhanced date field finding with multiple strategies"""
        try:
            field = self.driver.find_element(By.CSS_SELECTOR, selector)
            self.logger.info(f"Found {field_type} date field using selector: {selector}")
            return field
        except Exception as e:
            self.logger.error(f"Could not find {field_type} date field with selector {selector}: {str(e)}")
            
            # List all input fields for debugging
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            self.logger.info(f"Found {len(all_inputs)} input fields on page:")
            for i, inp in enumerate(all_inputs):
                inp_type = inp.get_attribute("type") or "No type"
                inp_name = inp.get_attribute("name") or "No name"
                inp_id = inp.get_attribute("id") or "No id"
                inp_class = inp.get_attribute("class") or "No class"
                self.logger.info(f"Input {i}: type='{inp_type}', name='{inp_name}', id='{inp_id}', class='{inp_class}'")
            
            return None
    
    def _set_date_field_value_enhanced(self, field_element, date_value, field_type):
        """Enhanced date field value setting with comprehensive validation"""
        try:
            self.logger.info(f"Setting {field_type} date field to: {date_value}")
            
            # Get current value before setting
            current_value = field_element.get_attribute('value')
            self.logger.info(f"Current {field_type} field value: '{current_value}'")
            
            # Method 1: Clear and send keys
            field_element.clear()
            time.sleep(0.2)
            field_element.send_keys(date_value)
            time.sleep(0.2)
            
            # Method 2: JavaScript value setting with comprehensive events
            self.driver.execute_script("""
                console.log('Setting date field value:', arguments[1]);
                arguments[0].value = arguments[1];
                
                // Trigger comprehensive events
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('keyup', { bubbles: true }));
                
                console.log('Date field value after setting:', arguments[0].value);
            """, field_element, date_value)
            
            # Give time for any JavaScript validation/processing
            time.sleep(1)
            
            # Verify the value was set correctly with multiple checks
            for attempt in range(3):
                actual_value = field_element.get_attribute('value')
                self.logger.info(f"Verification attempt {attempt + 1}: {field_type} field value = '{actual_value}'")
                
                if actual_value == date_value:
                    self.logger.info(f"SUCCESS: {field_type} date field correctly set to: {actual_value}")
                    return
                elif actual_value and actual_value != current_value:
                    self.logger.warning(f"PARTIAL: {field_type} field has value '{actual_value}' but expected '{date_value}'")
                    break
                else:
                    # Try force setting again
                    self.driver.execute_script("arguments[0].value = arguments[1];", field_element, date_value)
                    time.sleep(0.5)
            
            # Final verification
            final_value = field_element.get_attribute('value')
            if final_value != date_value:
                self.logger.error(f"FAILED: {field_type} date field final value '{final_value}' does not match expected '{date_value}'")
                raise Exception(f"Date field {field_type} could not be set correctly")
            
        except Exception as e:
            self.logger.error(f"Failed to set {field_type} date field: {str(e)}")
            raise
    
    def _wait_for_download_completion_enhanced(self, initial_files):
        """Enhanced download completion detection with comprehensive validation"""
        self.logger.info("ENHANCED DOWNLOAD DETECTION: Waiting for file completion...")
        timeout = 90  # Extended timeout for slow networks
        start_time = time.time()
        
        downloaded_file = None
        check_interval = 2  # Check every 2 seconds
        
        while time.time() - start_time < timeout:
            current_files = list(self.download_folder.glob("*.xlsx"))
            
            # Check for new files
            new_files = [f for f in current_files if f not in initial_files]
            if new_files:
                # Found new file(s), get the most recent
                newest_file = max(new_files, key=lambda x: x.stat().st_mtime)
                file_size = newest_file.stat().st_size
                
                self.logger.info(f"DETECTION: Found file {newest_file.name}, size: {file_size} bytes")
                
                # Enhanced stability check - wait for file to stop growing
                stable_checks = 6  # Check stability for 12 seconds (6 * 2s intervals)
                stable_count = 0
                last_size = -1
                
                for stability_check in range(stable_checks):
                    time.sleep(check_interval)
                    current_size = newest_file.stat().st_size
                    
                    self.logger.info(f"Stability check {stability_check + 1}/{stable_checks}: size {current_size} bytes")
                    
                    if current_size == last_size and current_size > 0:
                        stable_count += 1
                        if stable_count >= 3:  # File stable for 3 consecutive checks (6 seconds)
                            self.logger.info(f"STABLE: File {newest_file.name} stable at {current_size} bytes")
                            downloaded_file = newest_file
                            break
                    else:
                        stable_count = 0
                        if current_size > last_size:
                            self.logger.info(f"GROWING: File size increased from {last_size} to {current_size}")
                    
                    last_size = current_size
                
                if downloaded_file:
                    break
                else:
                    self.logger.warning(f"File {newest_file.name} did not stabilize, continuing to wait...")
            
            time.sleep(check_interval)
        
        if not downloaded_file:
            # Enhanced error reporting
            final_files = list(self.download_folder.glob("*.xlsx"))
            self.logger.error(f"TIMEOUT: No stable download found after {timeout} seconds")
            self.logger.error(f"Initial files: {[f.name for f in initial_files]}")
            self.logger.error(f"Final files: {[f.name for f in final_files]}")
            
            # Check if any files were created but not stable
            if final_files:
                for f in final_files:
                    if f not in initial_files:
                        size = f.stat().st_size
                        self.logger.error(f"Unstable file found: {f.name} ({size} bytes)")
            
            raise Exception(f"Download timeout after {timeout} seconds - no stable file found")
        
        return downloaded_file
    
    def _set_date_filters_enhanced(self, start_date, end_date):
        """Enhanced date filter setting with validation and debugging"""
        self.logger.info(f"ENHANCED DATE FILTERS: Setting {start_date} to {end_date} for {self.export_type}")
        
        try:
            # Take screenshot before setting dates
            self.driver.save_screenshot(f"before_date_set_{self.export_type}.png")
            
            # Convert and validate date format
            start_formatted = self._validate_and_format_date(start_date)
            end_formatted = self._validate_and_format_date(end_date)
            
            self.logger.info(f"Formatted dates: start={start_formatted}, end={end_formatted}")
            
            # Use export-specific date selectors from config
            start_date_selector = self.export_config["selectors"].get("start_date")
            end_date_selector = self.export_config["selectors"].get("end_date")
            
            self.logger.info(f"Using selectors: start='{start_date_selector}', end='{end_date_selector}'")
            
            # Enhanced field finding and setting
            if start_date_selector:
                start_field = self._find_date_field_enhanced(start_date_selector, "start")
                if start_field:
                    self._set_date_field_value_enhanced(start_field, start_formatted, "start")
            
            if end_date_selector:
                end_field = self._find_date_field_enhanced(end_date_selector, "end")
                if end_field:
                    self._set_date_field_value_enhanced(end_field, end_formatted, "end")
            
            # Take screenshot after setting dates
            self.driver.save_screenshot(f"after_date_set_{self.export_type}.png")
            
            # Wait for any dynamic content to load
            time.sleep(2)
            
        except Exception as e:
            self.logger.error(f"Enhanced date filter setup failed: {str(e)}")
            self.driver.save_screenshot(f"date_filter_error_{self.export_type}.png")
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
            
            # Use export-specific date selectors from config
            start_date_selector = self.export_config["selectors"].get("start_date")
            end_date_selector = self.export_config["selectors"].get("end_date")
            
            # Find start date field using config selector
            start_field = None
            if start_date_selector:
                try:
                    start_field = self.driver.find_element(By.CSS_SELECTOR, start_date_selector)
                except Exception as e:
                    self.logger.warning(f"Could not find start date field with selector {start_date_selector}: {str(e)}")
            
            # Find end date field using config selector
            end_field = None
            if end_date_selector:
                try:
                    end_field = self.driver.find_element(By.CSS_SELECTOR, end_date_selector)
                except Exception as e:
                    self.logger.warning(f"Could not find end date field with selector {end_date_selector}: {str(e)}")
            
            if start_field:
                self._set_date_field_value(start_field, start_formatted, "start")
                self.logger.info(f"Start date set using selector '{start_date_selector}': {start_formatted}")
            else:
                self.logger.error(f"Start date field not found! Selector: {start_date_selector}")
            
            if end_field:
                self._set_date_field_value(end_field, end_formatted, "end")
                self.logger.info(f"End date set using selector '{end_date_selector}': {end_formatted}")
            else:
                self.logger.error(f"End date field not found! Selector: {end_date_selector}")
                
        except Exception as e:
            self.logger.warning(f"Date filter setup failed: {str(e)}")
            # Continue anyway - some exports might not need date filters
    
    def _set_date_field_value(self, field_element, date_value, field_type):
        """Set date field value using multiple methods to ensure proper triggering"""
        try:
            # Method 1: Standard clear + send_keys
            field_element.clear()
            field_element.send_keys(date_value)
            
            # Method 2: JavaScript value setting + trigger events
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
            """, field_element, date_value)
            
            # Give time for any JavaScript validation
            time.sleep(0.5)
            
            # Verify the value was set correctly
            actual_value = field_element.get_attribute('value')
            if actual_value != date_value:
                self.logger.warning(f"Date field {field_type} value mismatch: expected '{date_value}', got '{actual_value}'")
                
                # Method 3: Force setting with JavaScript if mismatch
                self.driver.execute_script("arguments[0].value = arguments[1];", field_element, date_value)
                
            self.logger.info(f"Date field {field_type} set to: {actual_value}")
            
        except Exception as e:
            self.logger.error(f"Failed to set {field_type} date field: {str(e)}")
    
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
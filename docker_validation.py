#!/usr/bin/env python3
"""
Docker Chrome Installation Validation Script
Tests Chrome/Chromium installation and Selenium WebDriver functionality in container environment
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging with Windows UTF-8 support
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Console handler with UTF-8 encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# File handler with UTF-8 encoding
file_handler = logging.FileHandler('docker_validation.log', encoding='utf-8')
file_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger(__name__)

class DockerValidation:
    def __init__(self):
        self.results = {
            "chrome_installation": False,
            "chromedriver_installation": False,
            "selenium_functionality": False,
            "headless_automation": False
        }

    def check_chrome_installation(self):
        """Test Chrome browser installation"""
        logger.info("=== Testing Chrome Installation ===")

        chrome_paths = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/snap/bin/chromium"
        ]

        for path in chrome_paths:
            if os.path.exists(path):
                logger.info(f"[OK] Chrome found at: {path}")
                try:
                    result = subprocess.run([path, "--version"],
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info(f"[OK] Chrome version: {result.stdout.strip()}")
                        self.results["chrome_installation"] = True
                        return path
                except Exception as e:
                    logger.error(f"[FAIL] Chrome execution failed: {str(e)}")

        logger.error("[FAIL] Chrome not found in any expected location")
        return None

    def check_chromedriver_installation(self):
        """Test ChromeDriver installation via WebDriver Manager"""
        logger.info("=== Testing ChromeDriver Installation ===")

        try:
            # Test ChromeDriverManager
            driver_path = ChromeDriverManager().install()
            logger.info(f"[OK] ChromeDriver installed at: {driver_path}")

            # Verify driver exists
            if os.path.exists(driver_path):
                logger.info("[OK] ChromeDriver file verified")
                self.results["chromedriver_installation"] = True
                return driver_path
            else:
                logger.error("[FAIL] ChromeDriver file not found after installation")

        except Exception as e:
            logger.error(f"[FAIL] ChromeDriver installation failed: {str(e)}")

        return None

    def test_selenium_functionality(self):
        """Test basic Selenium WebDriver functionality"""
        logger.info("=== Testing Selenium WebDriver Functionality ===")

        try:
            # Chrome options for headless mode
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")

            # Initialize WebDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            logger.info("✅ WebDriver initialized successfully")

            # Test navigation
            driver.get("https://www.google.com")
            title = driver.title
            logger.info(f"✅ Navigation successful - Page title: {title}")

            # Test element finding
            search_box = driver.find_element("name", "q")
            logger.info("✅ Element finding successful")

            # Test typing
            search_box.send_keys("Docker Chrome Test")
            logger.info("✅ Text input successful")

            driver.quit()
            logger.info("✅ WebDriver cleanup successful")

            self.results["selenium_functionality"] = True
            return True

        except Exception as e:
            logger.error(f"❌ Selenium functionality test failed: {str(e)}")
            return False

    def test_headless_automation(self):
        """Test headless automation capability for backend system"""
        logger.info("=== Testing Headless Automation for Backend System ===")

        try:
            # Enhanced Chrome options for automation
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Download directory setup
            downloads_dir = os.path.abspath("downloads")
            os.makedirs(downloads_dir, exist_ok=True)

            prefs = {
                "download.default_directory": downloads_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)

            # Initialize WebDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            # Test navigation to login-required site (similar to backend)
            driver.get("https://httpbin.org/forms/post")
            logger.info("✅ Navigation to form page successful")

            # Test form filling (simulates login)
            email_field = driver.find_element("name", "custname")
            email_field.send_keys("test@example.com")
            logger.info("✅ Form filling successful")

            # Test JavaScript execution
            result = driver.execute_script("return document.title;")
            logger.info(f"✅ JavaScript execution successful: {result}")

            driver.quit()
            logger.info("✅ Headless automation test completed successfully")

            self.results["headless_automation"] = True
            return True

        except Exception as e:
            logger.error(f"❌ Headless automation test failed: {str(e)}")
            return False

    def run_validation(self):
        """Run complete validation suite"""
        logger.info("🚀 Starting Docker Chrome Validation")
        logger.info("=" * 50)

        # System information
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Environment DISPLAY: {os.getenv('DISPLAY', 'Not set')}")

        # Run all tests
        chrome_path = self.check_chrome_installation()
        driver_path = self.check_chromedriver_installation()

        if chrome_path and driver_path:
            self.test_selenium_functionality()
            self.test_headless_automation()

        # Results summary
        logger.info("=" * 50)
        logger.info("🎯 VALIDATION RESULTS SUMMARY:")
        logger.info("=" * 50)

        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")

        overall_success = all(self.results.values())
        logger.info("=" * 50)
        logger.info(f"🏆 OVERALL RESULT: {'✅ SUCCESS - Docker + Chrome Ready for Deployment' if overall_success else '❌ FAILED - Issues Need Resolution'}")
        logger.info("=" * 50)

        return overall_success

def main():
    """Main validation execution"""
    try:
        validator = DockerValidation()
        success = validator.run_validation()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation failed with unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
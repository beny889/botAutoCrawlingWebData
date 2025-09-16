#!/usr/bin/env python3
"""
Deployment Debug and Validation Script
Tests all dependencies and configurations before actual automation runs
Provides detailed logging for Render.com deployment debugging
"""

import sys
import os
import logging
from pathlib import Path
import json
import traceback

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('deployment_debug.log', mode='w', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_python_environment():
    """Test Python environment and basic functionality"""
    logger.info("=== TESTING PYTHON ENVIRONMENT ===")

    try:
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Python path: {sys.path}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Environment variables count: {len(os.environ)}")

        # Test basic imports
        import json
        import pathlib
        import subprocess
        logger.info("✅ Basic Python imports successful")

        return True

    except Exception as e:
        logger.error(f"❌ Python environment test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_selenium_installation():
    """Test Selenium WebDriver installation and basic functionality"""
    logger.info("=== TESTING SELENIUM INSTALLATION ===")

    try:
        import selenium
        logger.info(f"✅ Selenium version: {selenium.__version__}")
        logger.info(f"Selenium location: {selenium.__file__}")

        from selenium import webdriver
        logger.info("✅ Selenium webdriver import successful")

        from selenium.webdriver.chrome.options import Options
        logger.info("✅ Chrome options import successful")

        from selenium.webdriver.chrome.service import Service
        logger.info("✅ Chrome service import successful")

        from webdriver_manager.chrome import ChromeDriverManager
        logger.info("✅ WebDriver manager import successful")

        return True

    except ImportError as e:
        logger.error(f"❌ Selenium import failed: {e}")
        logger.error("This is the main issue causing deployment failures")
        return False
    except Exception as e:
        logger.error(f"❌ Selenium test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_chrome_installation():
    """Test Chrome browser installation"""
    logger.info("=== TESTING CHROME INSTALLATION ===")

    try:
        import subprocess

        # Test Chrome executable paths
        chrome_paths = [
            '/usr/bin/google-chrome-stable',
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium'
        ]

        chrome_found = False
        for path in chrome_paths:
            if os.path.exists(path):
                logger.info(f"✅ Chrome found at: {path}")
                chrome_found = True

                # Test Chrome version
                try:
                    result = subprocess.run([path, '--version'],
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info(f"Chrome version: {result.stdout.strip()}")
                    else:
                        logger.warning(f"Chrome version check failed: {result.stderr}")
                except Exception as e:
                    logger.warning(f"Could not get Chrome version: {e}")
                break

        if not chrome_found:
            logger.error("❌ Chrome not found in any standard location")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Chrome test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_other_dependencies():
    """Test other critical dependencies"""
    logger.info("=== TESTING OTHER DEPENDENCIES ===")

    dependencies = [
        ('pandas', 'Data processing'),
        ('gspread', 'Google Sheets API'),
        ('google.auth', 'Google authentication'),
        ('openpyxl', 'Excel file handling'),
        ('requests', 'HTTP requests'),
        ('webdriver_manager', 'WebDriver management')
    ]

    all_good = True

    for dep_name, description in dependencies:
        try:
            __import__(dep_name)
            logger.info(f"✅ {dep_name}: {description} - OK")
        except ImportError as e:
            logger.error(f"❌ {dep_name}: {description} - FAILED: {e}")
            all_good = False
        except Exception as e:
            logger.error(f"❌ {dep_name}: {description} - ERROR: {e}")
            all_good = False

    return all_good

def test_environment_variables():
    """Test critical environment variables"""
    logger.info("=== TESTING ENVIRONMENT VARIABLES ===")

    required_vars = [
        'TELEGRAM_TOKEN',
        'TELEGRAM_CHAT_ID',
        'GOOGLE_SERVICE_ACCOUNT_JSON'
    ]

    optional_vars = [
        'CHROME_BIN',
        'DISPLAY',
        'PYTHONUNBUFFERED',
        'DISABLE_NOTIFICATIONS'
    ]

    missing_required = []

    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # Show partial value for security
            if len(value) > 20:
                display_value = f"{value[:10]}...{value[-10:]}"
            else:
                display_value = f"{value[:5]}..."
            logger.info(f"✅ {var}: {display_value}")
        else:
            logger.error(f"❌ {var}: NOT SET")
            missing_required.append(var)

    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            logger.info(f"✅ {var}: {value}")
        else:
            logger.warning(f"⚠️ {var}: Not set (optional)")

    return len(missing_required) == 0

def test_file_system():
    """Test file system access and required directories"""
    logger.info("=== TESTING FILE SYSTEM ===")

    try:
        # Test current directory access
        cwd = Path.cwd()
        logger.info(f"Current directory: {cwd}")

        # Test required files
        required_files = [
            'main_scheduler.py',
            'exports/automation_transaksi.py',
            'shared/backend_connector.py',
            'shared/config.py'
        ]

        missing_files = []
        for file_path in required_files:
            full_path = cwd / file_path
            if full_path.exists():
                logger.info(f"✅ {file_path}: Found")
            else:
                logger.error(f"❌ {file_path}: Missing")
                missing_files.append(file_path)

        # Test directory creation
        test_dirs = ['downloads', 'logs']
        for dir_name in test_dirs:
            dir_path = cwd / dir_name
            try:
                dir_path.mkdir(exist_ok=True)
                logger.info(f"✅ {dir_name}/: Directory OK")
            except Exception as e:
                logger.error(f"❌ {dir_name}/: Cannot create: {e}")
                return False

        return len(missing_files) == 0

    except Exception as e:
        logger.error(f"❌ File system test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def create_service_account_file():
    """Create service account file from environment variable"""
    logger.info("=== CREATING SERVICE ACCOUNT FILE ===")

    try:
        json_content = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not json_content:
            logger.error("❌ GOOGLE_SERVICE_ACCOUNT_JSON not found in environment")
            return False

        # Validate JSON content
        try:
            json_data = json.loads(json_content)
            logger.info("✅ Service account JSON is valid")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
            return False

        # Write to file
        service_file = Path('service-account-key.json')
        service_file.write_text(json_content)
        logger.info(f"✅ Service account file created: {service_file.absolute()}")

        return True

    except Exception as e:
        logger.error(f"❌ Service account file creation failed: {e}")
        logger.error(traceback.format_exc())
        return False

def run_comprehensive_test():
    """Run all tests and provide comprehensive report"""
    logger.info("🚀 STARTING COMPREHENSIVE DEPLOYMENT DEBUG")
    logger.info("=" * 60)

    tests = [
        ("Python Environment", test_python_environment),
        ("Selenium Installation", test_selenium_installation),
        ("Chrome Installation", test_chrome_installation),
        ("Other Dependencies", test_other_dependencies),
        ("Environment Variables", test_environment_variables),
        ("File System", test_file_system),
        ("Service Account", create_service_account_file)
    ]

    results = {}

    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: EXCEPTION: {e}")
            results[test_name] = False

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 FINAL TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - DEPLOYMENT SHOULD WORK!")
        return True
    else:
        logger.error("💥 SOME TESTS FAILED - FIX ISSUES BEFORE DEPLOYMENT")
        return False

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Debug script failed with exception: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
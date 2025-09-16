"""
Centralized configuration for all export automation tasks
"""

import os

class ExportConfig:
    """Configuration class for export automation"""
    
    # Backend credentials - SECURE: Environment variables only
    USERNAME = os.getenv('BACKEND_USERNAME')
    PASSWORD = os.getenv('BACKEND_PASSWORD')
    
    # Telegram notification credentials - SECURE: Environment variables only
    # Set DISABLE_NOTIFICATIONS=true to disable Telegram notifications during testing
    DISABLE_NOTIFICATIONS = True  # Force disabled during development/testing
    TELEGRAM_TOKEN = None if DISABLE_NOTIFICATIONS else os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = None if DISABLE_NOTIFICATIONS else os.getenv('TELEGRAM_CHAT_ID')
    
    # Google Service Account Configuration
    @classmethod
    def get_service_account_info(cls):
        """Get Google service account info from environment or file"""
        import json
        import tempfile
        import os
        
        # Try environment variable first (for cloud deployment)
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if service_account_json:
            try:
                # PRECISE JSON cleaning to handle escape character issues while preserving base64 content
                import re
                import json as json_module

                print(f"DEBUG: Raw JSON length: {len(service_account_json)}")
                print(f"DEBUG: Character at position 568: '{service_account_json[567:570] if len(service_account_json) > 568 else 'N/A'}'")

                # Clean and fix JSON formatting issues
                json_content = service_account_json.strip()

                # Remove outer quotes if present
                if json_content.startswith('"') and json_content.endswith('"'):
                    json_content = json_content[1:-1]

                print(f"DEBUG: Before fixing - chars 565-570: '{json_content[565:570] if len(json_content) > 570 else 'N/A'}'")

                # PRECISE APPROACH: Only fix literal newlines that break JSON structure
                # Preserve all base64 content in private_key field exactly as-is

                try:
                    # Method 1: Simple global newline replacement (preserves everything else)
                    test_content = json_content.replace('\n', '\\n')
                    parsed = json_module.loads(test_content)
                    print("DEBUG: Simple global newline escape successful")
                    return parsed

                except json_module.JSONDecodeError as e:
                    print(f"DEBUG: Simple approach failed with error: {e}")
                    print(f"DEBUG: Error at position: {getattr(e, 'pos', 'unknown')}")

                    # Method 2: Only fix problematic escape sequences, preserve base64
                    try:
                        # Fix only the specific characters that cause JSON parsing issues
                        # Don't touch anything that looks like base64 content
                        fixed_content = json_content

                        # Replace literal newlines with escaped newlines
                        fixed_content = fixed_content.replace('\n', '\\n')

                        # Fix any double backslashes that might have been created
                        fixed_content = fixed_content.replace('\\\\n', '\\n')

                        # Remove carriage returns (these definitely break JSON)
                        fixed_content = fixed_content.replace('\r', '')

                        print(f"DEBUG: After precise fix - length: {len(fixed_content)}")
                        print(f"DEBUG: After fix - chars 565-570: '{fixed_content[565:570] if len(fixed_content) > 570 else 'N/A'}'")

                        parsed = json_module.loads(fixed_content)
                        print("DEBUG: Precise fix method successful")
                        return parsed

                    except json_module.JSONDecodeError as e2:
                        print(f"DEBUG: Precise fix also failed: {e2}")
                        print(f"DEBUG: Error position: {getattr(e2, 'pos', 'unknown')}")

                        # Method 3: Parse and reconstruct JSON safely
                        # This is a last resort that rebuilds the JSON structure
                        raise ValueError(f"Unable to parse Google Service Account JSON after multiple fix attempts. Original error: {e}, Precise fix error: {e2}")
            except json.JSONDecodeError as e:
                raise ValueError(f"GOOGLE_SERVICE_ACCOUNT_JSON environment variable contains invalid JSON: {e}")
        
        # Fallback to local file (for development)
        service_account_file = "service-account-key.json"
        if os.path.exists(service_account_file):
            with open(service_account_file, 'r') as f:
                return json.load(f)
        
        raise FileNotFoundError(
            "Google service account credentials not found. "
            "Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable or place service-account-key.json file."
        )
    
    # Validate critical environment variables
    @classmethod
    def validate_environment(cls):
        """Validate that all required environment variables are set"""
        missing_vars = []
        
        if not cls.USERNAME:
            missing_vars.append('BACKEND_USERNAME')
        if not cls.PASSWORD:
            missing_vars.append('BACKEND_PASSWORD')
        
        # Only require Telegram credentials if notifications are enabled
        if not cls.DISABLE_NOTIFICATIONS:
            if not cls.TELEGRAM_TOKEN:
                missing_vars.append('TELEGRAM_TOKEN')
            if not cls.TELEGRAM_CHAT_ID:
                missing_vars.append('TELEGRAM_CHAT_ID')
        
        # Validate Google service account (with deployment mode bypass)
        import os
        skip_validation = os.getenv('SKIP_STRICT_VALIDATION') == 'true'

        if not skip_validation:
            try:
                cls.get_service_account_info()
            except (FileNotFoundError, ValueError) as e:
                missing_vars.append('GOOGLE_SERVICE_ACCOUNT_JSON or service-account-key.json file')
        else:
            print("INFO: Skipping strict service account validation in deployment mode")

        if missing_vars and not skip_validation:
            raise EnvironmentError(
                f"Missing required environment variables or files: {', '.join(missing_vars)}. "
                f"Please set these variables before running the automation."
            )
        
        return True
    
    # Backend base URL
    BACKEND_BASE_URL = "https://backend.andalanatk.com"
    
    # Export configurations - ALL EXPORTS ENABLED
    EXPORTS = {
        "transaksi": {
            "name": "Transaction Export",
            "url": f"{BACKEND_BASE_URL}/transaksi/index-export",
            "google_sheet_url": "https://docs.google.com/spreadsheets/d/1dhLTUzUQ1ug4KPjU0Q8A8x38IioW5ZwKvVEIYHqf7aw",
            "unique_key": "Transaksi ID",
            "requires_date_filter": True,
            "file_prefix": "export_transaksi",
            "file_type": "excel",
            "selectors": {
                "start_date": 'input[name="start_date"]',
                "end_date": 'input[name="end_date"]',
                "export_button": 'button.btn.btn-primary',
                "export_button_xpath": '//button[contains(text(), "Export")]',
                "date_format": "YYYY-MM-DD"
            }
        },
        "point_trx": {
            "name": "Point Transaction Export",
            "url": f"{BACKEND_BASE_URL}/point_transaction",
            "google_sheet_url": "https://docs.google.com/spreadsheets/d/1sI_89ZVXa7zgxVuCwSLc3Q7eBZtZqOhGVPMjQCJ51wU",
            "unique_key": "Point Transaction ID",
            "requires_date_filter": True,
            "file_prefix": "export_point_trx",
            "file_type": "excel",
            "selectors": {
                "start_date": 'input[name="start"]',
                "end_date": 'input[name="end"]',
                "export_button": 'button.btn.btn-success.m3.expot-pdf',
                "date_format": "YYYY-MM-DD"
            }
        },
        "user": {
            "name": "User Data Export",
            "url": f"{BACKEND_BASE_URL}/user-front",
            "google_sheet_url": "https://docs.google.com/spreadsheets/d/1CLKjcByabVe6-8hTTcP6JtE56WulHIEOPkyHTQ2l0e8",
            "unique_key": "User ID",
            "requires_date_filter": True,
            "file_prefix": "export_user",
            "file_type": "excel",
            "selectors": {
                "start_date": 'input[id="filter-start"]',
                "end_date": 'input[id="filter-end"]',
                "export_button": 'button.btn.btn-success.m3.expot-pdf',
                "date_format": "YYYY-MM-DD"
            }
        },
        
        # All exports now enabled
        "pembayaran_koin": {
            "name": "Coin Payment Export",
            "url": f"{BACKEND_BASE_URL}/koin_pay",
            "google_sheet_url": "https://docs.google.com/spreadsheets/d/1KWEMz3R5N1EnlS9NdJS9NiQRUsBuTAIfEoaYpS2NhAk", 
            "unique_key": "Payment ID",
            "requires_date_filter": True,
            "file_prefix": "export_pembayaran_koin",
            "file_type": "excel",
            "selectors": {
                "start_date": 'input[id="filter-start"]',
                "end_date": 'input[id="filter-end"]',
                "export_button": 'button.btn.btn-success.m3.expot-pdf',
                "date_format": "YYYY-MM-DD"
            }
        }
    }
    
    # Google API settings
    SERVICE_ACCOUNT_FILE = "service-account-key.json"
    GOOGLE_API_SCOPES = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Browser settings - Production Ready Configuration
    BROWSER_CONFIG = {
        "headless": True,   # Default to headless for production
        "slow_mo": 0,       # No delays for optimal performance
        "timeout": 90000    # Default timeout
    }
    
    # Development override settings
    DEBUG_BROWSER_CONFIG = {
        "headless": False,  # Show browser for debugging
        "slow_mo": 1000,    # Add delays for visual debugging
        "timeout": 90000    # Same timeout
    }
    
    @classmethod
    def get_browser_config(cls, headless=None, debug=False, production=False):
        """Get browser configuration with runtime overrides"""
        if debug:
            config = cls.DEBUG_BROWSER_CONFIG.copy()
        else:
            config = cls.BROWSER_CONFIG.copy()
            
        # Override headless setting if specified
        if headless is not None:
            config["headless"] = headless
            
        # Production mode optimizations
        if production:
            config["headless"] = True
            config["slow_mo"] = 0
            
        return config
    
    # File management
    DOWNLOADS_FOLDER = "downloads"
    LOGS_FOLDER = "logs"
    CLEANUP_DAYS = 7
    
    # Selectors (common across exports)
    LOGIN_SELECTORS = {
        "username": '[name="email"]',
        "password": '[name="password"]',
        "submit": '.btn.btn-primary.btn-block.waves-effect.waves-light',
        "submit_xpath": '//button[contains(text(), "Log In") or @type="submit"]'
    }
    
    @classmethod
    def get_export_config(cls, export_type: str):
        """Get configuration for specific export type"""
        if export_type not in cls.EXPORTS:
            raise ValueError(f"Unknown export type: {export_type}")
        return cls.EXPORTS[export_type]
    
    @classmethod
    def get_all_export_types(cls):
        """Get list of all available export types"""
        return list(cls.EXPORTS.keys())
"""
User Data export automation using Selenium
"""

import logging
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.backend_connector import BackendConnector
from shared.sheets_manager import SheetsManager
from shared.config import ExportConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation_user.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class UserExportAutomation:
    """User Data export automation with smart data validation"""
    
    def __init__(self):
        self.export_type = "user"
        self.connector = BackendConnector(self.export_type)
        self.sheets_manager = SheetsManager(self.export_type)
        self.logger = logging.getLogger(__name__)
    
    def run_export(self):
        """Run the complete user data export process (no date filtering needed)"""
        try:
            self.logger.info("Starting user data export (full user list)")
            
            # Setup browser
            self.connector.setup_browser()
            
            # Login to backend
            self.connector.login_to_backend()
            
            # Navigate to export page
            self.connector.navigate_to_export_page()
            
            # Download export file (no date filtering for user data)
            downloaded_file = self.connector.download_export_file()
            
            # Upload to Google Sheets with smart validation
            upload_result = self.sheets_manager.upload_with_smart_validation(downloaded_file)

            # Cleanup old files
            self.connector.cleanup_old_files()

            # Handle new return format
            if isinstance(upload_result, dict):
                success = upload_result.get("success", False)
                records = upload_result.get("records", 0)
                self.logger.info(f"User data export completed! Success: {success}, Records: {records}")
                return upload_result
            else:
                # Legacy return format (boolean)
                self.logger.info("User data export completed successfully!")
                return {"success": upload_result, "records": 0}
            
        except Exception as e:
            self.logger.error(f"User data export failed: {str(e)}")
            return {"success": False, "records": 0, "error": str(e)}
        
        finally:
            # Cleanup browser resources
            self.connector.cleanup()

# Convenience function
def run_user_export():
    """Export complete user data"""
    automation = UserExportAutomation()
    return automation.run_export()

# Main execution
if __name__ == "__main__":
    automation = UserExportAutomation()
    automation.run_export()
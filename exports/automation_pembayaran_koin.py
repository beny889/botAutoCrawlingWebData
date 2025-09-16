"""
Coin Payment export automation using Selenium
"""

import logging
from datetime import datetime, timedelta
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
        logging.FileHandler('logs/automation_pembayaran_koin.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class PembayaranKoinExportAutomation:
    """Coin Payment export automation with smart data validation"""
    
    def __init__(self):
        self.export_type = "pembayaran_koin"
        self.connector = BackendConnector(self.export_type)
        self.sheets_manager = SheetsManager(self.export_type)
        self.logger = logging.getLogger(__name__)
    
    def run_export(self, start_date=None, end_date=None):
        """Run the complete coin payment export process"""
        try:
            # Default to yesterday if no dates provided
            if not start_date:
                yesterday = datetime.now() - timedelta(days=1)
                start_date = yesterday.strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            self.logger.info(f"Starting coin payment export for date range: {start_date} to {end_date}")
            
            # Setup browser
            self.connector.setup_browser()
            
            # Login to backend
            self.connector.login_to_backend()
            
            # Navigate to export page
            self.connector.navigate_to_export_page()
            
            # Download export file
            downloaded_file = self.connector.download_export_file(start_date, end_date)
            
            # Upload to Google Sheets with smart validation
            upload_result = self.sheets_manager.upload_with_smart_validation(downloaded_file)

            # Cleanup old files
            self.connector.cleanup_old_files()

            # Handle new return format
            if isinstance(upload_result, dict):
                success = upload_result.get("success", False)
                records = upload_result.get("records", 0)
                self.logger.info(f"Coin payment export completed! Success: {success}, Records: {records}")
                return upload_result
            else:
                # Legacy return format (boolean)
                self.logger.info("Coin payment export completed successfully!")
                return {"success": upload_result, "records": 0}

        except Exception as e:
            self.logger.error(f"Coin payment export failed: {str(e)}")
            return {"success": False, "records": 0, "error": str(e)}
        
        finally:
            # Cleanup browser resources
            self.connector.cleanup()

# Convenience functions
def run_today():
    """Export coin payment data for today"""
    automation = PembayaranKoinExportAutomation()
    today = datetime.now().strftime("%Y-%m-%d")
    return automation.run_export(today, today)

def run_yesterday():
    """Export coin payment data for yesterday"""
    automation = PembayaranKoinExportAutomation()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return automation.run_export(yesterday, yesterday)

def run_date_range(start_date, end_date):
    """Export coin payment data for specific date range"""
    automation = PembayaranKoinExportAutomation()
    return automation.run_export(start_date, end_date)

# Main execution
if __name__ == "__main__":
    automation = PembayaranKoinExportAutomation()
    # Test with yesterday's data
    automation.run_export()
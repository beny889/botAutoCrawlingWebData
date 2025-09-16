"""
Transaction export automation - refactored with modular architecture using Selenium
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
        logging.FileHandler('logs/automation_transaksi.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class TransaksiExportAutomation:
    """Transaction export automation with smart data validation"""
    
    def __init__(self):
        self.export_type = "transaksi"
        self.connector = BackendConnector(self.export_type)
        self.sheets_manager = SheetsManager(self.export_type)
        self.logger = logging.getLogger(__name__)
    
    def run_export(self, start_date=None, end_date=None):
        """Run the complete transaction export process"""
        try:
            # Default to yesterday if no dates provided
            if not start_date:
                yesterday = datetime.now() - timedelta(days=1)
                start_date = yesterday.strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            self.logger.info(f"Starting transaction export for date range: {start_date} to {end_date}")
            
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
                self.logger.info(f"Transaction export completed! Success: {success}, Records: {records}")
                return upload_result
            else:
                # Legacy return format (boolean)
                self.logger.info("Transaction export completed successfully!")
                return {"success": upload_result, "records": 0}

        except Exception as e:
            self.logger.error(f"Transaction export failed: {str(e)}")
            return {"success": False, "records": 0, "error": str(e)}
        
        finally:
            # Cleanup browser resources
            self.connector.cleanup()

# Convenience functions for different use cases
def run_today():
    """Export transaction data for today"""
    automation = TransaksiExportAutomation()
    today = datetime.now().strftime("%Y-%m-%d")
    return automation.run_export(today, today)

def run_yesterday():
    """Export transaction data for yesterday"""
    automation = TransaksiExportAutomation()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return automation.run_export(yesterday, yesterday)

def run_date_range(start_date, end_date):
    """Export transaction data for specific date range"""
    automation = TransaksiExportAutomation()
    return automation.run_export(start_date, end_date)

def run_last_week():
    """Export transaction data for last 7 days"""
    automation = TransaksiExportAutomation()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    return automation.run_export(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )

# Main execution
if __name__ == "__main__":
    # Test with specific date
    automation = TransaksiExportAutomation()
    automation.run_export("2025-09-08", "2025-09-08")
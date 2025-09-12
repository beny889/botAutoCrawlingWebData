"""
Point Transaction export automation
"""

import asyncio
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
        logging.FileHandler('logs/automation_point_trx.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class PointTrxExportAutomation:
    """Point Transaction export automation with smart data validation"""
    
    def __init__(self):
        self.export_type = "point_trx"
        self.connector = BackendConnector(self.export_type)
        self.sheets_manager = SheetsManager(self.export_type)
        self.logger = logging.getLogger(__name__)
    
    async def run_export(self, start_date=None, end_date=None):
        """Run the complete point transaction export process"""
        try:
            # Default to yesterday if no dates provided
            if not start_date:
                yesterday = datetime.now() - timedelta(days=1)
                start_date = yesterday.strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            self.logger.info(f"Starting point transaction export for date range: {start_date} to {end_date}")
            
            # Setup browser
            await self.connector.setup_browser()
            
            # Login to backend
            await self.connector.login_to_backend()
            
            # Navigate to export page
            await self.connector.navigate_to_export_page()
            
            # Download export file
            downloaded_file = await self.connector.download_export_file(start_date, end_date)
            
            # Upload to Google Sheets with smart validation
            self.sheets_manager.upload_with_smart_validation(downloaded_file)
            
            # Cleanup old files
            self.connector.cleanup_old_files()
            
            self.logger.info("Point transaction export completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Point transaction export failed: {str(e)}")
            return False
        
        finally:
            # Cleanup browser resources
            await self.connector.cleanup()

# Convenience functions
async def run_today():
    """Export point transaction data for today"""
    automation = PointTrxExportAutomation()
    today = datetime.now().strftime("%Y-%m-%d")
    return await automation.run_export(today, today)

async def run_yesterday():
    """Export point transaction data for yesterday"""
    automation = PointTrxExportAutomation()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return await automation.run_export(yesterday, yesterday)

async def run_date_range(start_date, end_date):
    """Export point transaction data for specific date range"""
    automation = PointTrxExportAutomation()
    return await automation.run_export(start_date, end_date)

# Main execution
if __name__ == "__main__":
    automation = PointTrxExportAutomation()
    # Test with yesterday's data
    asyncio.run(automation.run_export())
"""
User Data export automation
"""

import asyncio
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
    
    async def run_export(self):
        """Run the complete user data export process (no date filtering needed)"""
        try:
            self.logger.info("Starting user data export (full user list)")
            
            # Setup browser
            await self.connector.setup_browser()
            
            # Login to backend
            await self.connector.login_to_backend()
            
            # Navigate to export page
            await self.connector.navigate_to_export_page()
            
            # Download export file (no date filtering for user data)
            downloaded_file = await self.connector.download_export_file()
            
            # Upload to Google Sheets with smart validation
            self.sheets_manager.upload_with_smart_validation(downloaded_file)
            
            # Cleanup old files
            self.connector.cleanup_old_files()
            
            self.logger.info("User data export completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"User data export failed: {str(e)}")
            return False
        
        finally:
            # Cleanup browser resources
            await self.connector.cleanup()

# Convenience function
async def run_user_export():
    """Export complete user data"""
    automation = UserExportAutomation()
    return await automation.run_export()

# Main execution
if __name__ == "__main__":
    automation = UserExportAutomation()
    asyncio.run(automation.run_export())
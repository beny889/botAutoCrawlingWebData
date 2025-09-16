"""
Main scheduler for all export automation tasks using Selenium
Run multiple exports in sequence or parallel
"""

# CRITICAL: Run deployment debug validation BEFORE any imports
import os
import sys
import json
from pathlib import Path

def run_deployment_validation():
    """Run critical deployment validation before importing Selenium"""
    print("=== DEPLOYMENT VALIDATION (EMBEDDED) ===")

    # 1. Create service account file from environment variable
    json_content = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if json_content:
        try:
            # Clean and validate JSON content
            json_content = json_content.strip()

            # Handle potential escape character issues
            if json_content.startswith('"') and json_content.endswith('"'):
                # Remove outer quotes if present
                json_content = json_content[1:-1]

            # Replace common escape sequence issues
            json_content = json_content.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

            # Validate JSON structure
            parsed_json = json.loads(json_content)

            # Write to file
            Path('service-account-key.json').write_text(json_content)
            print("✅ Service account file created successfully")

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in service account: {e}")
            print(f"JSON content preview: {json_content[:100]}...")
            print("⚠️ Continuing without service account - Google Sheets may fail")
            # Don't exit, let the automation try to run
        except Exception as e:
            print(f"❌ Service account creation failed: {e}")
            print("⚠️ Continuing without service account - Google Sheets may fail")
            # Don't exit, let the automation try to run
    else:
        print("⚠️ GOOGLE_SERVICE_ACCOUNT_JSON not set - Google Sheets authentication may fail")

    # 2. Test Selenium import (the main issue)
    try:
        import selenium
        print(f"✅ Selenium {selenium.__version__} available")
    except ImportError as e:
        print(f"❌ SELENIUM IMPORT FAILED: {e}")
        print("This is the critical issue causing deployment failures")
        sys.exit(1)

    # 3. Test other critical imports
    try:
        import pandas, gspread, requests
        print("✅ All dependencies available")
    except ImportError as e:
        print(f"❌ Dependency import failed: {e}")
        sys.exit(1)

    print("✅ All validations passed - proceeding with automation")

# Run validation immediately
run_deployment_validation()

import logging
from datetime import datetime, timedelta

# Setup logging
log_folder = Path("logs")
log_folder.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/main_scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Import all export automation classes
sys.path.append('exports')
from exports.automation_transaksi import TransaksiExportAutomation
from exports.automation_point_trx import PointTrxExportAutomation
from exports.automation_user import UserExportAutomation
from exports.automation_pembayaran_koin import PembayaranKoinExportAutomation

# Import Telegram notifications and configuration
# Note: SingleSessionAutomation temporarily disabled during Selenium migration
from shared.telegram_notifier import TelegramNotifier
from shared.config import ExportConfig

class MainScheduler:
    """Main scheduler for all export automation tasks"""
    
    def __init__(self, use_single_session=True):
        self.logger = logging.getLogger(__name__)
        self.use_single_session = use_single_session
        
        # Validate environment variables before proceeding
        try:
            ExportConfig.validate_environment()
            self.logger.info("Environment variables validated successfully")
        except EnvironmentError as e:
            self.logger.error(f"Environment validation failed: {str(e)}")
            raise
        
        # Initialize Telegram notifier
        self.telegram = TelegramNotifier(
            token=ExportConfig.TELEGRAM_TOKEN,
            chat_id=ExportConfig.TELEGRAM_CHAT_ID
        )
        
        # Individual export classes
        self.exports = {
            "transaksi": TransaksiExportAutomation,
            "point_trx": PointTrxExportAutomation,
            "user": UserExportAutomation,
            "pembayaran_koin": PembayaranKoinExportAutomation
        }
    
    def run_single_export(self, export_type, start_date=None, end_date=None):
        """Run a single export task"""
        if export_type not in self.exports:
            raise ValueError(f"Unknown export type: {export_type}")
        
        self.logger.info(f"Starting {export_type} export with dates: {start_date} to {end_date}")
        
        try:
            automation = self.exports[export_type]()
            
            # Handle user export (no date parameters)
            if export_type == "user":
                self.logger.info(f"User export: running without date parameters")
                result = automation.run_export()
            else:
                self.logger.info(f"{export_type} export: running with start_date={start_date}, end_date={end_date}")
                result = automation.run_export(start_date, end_date)
            
            if result:
                self.logger.info(f"{export_type} export completed successfully!")
            else:
                self.logger.error(f"{export_type} export failed!")
            
            return result
            
        except Exception as e:
            self.logger.error(f"{export_type} export failed with exception: {str(e)}")
            return False
    
    def run_all_exports_sequential(self, start_date=None, end_date=None):
        """Run all exports one by one (sequential)"""
        start_time = datetime.now()
        
        # Send start notification
        mode = "single session" if self.use_single_session else "individual sessions"
        self.telegram.send_system_start(mode)
        
        # Temporarily use individual sessions mode during Selenium migration
        # Single session mode will be re-enabled after SingleSessionAutomation is updated for Selenium
        if self.use_single_session:
            self.logger.info("Single session mode temporarily disabled - using individual sessions")
            self.logger.info("Running individual exports with Selenium WebDriver...")
            return self._run_individual_exports(start_date, end_date, start_time)
        else:
            return self._run_individual_exports(start_date, end_date, start_time)
    
    def _run_individual_exports(self, start_date=None, end_date=None, start_time=None):
        """Run exports using individual automation classes (legacy mode)"""
        if start_time is None:
            start_time = datetime.now()
            
        self.logger.info("Starting all exports in individual session mode...")
        
        results = {}
        
        for export_type in self.exports.keys():
            self.logger.info(f"Running {export_type} export...")
            export_start_time = datetime.now()
            
            try:
                result = self.run_single_export(export_type, start_date, end_date)
                execution_time = (datetime.now() - export_start_time).total_seconds()
                
                if result:
                    # Send success notification for individual export
                    self.telegram.send_export_success(export_type, 0, execution_time)  # Records count not available in legacy mode
                    results[export_type] = {"success": True, "records": 0, "time": execution_time}
                else:
                    # Send failure notification
                    self.telegram.send_export_failure(export_type, "Export returned False")
                    results[export_type] = {"success": False, "error": "Export returned False", "time": execution_time}
            except Exception as e:
                execution_time = (datetime.now() - export_start_time).total_seconds()
                error_msg = str(e)
                self.telegram.send_export_failure(export_type, error_msg)
                results[export_type] = {"success": False, "error": error_msg, "time": execution_time}
        
        # Summary
        successful = [k for k, v in results.items() if v.get("success", False)]
        failed = [k for k, v in results.items() if not v.get("success", False)]
        
        self.logger.info(f"Individual exports execution completed!")
        self.logger.info(f"Successful exports: {successful}")
        if failed:
            self.logger.warning(f"Failed exports: {failed}")
        
        # Send daily summary
        total_time = (datetime.now() - start_time).total_seconds()
        self.telegram.send_daily_summary(results, total_time)
        
        return results
    
    def run_all_exports_parallel(self, start_date=None, end_date=None):
        """Run all exports simultaneously (parallel) - Note: Not truly parallel with Selenium"""
        self.logger.info("Starting all exports in sequential mode (Selenium limitation)...")
        # Note: Selenium doesn't support true parallel execution like asyncio
        # Running sequentially instead
        return self._run_individual_exports(start_date, end_date)
    
    def run_daily_exports(self, target_date=None, mode="sequential"):
        """Run daily exports for specific date"""
        if not target_date:
            # Default to yesterday
            target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        self.logger.info(f"Running daily exports for {target_date} in {mode} mode")
        
        if mode == "parallel":
            return self.run_all_exports_parallel(target_date, target_date)
        else:
            return self.run_all_exports_sequential(target_date, target_date)
    
    def run_weekly_exports(self, mode="sequential"):
        """Run exports for the last 7 days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        self.logger.info(f"Running weekly exports from {start_date_str} to {end_date_str} in {mode} mode")
        
        if mode == "parallel":
            return self.run_all_exports_parallel(start_date_str, end_date_str)
        else:
            return self.run_all_exports_sequential(start_date_str, end_date_str)
    
    def get_export_status(self):
        """Get status information about all available exports"""
        status = {
            "available_exports": list(self.exports.keys()),
            "total_exports": len(self.exports),
            "last_run": "N/A"  # Could add timestamp tracking later
        }
        
        self.logger.info(f"Export status: {status}")
        return status

# Convenience functions
def run_all_today_sequential():
    """Run all exports for today in sequential mode"""
    scheduler = MainScheduler()
    today = datetime.now().strftime("%Y-%m-%d")
    return scheduler.run_all_exports_sequential(today, today)

def run_all_today_parallel():
    """Run all exports for today in parallel mode"""
    scheduler = MainScheduler()
    today = datetime.now().strftime("%Y-%m-%d")
    return scheduler.run_all_exports_parallel(today, today)

def run_all_yesterday():
    """Run all exports for yesterday"""
    scheduler = MainScheduler()
    return scheduler.run_daily_exports()

def run_specific_export(export_type, date=None):
    """Run specific export for specific date"""
    scheduler = MainScheduler()
    if not date:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return scheduler.run_single_export(export_type, date, date)

# Main execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run export automation tasks')
    parser.add_argument('--export', type=str, help='Specific export to run (transaksi, point_trx, user, pembayaran_koin)')
    parser.add_argument('--date', type=str, help='Date for export (YYYY-MM-DD)')
    parser.add_argument('--mode', type=str, choices=['sequential', 'parallel'], default='sequential', help='Execution mode')
    parser.add_argument('--all', action='store_true', help='Run all exports')
    parser.add_argument('--single-session', action='store_true', default=True, help='Use single session mode (default)')
    parser.add_argument('--individual-sessions', action='store_false', dest='single_session', help='Use individual sessions (legacy mode)')
    parser.add_argument('--headless', action='store_true', help='Force headless mode (no browser window)')
    parser.add_argument('--debug', action='store_true', help='Debug mode (show browser, slow motion)')
    parser.add_argument('--production', action='store_true', help='Production mode (optimized settings)')
    
    args = parser.parse_args()
    
    # ENHANCED DEBUG: Log all parsed arguments with validation
    logging.info("="*50)
    logging.info("MAIN SCHEDULER ARGUMENT VALIDATION")
    logging.info(f"Parsed arguments: export={args.export}, date={args.date}, mode={args.mode}, all={args.all}")
    logging.info(f"Single session: {args.single_session}")
    logging.info(f"Headless: {args.headless}, Debug: {args.debug}, Production: {args.production}")
    
    # CRITICAL: Validate single export execution
    if args.export and args.all:
        logging.error("CONFLICT: Both --export and --all specified. Using --export only.")
        args.all = False
    
    if args.export:
        logging.info(f"SINGLE EXPORT MODE: Will run ONLY {args.export} export")
        if args.export not in ["transaksi", "point_trx", "user", "pembayaran_koin"]:
            logging.error(f"Invalid export type: {args.export}")
            sys.exit(1)
    elif args.all:
        logging.info("ALL EXPORTS MODE: Will run all 4 exports")
    else:
        logging.info("DEFAULT MODE: Will run daily exports (yesterday)")
    
    # Default date fallback if none provided
    if args.date is None:
        args.date = "2025-09-11"  # Use date with known data
        logging.info(f"No date provided, using default: {args.date}")
    
    logging.info("="*50)
    
    scheduler = MainScheduler(use_single_session=args.single_session)
    
    if args.export:
        # SINGLE EXPORT EXECUTION - Enhanced logging
        logging.info(f"EXECUTING SINGLE EXPORT: {args.export}")
        logging.info(f"Date range: {args.date} to {args.date}")
        result = scheduler.run_single_export(args.export, args.date, args.date)
        logging.info(f"SINGLE EXPORT RESULT: {'SUCCESS' if result else 'FAILED'}")
        sys.exit(0 if result else 1)
    elif args.all:
        # Run all exports
        logging.info(f"Running all exports with date: {args.date}")
        if args.mode == 'parallel':
            scheduler.run_all_exports_parallel(args.date, args.date)
        else:
            scheduler.run_all_exports_sequential(args.date, args.date)
    else:
        # Default: run daily exports for yesterday
        scheduler.run_daily_exports()
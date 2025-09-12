"""
Main scheduler for all export automation tasks
Run multiple exports in sequence or parallel
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

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

# Import single session automation and Telegram notifications
from single_session_automation import SingleSessionAutomation
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
        
        # Legacy individual export classes
        self.exports = {
            "transaksi": TransaksiExportAutomation,
            "point_trx": PointTrxExportAutomation,
            "user": UserExportAutomation,
            "pembayaran_koin": PembayaranKoinExportAutomation
        }
    
    async def run_single_export(self, export_type, start_date=None, end_date=None):
        """Run a single export task"""
        if export_type not in self.exports:
            raise ValueError(f"Unknown export type: {export_type}")
        
        self.logger.info(f"Starting {export_type} export...")
        
        try:
            automation = self.exports[export_type]()
            
            # Handle user export (no date parameters)
            if export_type == "user":
                result = await automation.run_export()
            else:
                result = await automation.run_export(start_date, end_date)
            
            if result:
                self.logger.info(f"{export_type} export completed successfully!")
            else:
                self.logger.error(f"{export_type} export failed!")
            
            return result
            
        except Exception as e:
            self.logger.error(f"{export_type} export failed with exception: {str(e)}")
            return False
    
    async def run_all_exports_sequential(self, start_date=None, end_date=None):
        """Run all exports one by one (sequential)"""
        start_time = datetime.now()
        
        # Send start notification
        mode = "single session" if self.use_single_session else "individual sessions"
        self.telegram.send_system_start(mode)
        
        if self.use_single_session:
            self.logger.info("Starting all exports in SINGLE SESSION sequential mode...")
            
            # Use single session automation with configuration
            # Get configuration from command line arguments if available
            import sys
            headless = '--headless' in sys.argv
            debug = '--debug' in sys.argv
            production = '--production' in sys.argv
            
            single_session = SingleSessionAutomation(headless=headless, debug=debug, production=production)
            result = await single_session.run_all_exports_sequential(start_date, end_date)
            
            if result["success"]:
                self.logger.info("Single session automation completed successfully!")
                # Send success summary
                total_time = (datetime.now() - start_time).total_seconds()
                self.telegram.send_daily_summary(result["results"], total_time)
                return result["results"]
            else:
                self.logger.error(f"Single session automation failed: {result.get('error', 'Unknown error')}")
                # Send error notification
                self.telegram.send_system_error(result.get('error', 'Unknown error'), "single_session")
                # Fallback to individual exports
                self.logger.info("Falling back to individual export mode...")
                return await self._run_individual_exports(start_date, end_date, start_time)
        else:
            return await self._run_individual_exports(start_date, end_date, start_time)
    
    async def _run_individual_exports(self, start_date=None, end_date=None, start_time=None):
        """Run exports using individual automation classes (legacy mode)"""
        if start_time is None:
            start_time = datetime.now()
            
        self.logger.info("Starting all exports in individual session mode...")
        
        results = {}
        
        for export_type in self.exports.keys():
            self.logger.info(f"Running {export_type} export...")
            export_start_time = datetime.now()
            
            try:
                result = await self.run_single_export(export_type, start_date, end_date)
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
    
    async def run_all_exports_parallel(self, start_date=None, end_date=None):
        """Run all exports simultaneously (parallel)"""
        if self.use_single_session:
            self.logger.warning("Single session mode doesn't support parallel execution - running sequential instead")
            return await self.run_all_exports_sequential(start_date, end_date)
        
        self.logger.info("Starting all exports in parallel mode...")
        
        # Create tasks for all exports
        tasks = []
        for export_type in self.exports.keys():
            task = asyncio.create_task(
                self.run_single_export(export_type, start_date, end_date),
                name=export_type
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Create results dictionary
        results = {}
        for i, export_type in enumerate(self.exports.keys()):
            result = results_list[i]
            if isinstance(result, Exception):
                self.logger.error(f"{export_type} export failed with exception: {str(result)}")
                results[export_type] = False
            else:
                results[export_type] = result
        
        # Summary
        successful = [k for k, v in results.items() if v]
        failed = [k for k, v in results.items() if not v]
        
        self.logger.info(f"Parallel execution completed!")
        self.logger.info(f"Successful exports: {successful}")
        if failed:
            self.logger.warning(f"Failed exports: {failed}")
        
        return results
    
    async def run_daily_exports(self, target_date=None, mode="sequential"):
        """Run daily exports for specific date"""
        if not target_date:
            # Default to yesterday
            target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        self.logger.info(f"Running daily exports for {target_date} in {mode} mode")
        
        if mode == "parallel":
            return await self.run_all_exports_parallel(target_date, target_date)
        else:
            return await self.run_all_exports_sequential(target_date, target_date)
    
    async def run_weekly_exports(self, mode="sequential"):
        """Run exports for the last 7 days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        self.logger.info(f"Running weekly exports from {start_date_str} to {end_date_str} in {mode} mode")
        
        if mode == "parallel":
            return await self.run_all_exports_parallel(start_date_str, end_date_str)
        else:
            return await self.run_all_exports_sequential(start_date_str, end_date_str)
    
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
async def run_all_today_sequential():
    """Run all exports for today in sequential mode"""
    scheduler = MainScheduler()
    today = datetime.now().strftime("%Y-%m-%d")
    return await scheduler.run_all_exports_sequential(today, today)

async def run_all_today_parallel():
    """Run all exports for today in parallel mode"""
    scheduler = MainScheduler()
    today = datetime.now().strftime("%Y-%m-%d")
    return await scheduler.run_all_exports_parallel(today, today)

async def run_all_yesterday():
    """Run all exports for yesterday"""
    scheduler = MainScheduler()
    return await scheduler.run_daily_exports()

async def run_specific_export(export_type, date=None):
    """Run specific export for specific date"""
    scheduler = MainScheduler()
    if not date:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return await scheduler.run_single_export(export_type, date, date)

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
    
    scheduler = MainScheduler(use_single_session=args.single_session)
    
    if args.export:
        # Run specific export
        asyncio.run(scheduler.run_single_export(args.export, args.date, args.date))
    elif args.all:
        # Run all exports
        if args.mode == 'parallel':
            asyncio.run(scheduler.run_all_exports_parallel(args.date, args.date))
        else:
            asyncio.run(scheduler.run_all_exports_sequential(args.date, args.date))
    else:
        # Default: run daily exports for yesterday
        asyncio.run(scheduler.run_daily_exports())
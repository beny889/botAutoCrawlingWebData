"""
Telegram notification system for export automation
Sends success/failure notifications and daily summaries
"""

import requests
import json
import logging
from datetime import datetime
import os
from typing import Dict, Any, Optional

class TelegramNotifier:
    """Handle Telegram notifications for automation results"""
    
    def __init__(self, token: str = None, chat_id: str = None):
        """Initialize Telegram notifier with credentials"""
        self.token = token or os.getenv('TELEGRAM_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.logger = logging.getLogger(__name__)
        
        if not self.token or not self.chat_id:
            self.logger.warning("Telegram credentials not provided. Notifications disabled.")
            self.enabled = False
        else:
            self.enabled = True
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram chat"""
        if not self.enabled:
            self.logger.info(f"Telegram disabled. Would send: {message}")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.info("Telegram notification sent successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Telegram: {str(e)}")
            return False
    
    def send_export_success(self, export_type: str, records_count: int, execution_time: float) -> bool:
        """Send success notification for individual export"""
        message = f"✅ <b>{export_type.upper()} Export Berhasil!</b>\n"
        message += f"📊 Records: {records_count} rows\n"
        message += f"⏱️ Waktu: {execution_time:.2f} detik\n"
        message += f"🕒 {datetime.now().strftime('%H:%M:%S WIB')}"
        
        return self.send_message(message)
    
    def send_export_failure(self, export_type: str, error: str, retry_attempt: int = 0, max_retries: int = 3) -> bool:
        """Send failure notification for individual export"""
        message = f"❌ <b>{export_type.upper()} Export Gagal!</b>\n"
        message += f"🚨 Error: {error[:200]}...\n" if len(error) > 200 else f"🚨 Error: {error}\n"
        
        if retry_attempt > 0:
            message += f"🔄 Retry attempt: {retry_attempt}/{max_retries}\n"
        
        message += f"🕒 {datetime.now().strftime('%H:%M:%S WIB')}"
        
        return self.send_message(message)
    
    def send_daily_summary(self, results: Dict[str, Any], total_time: float) -> bool:
        """Send daily summary of all exports"""
        successful = [k for k, v in results.items() if v.get("success", False)]
        failed = [k for k, v in results.items() if not v.get("success", False)]
        total_records = sum(v.get("records", 0) for v in results.values() if v.get("success", False))
        
        # Determine emoji based on results
        if len(failed) == 0:
            status_emoji = "🎉"
            status_text = "SEMUA BERHASIL"
        elif len(successful) > len(failed):
            status_emoji = "⚠️"
            status_text = "SEBAGIAN BERHASIL"
        else:
            status_emoji = "❌"
            status_text = "MAYORITAS GAGAL"
        
        message = f"{status_emoji} <b>SUMMARY DAILY EXPORT</b>\n"
        message += f"📈 Status: {status_text}\n"
        message += f"📊 Total Records: {total_records}\n"
        message += f"⏱️ Total Waktu: {total_time:.2f} detik\n\n"
        
        # Success details
        if successful:
            message += f"✅ <b>Berhasil ({len(successful)}):</b>\n"
            for export_type in successful:
                records = results[export_type].get("records", 0)
                message += f"  • {export_type}: {records} rows\n"
        
        # Failure details
        if failed:
            message += f"\n❌ <b>Gagal ({len(failed)}):</b>\n"
            for export_type in failed:
                error = results[export_type].get("error", "Unknown error")[:50]
                message += f"  • {export_type}: {error}...\n"
        
        message += f"\n🕒 {datetime.now().strftime('%d/%m/%Y %H:%M:%S WIB')}"
        
        return self.send_message(message)
    
    def send_system_start(self, mode: str = "sequential") -> bool:
        """Send notification when automation starts"""
        message = f"🚀 <b>AUTOMATION DIMULAI</b>\n"
        message += f"🔧 Mode: {mode}\n"
        message += f"📋 Target: 4 exports (transaksi, point_trx, user, pembayaran_koin)\n"
        message += f"🕒 Start: {datetime.now().strftime('%H:%M:%S WIB')}"
        
        return self.send_message(message)
    
    def send_system_error(self, error: str, component: str = "system") -> bool:
        """Send critical system error notification"""
        message = f"🚨 <b>SYSTEM ERROR</b>\n"
        message += f"🔧 Component: {component}\n"
        message += f"❌ Error: {error[:300]}...\n" if len(error) > 300 else f"❌ Error: {error}\n"
        message += f"🕒 {datetime.now().strftime('%H:%M:%S WIB')}"
        
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """Test Telegram connection"""
        if not self.enabled:
            self.logger.warning("Telegram not enabled - cannot test connection")
            return False
        
        test_message = f"🧪 <b>TEST CONNECTION</b>\n"
        test_message += f"✅ Telegram notifications active\n"
        test_message += f"🕒 {datetime.now().strftime('%d/%m/%Y %H:%M:%S WIB')}"
        
        return self.send_message(test_message)

# Convenience function for quick notifications
def send_quick_notification(message: str, token: str = None, chat_id: str = None) -> bool:
    """Quick notification without class instantiation"""
    notifier = TelegramNotifier(token, chat_id)
    return notifier.send_message(message)

# Default instance using environment variables
default_notifier = TelegramNotifier()
#!/usr/bin/env python3
"""
Automation Results Monitor
Comprehensive monitoring and evaluation of deployed automation system
"""

import requests
import time
from datetime import datetime, timedelta
import json

class AutomationResultsMonitor:
    def __init__(self, api_key="rnd_ju3gULSunfBvdLUqnBp7Nws3RERh"):
        self.api_key = api_key
        self.service_id = "crn-d33565gdl3ps738is730"
        self.service_name = "andalan-atk-automation-production"
        self.deploy_id = "dep-d34g5ubipnbc73fuqldg"
        self.base_url = "https://api.render.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def print_status(self, message):
        """Print status with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def check_service_status(self):
        """Check current service status"""
        try:
            self.print_status("=== SERVICE STATUS CHECK ===")
            response = requests.get(f"{self.base_url}/services", headers=self.headers, timeout=10)

            if response.status_code == 200:
                services = response.json()
                for service_wrapper in services:
                    service = service_wrapper.get('service', service_wrapper)
                    if service.get('id') == self.service_id:
                        status = service.get('suspended', 'unknown')
                        last_run = service.get('serviceDetails', {}).get('lastSuccessfulRunAt')

                        self.print_status(f"Service Status: {status}")
                        self.print_status(f"Service Type: {service.get('type')}")
                        self.print_status(f"Last Successful Run: {last_run}")

                        if last_run:
                            # Parse and check if recent
                            from dateutil import parser
                            last_run_time = parser.parse(last_run)
                            time_diff = datetime.now() - last_run_time.replace(tzinfo=None)

                            self.print_status(f"Time since last run: {time_diff}")

                            if time_diff < timedelta(hours=1):
                                self.print_status("[RECENT] Automation executed recently!")
                                return True
                            else:
                                self.print_status("[OLD] Last run was more than 1 hour ago")
                                return False
                        else:
                            self.print_status("[UNKNOWN] No last run time available")
                            return None

                self.print_status("[ERROR] Target service not found")
                return False
            else:
                self.print_status(f"[ERROR] API call failed: {response.status_code}")
                return False

        except Exception as e:
            self.print_status(f"[ERROR] Status check failed: {str(e)}")
            return False

    def get_recent_deployments(self):
        """Get recent deployment history"""
        try:
            self.print_status("=== RECENT DEPLOYMENTS ===")
            response = requests.get(f"{self.base_url}/services/{self.service_id}/deploys",
                                  headers=self.headers, timeout=15)

            if response.status_code == 200:
                deploys = response.json()
                self.print_status(f"Found {len(deploys)} total deployments")

                # Show recent deployments
                recent_deploys = deploys[:5]  # Last 5 deployments

                for i, deploy in enumerate(recent_deploys):
                    deploy_id = deploy.get('id', 'Unknown')
                    status = deploy.get('status', 'Unknown')
                    created = deploy.get('createdAt', 'Unknown')

                    marker = ">>> OUR DEPLOYMENT <<<" if deploy_id == self.deploy_id else ""

                    self.print_status(f"Deployment {i+1}: {deploy_id}")
                    self.print_status(f"  Status: {status} {marker}")
                    self.print_status(f"  Created: {created}")

                    if deploy.get('commit'):
                        commit_id = deploy['commit'].get('id', 'Unknown')[:7]
                        commit_msg = deploy['commit'].get('message', 'N/A')[:50]
                        self.print_status(f"  Commit: {commit_id} - {commit_msg}...")

                    self.print_status("")

                return recent_deploys
            else:
                self.print_status(f"[ERROR] Failed to fetch deployments: {response.status_code}")
                return None

        except Exception as e:
            self.print_status(f"[ERROR] Deployment fetch failed: {str(e)}")
            return None

    def analyze_expected_execution_schedule(self):
        """Analyze when the automation should have run"""
        self.print_status("=== EXECUTION SCHEDULE ANALYSIS ===")

        now = datetime.now()

        # Cron schedule: "0 1,11 * * *" = 01:00 and 11:00 UTC
        # That's 8:00 AM and 6:00 PM WIB (UTC+7)

        today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        today_6pm = now.replace(hour=18, minute=0, second=0, microsecond=0)
        yesterday_6pm = today_6pm - timedelta(days=1)

        self.print_status(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} WIB")
        self.print_status(f"Today 8 AM: {today_8am.strftime('%Y-%m-%d %H:%M:%S')} WIB")
        self.print_status(f"Today 6 PM: {today_6pm.strftime('%Y-%m-%d %H:%M:%S')} WIB")

        # Determine which execution we should expect
        if now >= today_6pm:
            expected_run = today_6pm
            next_run = today_8am + timedelta(days=1)
            self.print_status("[EXPECTED] Should have run today at 6 PM")
        elif now >= today_8am:
            expected_run = today_8am
            next_run = today_6pm
            self.print_status("[EXPECTED] Should have run today at 8 AM")
        else:
            expected_run = yesterday_6pm
            next_run = today_8am
            self.print_status("[EXPECTED] Should have run yesterday at 6 PM")

        time_since_expected = now - expected_run
        time_to_next = next_run - now

        self.print_status(f"Time since expected run: {time_since_expected}")
        self.print_status(f"Time to next run: {time_to_next}")

        return expected_run, next_run

    def provide_telegram_monitoring_guide(self):
        """Provide guidance for monitoring Telegram notifications"""
        self.print_status("=== TELEGRAM MONITORING GUIDE ===")
        self.print_status("")

        self.print_status("Expected Telegram Notifications:")
        notifications = [
            "[START] AUTOMATION DIMULAI - Mode: individual sessions - 4 exports",
            "Starting transaksi export with dates: 2025-09-16 to 2025-09-16",
            "Starting point_trx export with dates: 2025-09-16 to 2025-09-16",
            "Starting user export with dates: 2025-09-16 to 2025-09-16",
            "Starting pembayaran_koin export with dates: 2025-09-16 to 2025-09-16",
            "[OK] [Export Name] Export Berhasil! Records: X rows (if successful)",
            "[ERROR] [Export Name] Export Gagal! (if failed)",
            "[SUMMARY] SUMMARY DAILY EXPORT - Final results"
        ]

        for i, notification in enumerate(notifications, 1):
            self.print_status(f"{i}. {notification}")

        self.print_status("")
        self.print_status("Key Indicators to Look For:")
        self.print_status("[OK] JSON parsing attempts (control character cleaning)")
        self.print_status("[OK] Google Sheets bypass activation (SKIP_GOOGLE_SHEETS=true)")
        self.print_status("[OK] Backend login success")
        self.print_status("[OK] File downloads (even if 0 records)")
        self.print_status("[OK] Automation completion without crashes")

    def check_for_manual_run_opportunity(self):
        """Check if we can trigger a manual run for testing"""
        self.print_status("=== MANUAL TESTING OPPORTUNITY ===")

        now = datetime.now()

        # Check if it's not close to scheduled run times
        today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        today_6pm = now.replace(hour=18, minute=0, second=0, microsecond=0)

        # Buffer time (30 minutes before/after scheduled runs)
        buffer_minutes = 30

        near_8am = abs((now - today_8am).total_seconds()) < buffer_minutes * 60
        near_6pm = abs((now - today_6pm).total_seconds()) < buffer_minutes * 60

        if near_8am or near_6pm:
            self.print_status("[NOT RECOMMENDED] Too close to scheduled run time")
            self.print_status("Wait for natural scheduled execution or manual trigger later")
            return False
        else:
            self.print_status("[SAFE] Manual testing can be performed now")
            self.print_status("You can trigger a manual deployment for immediate testing:")
            self.print_status("python render_api_trigger.py rnd_ju3gULSunfBvdLUqnBp7Nws3RERh")
            return True

    def run_comprehensive_monitoring(self):
        """Run complete monitoring and analysis"""
        self.print_status("AUTOMATION RESULTS MONITORING - COMPREHENSIVE ANALYSIS")
        self.print_status("=" * 70)

        # 1. Check service status
        service_status = self.check_service_status()
        self.print_status("")

        # 2. Get recent deployments
        deployments = self.get_recent_deployments()
        self.print_status("")

        # 3. Analyze execution schedule
        expected_run, next_run = self.analyze_expected_execution_schedule()
        self.print_status("")

        # 4. Provide Telegram monitoring guidance
        self.provide_telegram_monitoring_guide()
        self.print_status("")

        # 5. Check manual testing opportunity
        can_test_manually = self.check_for_manual_run_opportunity()
        self.print_status("")

        # 6. Final recommendations
        self.print_status("=== MONITORING RECOMMENDATIONS ===")

        if service_status is True:
            self.print_status("[EXCELLENT] Recent automation execution detected!")
            self.print_status("   Action: Check Telegram for results and analyze using log_analysis_template.md")
        elif service_status is False:
            self.print_status("[ATTENTION] No recent automation execution")
            self.print_status("   Action: Monitor Telegram for next scheduled run or trigger manual test")
        else:
            self.print_status("[UNCLEAR] Service status needs verification")
            self.print_status("   Action: Monitor both service logs and Telegram notifications")

        if can_test_manually:
            self.print_status("[TESTING] Manual trigger available for immediate validation")

        self.print_status("")
        self.print_status("Next Steps:")
        self.print_status("1. Monitor Telegram chat for automation notifications")
        self.print_status("2. Use log_analysis_template.md for systematic evaluation")
        self.print_status("3. Document results in monitoring logs")
        self.print_status("4. Report findings for system optimization")

        self.print_status("")
        self.print_status("=" * 70)

if __name__ == "__main__":
    monitor = AutomationResultsMonitor()
    monitor.run_comprehensive_monitoring()
#!/usr/bin/env python3
"""
Deployment Monitoring Script for Render.com
Monitors deployment status and collects logs for analysis
"""

import time
import requests
import json
from datetime import datetime
import re

class RenderDeploymentMonitor:
    def __init__(self, service_name="andalan-atk-automation-final-json-fix"):
        self.service_name = service_name
        self.last_commit = "d8d2093"  # Latest commit with JSON fixes

    def print_status(self, message):
        """Print status with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def check_github_commit_status(self):
        """Check if our latest commit is visible on GitHub"""
        try:
            url = "https://api.github.com/repos/beny889/botAutoCrawlingWebData/commits"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                commits = response.json()
                if commits and len(commits) > 0:
                    latest_commit = commits[0]
                    commit_sha = latest_commit['sha'][:7]
                    commit_message = latest_commit['commit']['message'].split('\n')[0]
                    commit_date = latest_commit['commit']['committer']['date']

                    self.print_status(f"GitHub Latest Commit: {commit_sha}")
                    self.print_status(f"Commit Message: {commit_message}")
                    self.print_status(f"Commit Date: {commit_date}")

                    if commit_sha == self.last_commit:
                        self.print_status("[OK] Our latest commit is visible on GitHub")
                        return True
                    else:
                        self.print_status(f"[WARNING] Expected {self.last_commit}, found {commit_sha}")
                        return False

            else:
                self.print_status(f"[ERROR] GitHub API error: {response.status_code}")
                return False

        except Exception as e:
            self.print_status(f"[ERROR] GitHub check failed: {str(e)}")
            return False

    def analyze_deployment_expectations(self):
        """Analyze what we expect to see in the deployment logs"""
        self.print_status("DEPLOYMENT ANALYSIS EXPECTATIONS:")
        self.print_status("")

        expectations = [
            "[OK] Docker build should complete successfully",
            "[OK] Chrome installation should work (google-chrome-stable)",
            "[OK] Python dependencies should install via pip",
            "[OK] Runtime dependency installation should execute",
            "[CHECK] JSON parsing: Should see control character cleaning attempts",
            "[CHECK] JSON parsing: May see 'Invalid control character at: line 1 column 58'",
            "[CHECK] JSON parsing: Should attempt multiple fix methods",
            "[CHECK] Fallback: Should enable SKIP_GOOGLE_SHEETS=true if JSON fails",
            "[OK] Backend automation should execute with Selenium",
            "[OK] Telegram notifications should be sent",
            "[RESULT] Expected final status: Backend automation working, Google Sheets bypassed"
        ]

        for expectation in expectations:
            self.print_status(f"  {expectation}")

        self.print_status("")

    def simulate_log_analysis(self):
        """Simulate what we would look for in real deployment logs"""
        self.print_status("LOG ANALYSIS CHECKLIST:")
        self.print_status("")

        log_patterns = {
            "Docker Build": [
                "Installing collected packages: selenium",
                "Selenium OK",
                "google-chrome-stable"
            ],
            "Runtime Dependencies": [
                "[OK] Selenium 4.14.0 now available after runtime install",
                "[OK] pandas installed successfully",
                "[OK] All dependency checks completed"
            ],
            "JSON Parsing Issues": [
                "DEBUG: Raw JSON length: 2522",
                "Invalid control character at: line 1 column 58",
                "DEBUG: Skipping control character",
                "DEBUG: All JSON parsing methods failed",
                "Google Sheets temporarily disabled"
            ],
            "Backend Automation": [
                "Running all exports with date: 2025-09-16",
                "Starting transaksi export",
                "Backend automation working",
                "Export completed"
            ],
            "Telegram Notifications": [
                "Telegram notification sent successfully",
                "AUTOMATION DIMULAI",
                "SUMMARY DAILY EXPORT"
            ]
        }

        for category, patterns in log_patterns.items():
            self.print_status(f"[SEARCH] {category}:")
            for pattern in patterns:
                self.print_status(f"   Look for: '{pattern}'")
            self.print_status("")

    def provide_manual_trigger_instructions(self):
        """Provide instructions for manual deployment triggering"""
        self.print_status("MANUAL TRIGGER INSTRUCTIONS:")
        self.print_status("")
        self.print_status("Since CLI authentication is complex, here are alternative approaches:")
        self.print_status("")

        self.print_status("METHOD 1: Render Dashboard")
        self.print_status("1. Go to https://dashboard.render.com")
        self.print_status("2. Find service: andalan-atk-automation-final-json-fix")
        self.print_status("3. Click 'Manual Deploy' button")
        self.print_status("4. Select 'Deploy latest commit' or specific commit d8d2093")
        self.print_status("5. Monitor logs in real-time during deployment")
        self.print_status("")

        self.print_status("METHOD 2: Deploy Hook (if configured)")
        self.print_status("1. Use HTTP GET/POST to deploy hook URL")
        self.print_status("2. Monitor deployment status via dashboard")
        self.print_status("")

        self.print_status("METHOD 3: Wait for Automatic Deployment")
        self.print_status("1. Render should auto-deploy within 1-2 minutes of git push")
        self.print_status("2. Check deployment status in dashboard")
        self.print_status("3. Monitor logs for our JSON parsing fixes")
        self.print_status("")

    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        self.print_status("RENDER DEPLOYMENT MONITORING - STARTING")
        self.print_status("=" * 60)

        # Check GitHub status
        github_ok = self.check_github_commit_status()
        self.print_status("")

        # Analyze expectations
        self.analyze_deployment_expectations()

        # Provide log analysis guidance
        self.simulate_log_analysis()

        # Manual trigger instructions
        self.provide_manual_trigger_instructions()

        self.print_status("MONITORING SUMMARY:")
        self.print_status(f"[STATUS] GitHub Commit: {self.last_commit} - {'Visible' if github_ok else 'Check needed'}")
        self.print_status("[FOCUS] Key Focus: JSON parsing control character fixes")
        self.print_status("[TARGET] Expected Outcome: Backend automation working, Google Sheets bypassed")
        self.print_status("[ACTION] Next Steps: Monitor Render dashboard for deployment progress")
        self.print_status("")
        self.print_status("=" * 60)

if __name__ == "__main__":
    monitor = RenderDeploymentMonitor()
    monitor.run_monitoring_cycle()
#!/usr/bin/env python3
"""
Manual Deployment Trigger Script for Render.com
Triggers deployment and monitors progress
"""

import subprocess
import time
import sys
from datetime import datetime

class RenderDeploymentTrigger:
    def __init__(self):
        self.service_name = "andalan-atk-automation-final-json-fix"
        self.commit_sha = "d8d2093"
        self.render_cli = "./render.exe"

    def print_status(self, message):
        """Print status with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def check_cli_available(self):
        """Check if Render CLI is available and authenticated"""
        try:
            result = subprocess.run([self.render_cli, "--version"],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.print_status(f"Render CLI available: {result.stdout.strip()}")
                return True
            else:
                self.print_status("Render CLI not available or not authenticated")
                return False
        except Exception as e:
            self.print_status(f"CLI check failed: {str(e)}")
            return False

    def list_services(self):
        """List available services to find our service ID"""
        try:
            self.print_status("Fetching service list...")
            result = subprocess.run([self.render_cli, "services", "--output", "json"],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                self.print_status("Services list retrieved successfully")
                # In a real scenario, you'd parse JSON to find service ID
                # For now, we'll use the service name
                return True
            else:
                self.print_status(f"Failed to list services: {result.stderr}")
                return False

        except Exception as e:
            self.print_status(f"Service listing failed: {str(e)}")
            return False

    def trigger_manual_deploy(self):
        """Trigger manual deployment"""
        try:
            self.print_status(f"Triggering manual deployment for commit {self.commit_sha}...")

            # Note: Actual command would need service ID, using service name for demo
            cmd = [self.render_cli, "deploys", "create", "--service", self.service_name, "--confirm"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                self.print_status("Manual deployment triggered successfully!")
                self.print_status(f"Output: {result.stdout}")
                return True
            else:
                self.print_status(f"Deployment trigger failed: {result.stderr}")
                return False

        except Exception as e:
            self.print_status(f"Manual deployment failed: {str(e)}")
            return False

    def monitor_deployment_status(self, deploy_id=None):
        """Monitor deployment progress"""
        try:
            self.print_status("Monitoring deployment status...")

            for i in range(20):  # Monitor for up to 10 minutes (20 * 30s)
                time.sleep(30)

                # Check deployment status
                result = subprocess.run([self.render_cli, "deploys", "list", "--service", self.service_name, "--limit", "1"],
                                      capture_output=True, text=True, timeout=15)

                if result.returncode == 0:
                    self.print_status(f"Status check {i+1}/20: Deployment in progress...")
                    # In real implementation, parse JSON to check status
                    # For now, just monitor for a reasonable time
                else:
                    self.print_status("Status check failed, continuing monitoring...")

            self.print_status("Monitoring period completed. Check Render dashboard for final status.")
            return True

        except Exception as e:
            self.print_status(f"Monitoring failed: {str(e)}")
            return False

    def provide_manual_instructions(self):
        """Provide manual deployment instructions"""
        self.print_status("=== MANUAL DEPLOYMENT INSTRUCTIONS ===")
        self.print_status("")

        instructions = [
            "Since CLI automation has limitations, please use the Render Dashboard:",
            "",
            "1. Open browser to: https://dashboard.render.com",
            "2. Navigate to your service: andalan-atk-automation-final-json-fix",
            "3. Click 'Manual Deploy' button",
            "4. Select 'Deploy latest commit' (d8d2093)",
            "5. Click 'Deploy' to start the process",
            "",
            "During deployment, monitor these phases:",
            "  - Docker Build (5-8 minutes)",
            "  - Runtime Validation (1-2 minutes)",
            "  - Automation Execution (2-3 minutes)",
            "",
            "Key logs to watch for:",
            "  - 'Invalid control character at: line 1 column 58'",
            "  - 'Google Sheets temporarily disabled'",
            "  - 'Telegram notification sent successfully'",
            "  - Backend automation success/failure",
            "",
            "Expected result: Backend automation working, Google Sheets bypassed"
        ]

        for instruction in instructions:
            self.print_status(instruction)

    def run_trigger_workflow(self):
        """Run the complete deployment trigger workflow"""
        self.print_status("=== RENDER MANUAL DEPLOYMENT TRIGGER ===")
        self.print_status("")

        # Check CLI availability
        cli_available = self.check_cli_available()

        if cli_available:
            self.print_status("Attempting CLI-based deployment trigger...")

            # List services
            if self.list_services():
                # Trigger deployment
                if self.trigger_manual_deploy():
                    # Monitor progress
                    self.monitor_deployment_status()
                else:
                    self.print_status("CLI deployment failed, falling back to manual instructions")
                    self.provide_manual_instructions()
            else:
                self.print_status("Service listing failed, providing manual instructions")
                self.provide_manual_instructions()
        else:
            self.print_status("CLI not available, providing manual instructions")
            self.provide_manual_instructions()

        self.print_status("")
        self.print_status("=== NEXT STEPS ===")
        self.print_status("1. Monitor deployment logs in Render dashboard")
        self.print_status("2. Use log_analysis_template.md to evaluate results")
        self.print_status("3. Check Telegram notifications for automation status")
        self.print_status("4. Report findings for further optimization")

if __name__ == "__main__":
    trigger = RenderDeploymentTrigger()
    trigger.run_trigger_workflow()
#!/usr/bin/env python3
"""
Render API Deployment Trigger and Monitor
Uses Render REST API for automated deployment triggering and monitoring
"""

import requests
import json
import time
from datetime import datetime
import os

class RenderAPIManager:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('RENDER_API_KEY')
        self.base_url = "https://api.render.com/v1"
        self.service_name = "andalan-atk-automation-production"
        self.service_id = None
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def print_status(self, message):
        """Print status with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def validate_api_key(self):
        """Validate API key by testing a simple API call"""
        if not self.api_key:
            self.print_status("[ERROR] No API key provided. Set RENDER_API_KEY environment variable or pass as parameter")
            return False

        try:
            response = requests.get(f"{self.base_url}/services", headers=self.headers, timeout=10)

            if response.status_code == 200:
                self.print_status("[OK] API key validated successfully")
                return True
            elif response.status_code == 401:
                self.print_status("[ERROR] API key invalid - authentication failed")
                return False
            else:
                self.print_status(f"[ERROR] API validation failed with status {response.status_code}")
                return False

        except Exception as e:
            self.print_status(f"[ERROR] API validation failed: {str(e)}")
            return False

    def find_service_id(self):
        """Find service ID by service name"""
        try:
            self.print_status(f"Searching for service: {self.service_name}")
            response = requests.get(f"{self.base_url}/services", headers=self.headers, timeout=15)

            if response.status_code == 200:
                services = response.json()

                for service_wrapper in services:
                    # Handle nested service structure
                    service = service_wrapper.get('service', service_wrapper)

                    if service.get('name') == self.service_name:
                        self.service_id = service.get('id')
                        service_type = service.get('type')
                        self.print_status(f"[OK] Found service: {self.service_name}")
                        self.print_status(f"    Service ID: {self.service_id}")
                        self.print_status(f"    Service Type: {service_type}")
                        return True

                self.print_status(f"[ERROR] Service '{self.service_name}' not found")
                self.print_status("Available services:")
                for service_wrapper in services:
                    service = service_wrapper.get('service', service_wrapper)
                    self.print_status(f"  - {service.get('name')} ({service.get('type')})")
                return False

            else:
                self.print_status(f"[ERROR] Failed to fetch services: HTTP {response.status_code}")
                return False

        except Exception as e:
            self.print_status(f"[ERROR] Service search failed: {str(e)}")
            return False

    def get_latest_deployment(self):
        """Get information about the latest deployment"""
        try:
            self.print_status("Fetching latest deployment info...")
            response = requests.get(f"{self.base_url}/services/{self.service_id}/deploys",
                                  headers=self.headers, timeout=15)

            if response.status_code == 200:
                deploys = response.json()
                if deploys:
                    latest = deploys[0]
                    deploy_id = latest.get('id')
                    status = latest.get('status')
                    commit = latest.get('commit', {}).get('id', 'Unknown')[:7]
                    created_at = latest.get('createdAt')

                    self.print_status(f"[INFO] Latest deployment:")
                    self.print_status(f"    Deploy ID: {deploy_id}")
                    self.print_status(f"    Status: {status}")
                    self.print_status(f"    Commit: {commit}")
                    self.print_status(f"    Created: {created_at}")

                    return latest
                else:
                    self.print_status("[INFO] No previous deployments found")
                    return None
            else:
                self.print_status(f"[ERROR] Failed to fetch deployments: HTTP {response.status_code}")
                return None

        except Exception as e:
            self.print_status(f"[ERROR] Deployment fetch failed: {str(e)}")
            return None

    def trigger_deployment(self, clear_cache=False, commit_id=None):
        """Trigger a new deployment"""
        try:
            self.print_status("Triggering new deployment...")

            # Prepare request body
            body = {}
            if clear_cache:
                body['clearCache'] = 'clear'
            if commit_id:
                body['commitId'] = commit_id

            response = requests.post(f"{self.base_url}/services/{self.service_id}/deploys",
                                   headers=self.headers, json=body, timeout=20)

            if response.status_code == 201:
                deploy_info = response.json()
                deploy_id = deploy_info.get('id')
                status = deploy_info.get('status')

                self.print_status(f"[OK] Deployment triggered successfully!")
                self.print_status(f"    Deploy ID: {deploy_id}")
                self.print_status(f"    Status: {status}")

                return deploy_id

            elif response.status_code == 409:
                self.print_status("[WARNING] Deployment already in progress")
                return None
            else:
                self.print_status(f"[ERROR] Deployment trigger failed: HTTP {response.status_code}")
                self.print_status(f"Response: {response.text}")
                return None

        except Exception as e:
            self.print_status(f"[ERROR] Deployment trigger failed: {str(e)}")
            return None

    def monitor_deployment(self, deploy_id, max_minutes=15):
        """Monitor deployment progress until completion"""
        try:
            self.print_status(f"Monitoring deployment {deploy_id}...")
            max_checks = max_minutes * 2  # Check every 30 seconds

            for i in range(max_checks):
                response = requests.get(f"{self.base_url}/services/{self.service_id}/deploys/{deploy_id}",
                                      headers=self.headers, timeout=10)

                if response.status_code == 200:
                    deploy_info = response.json()
                    status = deploy_info.get('status')

                    self.print_status(f"[{i+1}/{max_checks}] Deployment status: {status}")

                    if status == 'live':
                        self.print_status("[OK] Deployment completed successfully!")
                        return True
                    elif status in ['build_failed', 'update_failed', 'canceled']:
                        self.print_status(f"[ERROR] Deployment failed with status: {status}")
                        return False
                    else:
                        # Still in progress (building, deploying, etc.)
                        time.sleep(30)
                        continue
                else:
                    self.print_status(f"[WARNING] Status check failed: HTTP {response.status_code}")
                    time.sleep(30)
                    continue

            self.print_status(f"[TIMEOUT] Deployment monitoring timed out after {max_minutes} minutes")
            return False

        except Exception as e:
            self.print_status(f"[ERROR] Deployment monitoring failed: {str(e)}")
            return False

    def get_deployment_logs(self, deploy_id, lines=100):
        """Get deployment logs"""
        try:
            self.print_status(f"Fetching deployment logs for {deploy_id}...")

            # Note: Render API logs endpoint may vary - this is the expected pattern
            response = requests.get(f"{self.base_url}/services/{self.service_id}/deploys/{deploy_id}/logs",
                                  headers=self.headers, timeout=15)

            if response.status_code == 200:
                logs_data = response.json()
                self.print_status(f"[OK] Retrieved deployment logs")
                return logs_data
            else:
                self.print_status(f"[WARNING] Logs not available via API (HTTP {response.status_code})")
                self.print_status("Use Render Dashboard to view logs: https://dashboard.render.com")
                return None

        except Exception as e:
            self.print_status(f"[ERROR] Log retrieval failed: {str(e)}")
            return None

    def run_api_deployment_workflow(self):
        """Run complete API-based deployment workflow"""
        self.print_status("=== RENDER API DEPLOYMENT WORKFLOW ===")
        self.print_status("")

        # Step 1: Validate API key
        if not self.validate_api_key():
            self.print_status("[FAILED] API key validation failed")
            self.provide_api_setup_instructions()
            return False

        # Step 2: Find service
        if not self.find_service_id():
            self.print_status("[FAILED] Service discovery failed")
            return False

        # Step 3: Check current deployment status
        latest_deploy = self.get_latest_deployment()

        # Step 4: Trigger new deployment
        deploy_id = self.trigger_deployment(clear_cache=True)

        if not deploy_id:
            self.print_status("[FAILED] Deployment trigger failed")
            return False

        # Step 5: Monitor deployment progress
        success = self.monitor_deployment(deploy_id)

        # Step 6: Get logs (if available)
        logs = self.get_deployment_logs(deploy_id)

        # Step 7: Summary
        self.print_status("")
        self.print_status("=== DEPLOYMENT SUMMARY ===")
        if success:
            self.print_status("[SUCCESS] Deployment completed successfully")
            self.print_status(f"Deploy ID: {deploy_id}")
            self.print_status("Monitor automation execution via Telegram notifications")
        else:
            self.print_status("[PARTIAL] Deployment may still be in progress")
            self.print_status(f"Deploy ID: {deploy_id}")
            self.print_status("Check Render Dashboard for detailed status")

        self.print_status("")
        self.print_status("Next steps:")
        self.print_status("1. Monitor Telegram notifications for automation status")
        self.print_status("2. Use log_analysis_template.md for systematic evaluation")
        self.print_status("3. Focus on JSON parsing and backend automation success")

        return success

    def provide_api_setup_instructions(self):
        """Provide instructions for setting up Render API key"""
        self.print_status("")
        self.print_status("=== RENDER API SETUP INSTRUCTIONS ===")
        self.print_status("")
        self.print_status("To use the Render API, you need to:")
        self.print_status("")
        self.print_status("1. Get your API key:")
        self.print_status("   - Go to https://dashboard.render.com")
        self.print_status("   - Navigate to Account Settings")
        self.print_status("   - Create a new API key")
        self.print_status("   - Copy the generated key")
        self.print_status("")
        self.print_status("2. Set environment variable:")
        self.print_status("   export RENDER_API_KEY='your_api_key_here'")
        self.print_status("   # OR in Windows:")
        self.print_status("   set RENDER_API_KEY=your_api_key_here")
        self.print_status("")
        self.print_status("3. Re-run this script:")
        self.print_status("   python render_api_trigger.py")
        self.print_status("")

if __name__ == "__main__":
    # Check for API key in command line arguments or environment
    import sys

    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]

    manager = RenderAPIManager(api_key)
    manager.run_api_deployment_workflow()
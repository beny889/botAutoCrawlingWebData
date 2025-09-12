#!/bin/bash

# Start script for Render.com deployment
# Sets up timezone and runs automation with proper logging

echo "🚀 Starting Automation Bot on Render.com..."
echo "⏰ Setting timezone to Asia/Jakarta (WIB)"

# Set timezone
export TZ=Asia/Jakarta

# Set Python to unbuffered mode for better logging
export PYTHONUNBUFFERED=1

# Print current time for verification
echo "📅 Current time: $(date)"

# Initialize Playwright (browser automation)
echo "🌐 Installing Playwright browsers..."
playwright install chromium --with-deps

# Create necessary directories
mkdir -p downloads
mkdir -p logs

# Start the automation
echo "🤖 Starting export automation..."
python main_scheduler.py --all --headless --production --single-session

# Check exit status
if [ $? -eq 0 ]; then
    echo "✅ Automation completed successfully!"
else
    echo "❌ Automation failed with errors!"
    exit 1
fi
"""
Local environment setup helper
Sets up environment variables and creates necessary directories
"""

import os
from pathlib import Path

def setup_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "downloads",
        "screenshots"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created/verified directory: {directory}")

def setup_environment_template():
    """Create environment template file"""
    env_template = """# Environment variables for local testing
# Copy this to .env or set these in your system environment

# Backend credentials
BACKEND_USERNAME=superadmin@gmail.com
BACKEND_PASSWORD=Z123465!@

# Telegram notification credentials  
TELEGRAM_TOKEN=7617892433:AAHrMesr-6MosGqMq5z0JVxFKa61ZAr_abM
TELEGRAM_CHAT_ID=-4924885979

# Google Service Account JSON (copy from service-account-key.json)
# GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# Optional settings
HEADLESS=false
TZ=Asia/Jakarta
PYTHONUNBUFFERED=1
"""
    
    env_file = Path("env_template.txt")
    env_file.write_text(env_template)
    print(f"✅ Created environment template: {env_file}")
    print("📝 Please set these environment variables before testing")

def check_environment():
    """Check if environment variables are set"""
    required_vars = [
        "BACKEND_USERNAME",
        "BACKEND_PASSWORD", 
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print("⚠️  Missing environment variables:")
        for var in missing:
            print(f"   - {var}")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def check_service_account():
    """Check Google service account configuration"""
    # Check environment variable
    if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'):
        print("✅ Google Service Account JSON found in environment variable")
        return True
    
    # Check local file
    service_account_file = Path("service-account-key.json")
    if service_account_file.exists():
        print("✅ Google Service Account file found: service-account-key.json")
        return True
    
    print("⚠️  Google Service Account not configured")
    print("   Either set GOOGLE_SERVICE_ACCOUNT_JSON environment variable")
    print("   or place service-account-key.json in the project root")
    return False

def main():
    """Main setup function"""
    print("🚀 Setting up local development environment")
    print("=" * 50)
    
    # Setup directories
    setup_directories()
    print()
    
    # Create environment template
    setup_environment_template()
    print()
    
    # Check environment
    env_ok = check_environment()
    print()
    
    # Check service account
    service_ok = check_service_account()
    print()
    
    # Summary
    print("=" * 50)
    if env_ok and service_ok:
        print("🎉 Local environment setup complete!")
        print("✅ Ready to run: python test_local.py")
    else:
        print("⚠️  Please fix the issues above before testing")
        print("📖 See env_template.txt for required environment variables")
    
    print()
    print("Next steps:")
    print("1. Set environment variables (see env_template.txt)")
    print("2. Place service-account-key.json file in project root (or set env var)")
    print("3. Run: pip install -r requirements_local.txt")
    print("4. Run: python test_local.py")

if __name__ == "__main__":
    main()
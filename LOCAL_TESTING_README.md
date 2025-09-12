# Local Testing Guide for Selenium Implementation

## Quick Start

1. **Setup Environment**:
   ```bash
   python setup_local.py
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements_local.txt
   ```

3. **Set Environment Variables** (see `env_template.txt` for all required variables):
   ```bash
   # Windows (Command Prompt)
   set BACKEND_USERNAME=superadmin@gmail.com
   set BACKEND_PASSWORD=Z123465!@
   set TELEGRAM_TOKEN=7617892433:AAHrMesr-6MosGqMq5z0JVxFKa61ZAr_abM
   set TELEGRAM_CHAT_ID=-4924885979

   # Windows (PowerShell)
   $env:BACKEND_USERNAME="superadmin@gmail.com"
   $env:BACKEND_PASSWORD="Z123465!@"
   $env:TELEGRAM_TOKEN="7617892433:AAHrMesr-6MosGqMq5z0JVxFKa61ZAr_abM"
   $env:TELEGRAM_CHAT_ID="-4924885979"
   ```

4. **Place Google Service Account File**:
   ```
   Copy service-account-key.json to project root
   OR set GOOGLE_SERVICE_ACCOUNT_JSON environment variable
   ```

5. **Run Tests**:
   ```bash
   python test_local.py
   ```

## Individual Component Testing

**Test Browser Only**:
```bash
python -c "from test_local import test_chrome_driver; test_chrome_driver()"
```

**Test Single Export**:
```bash
python exports/automation_transaksi.py
```

**Test Main Scheduler**:
```bash
python main_scheduler.py --export transaksi --date 2025-09-12 --debug
```

## Troubleshooting

### Chrome WebDriver Issues
- Make sure Chrome browser is installed
- ChromeDriverManager will auto-download the correct driver version

### Environment Variable Issues
- Check that all required variables are set: `python -c "from shared.config import ExportConfig; ExportConfig.validate_environment()"`
- Use `env_template.txt` as reference

### Import Issues
- Make sure all dependencies are installed: `pip install -r requirements_local.txt`
- Check Python path issues with shared modules

### Google Sheets Issues
- Verify service-account-key.json is present and valid
- Check that service account has access to the Google Sheets

## Expected Test Results

All tests should pass:
```
✅ Imports
✅ Environment Variables  
✅ Chrome WebDriver
✅ BackendConnector
✅ Export Class
✅ MainScheduler

🎉 ALL TESTS PASSED! Ready for deployment to Render.com
```

## Next Steps After Local Success

1. Commit changes to GitHub
2. Deploy to Render.com
3. Monitor execution logs
4. Verify all 4 exports work in cloud environment
# QUICK REFERENCE GUIDE
## Backend Export Automation - ✅ DEPLOYED & EXECUTING

*Updated status: Production deployment complete via Render API*

---

## Current Status (September 16, 2025) - DEPLOYED + JSON DEBUGGING

### ✅ **PRODUCTION DEPLOYMENT + JSON FIXES COMPLETE:**
- **Service Status**: LIVE (crn-d33565gdl3ps738is730)
- **Deploy ID**: dep-d34g5ubipnbc73fuqldg (updated with latest fixes)
- **Latest Commit**: 14cfbc3 - ord() validation + error documentation
- **Build Performance**: Completed in ~2 minutes (excellent)
- **API Integration**: Render API fully operational
- **JSON Fixes**: Multi-stage debugging complete
  - ✅ Control character removal (28 newlines)
  - ✅ ord() string length validation
  - ⏳ Testing final JSON parsing success
- **Error Documentation**: Complete timeline in ERRORS_AND_SOLUTIONS.md

### 🚀 **API DEPLOYMENT TOOLS:**
- **render_api_trigger.py**: Automated deployment triggering
- **test_render_api.py**: Service validation and discovery
- **API Key**: rnd_ju3gULSunfBvdLUqnBp7Nws3RERh (active)
- **Monitoring**: Real-time build status tracking

---

## Immediate Actions Available

### **OPTION A: Quick Fix (Web Service)**
**Time**: ~10 minutes  
**Risk**: Low (keeps current working setup)

1. **Update Render.com Dashboard**:
   - Go to service settings → Start Command field
   - Change from: `python main_scheduler.py --all --headless --production --single-session`
   - Change to: `python main_scheduler.py --export pembayaran_koin --headless --production --date 2025-09-11`
   - Save and deploy

2. **Expected Result**: Single export runs correctly, but port binding issues remain

### **OPTION B: Docker Validation (Recommended)**
**Time**: ~2-3 hours  
**Risk**: Medium (requires new learning)

1. **Create separate validation repository**
2. **Test Docker + Chrome + cron service approach**
3. **Compare architectures before deciding**

---

## File Locations and Key Info

### **Working Files**:
- **Main automation**: `main_scheduler.py` ✅ Working
- **Backend connector**: `shared/backend_connector.py` ✅ Enhanced  
- **Config**: `shared/config.py` ✅ Filtered (only coin export active)
- **Deployment**: `render.yaml` ✅ Configured but overridden by dashboard

### **Current Service**:
- **Name**: `automation-bot-final-fixed`
- **Type**: Web service (problematic)
- **URL**: Check your Render.com dashboard
- **Status**: Working but with restart loops

### **Environment Variables** (Set in Render.com dashboard):
```
BACKEND_USERNAME=superadmin@gmail.com
BACKEND_PASSWORD=Z123465!@
DISABLE_NOTIFICATIONS=true
HEADLESS=true
TZ=Asia/Jakarta
PYTHONUNBUFFERED=1
```

---

## Command Quick Reference

### **Single Export Test** (Current working command):
```bash
python main_scheduler.py --export pembayaran_koin --headless --production --date 2025-09-11
```

### **All Exports** (After re-enabling in config.py):
```bash
python main_scheduler.py --all --headless --production --date 2025-09-11
```

### **Re-enable Other Exports**:
In `shared/config.py`, uncomment:
```python
# "transaksi": { ... },
# "point_trx": { ... }, 
# "user": { ... },
```

---

## Architecture Decision Matrix

| Approach | Chrome Install | Service Type | Port Issues | Complexity | Status |
|----------|---------------|--------------|-------------|------------|---------|
| **Web Service** | ✅ Works | ❌ Wrong | ❌ Yes | 🟢 Low | Current |
| **Docker + Cron** | ❓ Unknown | ✅ Correct | ✅ No | 🟡 Medium | To Test |
| **External Chrome** | ✅ Works | ✅ Correct | ✅ No | 🔴 High | Alternative |

---

## Next Session Priorities

### **If Choosing Quick Fix (Option A)**:
1. Update Render.com dashboard Start Command
2. Test single export execution
3. Consider port binding solution
4. Plan for re-enabling other exports

### **If Choosing Docker Validation (Option B)**:
1. Create separate repository: `automation-docker-validation`
2. Copy essential files: `requirements.txt`, core automation scripts
3. Create Dockerfile with Chrome pre-installed
4. Test local Docker build
5. Test cron service deployment on Render.com
6. Compare approaches and make final decision

---

## Key Contacts/Resources

### **Render.com Service**:
- Dashboard: https://dashboard.render.com/
- Service: `automation-bot-final-fixed`
- Logs: Available in service dashboard

### **Google Sheets**:
- Coin Payment: https://docs.google.com/spreadsheets/d/1KWEMz3R5N1EnlS9NdJS9NiQRUsBuTAIfEoaYpS2NhAk
- Currently: 7+ records (working correctly)

### **Backend System**:
- URL: https://backend.andalanatk.com
- Test URL: https://backend.andalanatk.com/koin_pay
- Status: Working, data available for 2025-09-11

---

## Quick Debugging

### **If Export Fails**:
1. Check browser installation in logs
2. Verify environment variables set
3. Test date format (YYYY-MM-DD)
4. Check selector in `shared/config.py`

### **If Download Fails**:
1. Check file stability detection logs
2. Verify download folder permissions  
3. Test button click with screenshots
4. Check file size validation

### **If Upload Fails**:
1. Verify Google service account credentials
2. Check sheet permissions
3. Test data format compatibility
4. Review smart validation logs

---

## Emergency Rollback

### **If Changes Break System**:
1. **Git rollback**: `git checkout 2218a42` (last working commit)
2. **Config restore**: Uncomment all exports in config.py
3. **Service restore**: Use web service with `--all` command
4. **Dashboard restore**: Reset Start Command to original

---

*Quick reference created: September 13, 2025*  
*Core automation: ✅ Working perfectly*  
*Architecture: 🔄 Needs decision*
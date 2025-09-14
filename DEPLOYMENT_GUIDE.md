# Production Deployment Guide
## Docker + Cron Service Architecture

### Final Architecture Decision: Docker + Cron Service ✅

**Selected Solution**: Docker + Cron Service on Render.com
**Rationale**: Perfect service type match + full system control for Chrome installation
**Score**: 22/25 vs 12/25 (Web Service) vs 19/25 (Traditional Cron)

---

## Deployment Files Ready

### Core Configuration Files:
- ✅ **`render.yaml`**: Production cron service configuration
- ✅ **`Dockerfile`**: Optimized Chrome + Python environment
- ✅ **`docker-compose.yml`**: Local testing environment
- ✅ **`.dockerignore`**: Optimized build context
- ✅ **`docker_validation.py`**: Chrome installation validation script

### Deployment Configuration:
```yaml
services:
- type: cron
  name: andalan-atk-automation-production
  schedule: "0 1,11 * * *"  # 8:00 AM & 6:00 PM WIB
  dockerfilePath: ./Dockerfile
  dockerContext: .
```

---

## Deployment Steps

### 1. Repository Preparation
```bash
# Ensure all files are committed
git add render.yaml Dockerfile docker-compose.yml .dockerignore
git add ARCHITECTURE_COMPARISON.md DEPLOYMENT_GUIDE.md
git commit -m "Production Docker + Cron deployment configuration"
git push origin main
```

### 2. Render.com Deployment
1. **Create New Service**: Connect GitHub repository
2. **Service Type**: Will auto-detect cron from render.yaml
3. **Environment Variables**: Auto-configured from render.yaml
4. **Build Process**: Docker will handle Chrome installation
5. **Schedule**: 2x daily at 8 AM & 6 PM WIB

### 3. Expected Build Process
```dockerfile
FROM python:3.11-slim-bullseye
→ Install system dependencies (wget, gnupg, curl, xvfb)
→ Install Google Chrome stable via official repository
→ Install Python dependencies from requirements.txt
→ Copy automation scripts and shared components
→ Set environment variables for headless Chrome
→ CMD: python main_scheduler.py --all --headless --production --single-session
```

### 4. Production Execution
- **Trigger**: Cron schedule (automated)
- **Duration**: ~1.28 minutes per execution
- **Process**: Login → Export 4 data types → Upload to Google Sheets → Telegram notifications
- **Resource**: ~500MB memory, minimal CPU usage

---

## Advantages of Final Architecture

### ✅ Service Type Perfect Match:
- **Cron Service**: Designed for scheduled batch jobs
- **No Port Binding**: No HTTP service requirements
- **Clean Lifecycle**: Starts → Runs → Exits cleanly

### ✅ Chrome Installation Resolved:
- **Docker Build**: Full root privileges during build
- **System Packages**: apt-get install google-chrome-stable
- **Isolated Environment**: Consistent across deployments

### ✅ Configuration Control:
- **No Command Caching**: Docker CMD overrides dashboard issues
- **Infrastructure as Code**: render.yaml version controlled
- **Environment Variables**: Secure credential management

### ✅ Resource Efficiency:
- **Pay Per Execution**: Only charged during automation runs
- **Optimal Schedule**: 2x daily (77 minutes/month total)
- **Cost**: ~$7/month Render.com Background Worker

---

## Monitoring & Success Metrics

### Telegram Notifications:
- 🚀 **System Start**: "AUTOMATION DIMULAI - Mode: single session"
- ✅ **Export Success**: Individual export completion status
- 📊 **Daily Summary**: Total records, execution time, success rate
- 🚨 **Errors**: Detailed failure reporting with retry status

### Success Criteria:
- **Execution Time**: <2 minutes per run
- **Success Rate**: >95% monthly average
- **Memory Usage**: <512MB peak
- **Data Accuracy**: 100% data integrity validation

### Performance Monitoring:
```
Expected Metrics:
- Login Time: ~36 seconds
- Per Export: 8-14 seconds each
- Total Time: 1.28 minutes (headless)
- Memory: <500MB peak
- Success Rate: 100% (based on single-session testing)
```

---

## Troubleshooting Guide

### Common Issues & Solutions:

#### 1. Chrome Installation Failure
**Symptoms**: Browser not found errors
**Solution**: Docker build provides full system control - should not occur
**Debug**: Check Dockerfile Chrome installation steps

#### 2. Environment Variable Issues
**Symptoms**: Authentication failures, missing credentials
**Solution**: Verify render.yaml envVars section matches requirements
**Debug**: Check Render.com environment variables dashboard

#### 3. Schedule Not Triggering
**Symptoms**: Cron job not executing at scheduled times
**Solution**: Verify cron expression and timezone settings
**Debug**: Check Render.com cron job logs and UTC conversion

#### 4. Memory/Resource Limits
**Symptoms**: Container killed during execution
**Solution**: Monitor memory usage, optimize Chrome options if needed
**Debug**: Review container resource allocation

---

## Rollback Strategy

### If Docker Deployment Fails:
1. **Immediate Fallback**: Revert to Web Service with keep-alive
2. **Alternative Platform**: Test Railway, Fly.io alternatives
3. **Manual Process**: Temporary return to manual exports while debugging

### Rollback Commands:
```bash
# Revert to web service configuration
git checkout HEAD~1 render.yaml
git commit -m "Rollback to web service configuration"
git push origin main
```

---

## Success Confirmation Steps

### Phase 1: Deployment Validation
- [ ] Service creates successfully on Render.com
- [ ] Docker build completes without errors
- [ ] Chrome installation verified in build logs
- [ ] Environment variables properly configured

### Phase 2: Functionality Testing
- [ ] First cron execution completes successfully
- [ ] All 4 exports execute properly
- [ ] Google Sheets upload working
- [ ] Telegram notifications received

### Phase 3: Production Validation
- [ ] 2x daily schedule functioning
- [ ] Performance metrics within targets
- [ ] Error handling working correctly
- [ ] Data accuracy maintained

---

## Next Session Preparation

When deployment completes:
1. **Monitor First Execution**: Watch initial cron run logs
2. **Validate Data**: Confirm Google Sheets updates
3. **Performance Check**: Verify execution time targets
4. **Notification Test**: Confirm Telegram alerts working
5. **Documentation Update**: Record actual vs expected results

---

**Deployment Ready**: All configuration files prepared for production deployment
**Architecture**: Docker + Cron Service (optimal solution)
**Expected Result**: Reliable 2x daily automation in <2 minutes per run

---

*Deployment Guide - September 14, 2025*
# ==============================================================================
# TalentPulse AI - Git Initial Push Script for talentpulse-ai-68
# Author: Nguyen Dinh Sang (crcsportsvn@gmail.com)
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "📦 Initializing & Pushing to GitHub repository..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Stage all safe files (excluding .env and service accounts)
git add .

# 2. Create Initial Production Commit
git commit -m "feat: initial production-ready release of TalentPulse AI on Google Cloud Run (#AccelerateAIwithCloudRun)"

# 3. Create Main Branch
git branch -M main

# 4. Instructions for Remote Push
Write-Host ""
Write-Host "To link and push to your remote GitHub repository, run:" -ForegroundColor Yellow
Write-Host "git remote add origin https://github.com/crcsportsvn/talentpulse-ai-68.git" -ForegroundColor Green
Write-Host "git push -u origin main" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

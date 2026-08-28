# ==============================================================================
# TalentPulse AI - One-Click Google Cloud Run Deployment Script (PowerShell)
# #AccelerateAIwithCloudRun Challenge
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 Deploying TalentPulse AI to Google Cloud Run..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$PROJECT_ID = "talent-pulse-ai"
$SERVICE_NAME = "talentpulse-ai"
$REGION = "us-central1"
$GEMINI_API_KEY = $env:GEMINI_API_KEY

Write-Host "[1/4] Setting active GCP Project to '$PROJECT_ID'..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID

Write-Host "[2/4] Enabling Required Google Cloud APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com secretmanager.googleapis.com

Write-Host "[3/4] Building container and deploying to Cloud Run with 5-Layer Security..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
    --source . `
    --region $REGION `
    --platform managed `
    --allow-unauthenticated `
    --max-instances 2 `
    --min-instances 0 `
    --cpu-throttling `
    --concurrency 80 `
    --memory 1Gi `
    --set-env-vars "ENVIRONMENT=production,DEBUG=False,GCP_PROJECT_ID=$PROJECT_ID,GEMINI_API_KEY=$GEMINI_API_KEY"

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "✅ Deployment Completed Successfully!" -ForegroundColor Green
Write-Host "Get your public Cloud Run URL above for your contest submission." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

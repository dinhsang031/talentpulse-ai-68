"""
TalentPulse AI - Main FastAPI Application
Production-ready backend for Google Cloud Run deployment.
Integrates Firebase Auth, Cloud Firestore, Google AI Studio Gemini API, and Modern UI.
"""

import os
import uuid
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from backend.config import settings
from backend.auth import get_current_user, AuthenticatedUser
from backend.schemas import (
    CandidateProfile,
    ChatRequest,
    ChatResponse,
    ChatMessage,
    InterviewKitResponse
)
from backend.tools import (
    extract_text_from_pdf_stream,
    extract_text_from_docx_stream,
    parse_cv_filename
)
from backend.gemini_service import gemini_service
from backend.firestore_service import firestore_repo
from backend.rate_limiter import rate_limiter, get_client_ip

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("talentpulse.main")

app = FastAPI(
    title="TalentPulse AI - Multimodal Recruiter Platform",
    description="Production-ready AI Screening & Multi-turn Candidate Intelligence Copilot on Google Cloud Run",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 5 Defense: Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# ==============================================================================
# 1. SYSTEM & CONFIG ENDPOINTS
# ==============================================================================
@app.get("/api/health")
async def health_check():
    """Health check endpoint for Google Cloud Run container liveness probe."""
    return {
        "status": "healthy",
        "service": "talentpulse-ai",
        "gemini_model": settings.GEMINI_MODEL,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/config/firebase")
async def get_firebase_web_config():
    """Provides public Firebase Web credentials for frontend authentication."""
    return {
        "apiKey": settings.FIREBASE_WEB_API_KEY,
        "authDomain": settings.FIREBASE_WEB_AUTH_DOMAIN,
        "projectId": settings.FIREBASE_WEB_PROJECT_ID or settings.GCP_PROJECT_ID,
        "storageBucket": settings.FIREBASE_WEB_STORAGE_BUCKET,
        "messagingSenderId": settings.FIREBASE_WEB_MESSAGING_SENDER_ID,
        "appId": settings.FIREBASE_WEB_APP_ID
    }


@app.get("/api/auth/me")
async def get_user_info(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Returns currently authenticated recruiter user profile."""
    return {
        "uid": current_user.uid,
        "email": current_user.email,
        "name": current_user.name
    }


# ==============================================================================
# 2. CANDIDATE PROFILE & RESUME EXTRACTION ENDPOINTS
# ==============================================================================
@app.post("/api/resumes/upload", response_model=CandidateProfile)
async def upload_and_process_resume(
    request: Request,
    file: UploadFile = File(...),
    target_position: str = Form(""),
    job_description: Optional[str] = Form(""),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Ingest Resume (PDF, DOCX, Images), extract via Gemini Multimodal API,
    compute HR Fit & Radar scores, and persist under /users/{userId}/candidates/...
    Protected by Layer 2 Rate Limiter (Max 6 uploads/minute per user/IP).
    """
    client_ip = get_client_ip(request)
    rate_limiter.check_rate_limit(
        identifier=current_user.uid or client_ip,
        route_tag="upload_resume",
        max_requests=6,
        window_seconds=60
    )

    logger.info(f"Processing resume '{file.filename}' for user '{current_user.uid}' (Role: {target_position or 'Auto-detect'})")
    
    try:
        file_bytes = await file.read()
        filename_lower = file.filename.lower()
        
        mime_type = file.content_type
        if filename_lower.endswith(".pdf"):
            mime_type = "application/pdf"
            extracted_text = extract_text_from_pdf_stream(file_bytes)
        elif filename_lower.endswith(".docx") or filename_lower.endswith(".doc"):
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            extracted_text = extract_text_from_docx_stream(file_bytes)
        elif filename_lower.endswith(".png"):
            mime_type = "image/png"
            extracted_text = ""
        elif filename_lower.endswith(".jpg") or filename_lower.endswith(".jpeg"):
            mime_type = "image/jpeg"
            extracted_text = ""
        else:
            extracted_text = file_bytes.decode("utf-8", errors="ignore")

        # 2. Extract & Score via Gemini (Supports Multimodal PDF/Image Direct Stream)
        ai_result = await gemini_service.extract_candidate_data(
            cv_text=extracted_text,
            filename=file.filename,
            target_position=target_position,
            jd_text=job_description or "",
            file_bytes=file_bytes,
            mime_type=mime_type
        )

        candidate_id = f"cand_{uuid.uuid4().hex[:10]}"
        candidate_profile = CandidateProfile(
            id=candidate_id,
            user_id=current_user.uid,
            personal_info=ai_result["personal_info"],
            job_info=ai_result["job_info"],
            evaluation=ai_result["evaluation"],
            raw_text=extracted_text[:2000],
            original_filename=file.filename
        )

        # 3. Persist to Firestore
        saved_profile = await firestore_repo.save_candidate(candidate_profile)
        return saved_profile

    except Exception as e:
        logger.error(f"Error processing resume upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process resume: {str(e)}"
        )


@app.get("/api/candidates", response_model=List[CandidateProfile])
async def list_user_candidates(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Fetch all candidate profiles belonging strictly to the current authenticated user."""
    return await firestore_repo.list_candidates(current_user.uid)


@app.get("/api/candidates/{candidate_id}", response_model=CandidateProfile)
async def get_candidate_details(candidate_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get single candidate profile by ID with user isolation."""
    candidate = await firestore_repo.get_candidate(current_user.uid, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


# ==============================================================================
# 3. MULTI-TURN COPILOT & INTERVIEW KIT ENDPOINTS
# ==============================================================================
@app.post("/api/candidates/{candidate_id}/chat", response_model=ChatResponse)
async def chat_with_candidate(
    candidate_id: str,
    request: ChatRequest,
    req_obj: Request,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Multi-turn interactive conversation with Gemini grounded in Candidate CV Context.
    Protected by Layer 2 Rate Limiter (Max 25 chats/minute per user/IP).
    """
    client_ip = get_client_ip(req_obj)
    rate_limiter.check_rate_limit(
        identifier=current_user.uid or client_ip,
        route_tag="chat_copilot",
        max_requests=25,
        window_seconds=60
    )

    candidate = await firestore_repo.get_candidate(current_user.uid, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Record user message
    user_msg = ChatMessage(role="user", content=request.message)
    await firestore_repo.save_chat_message(current_user.uid, candidate_id, user_msg)

    # Call Gemini Copilot
    response = await gemini_service.chat_with_candidate_context(
        candidate_data=candidate.model_dump(),
        user_message=request.message,
        history=request.history or []
    )

    # Record model message
    model_msg = ChatMessage(role="model", content=response.reply)
    await firestore_repo.save_chat_message(current_user.uid, candidate_id, model_msg)

    return response


@app.post("/api/candidates/{candidate_id}/interview-kit", response_model=InterviewKitResponse)
async def generate_candidate_interview_kit(
    candidate_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Generate tailor-made interview questions and customized email invitation.
    Protected by Layer 2 Rate Limiter (Max 10 requests/minute per user/IP).
    """
    client_ip = get_client_ip(request)
    rate_limiter.check_rate_limit(
        identifier=current_user.uid or client_ip,
        route_tag="interview_kit",
        max_requests=10,
        window_seconds=60
    )

    candidate = await firestore_repo.get_candidate(current_user.uid, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return await gemini_service.generate_interview_kit(
        candidate_id=candidate_id,
        candidate_data=candidate.model_dump(),
        job_title=candidate.personal_info.position or "Position"
    )


# ==============================================================================
# 4. STATIC FRONTEND HOSTING
# ==============================================================================
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

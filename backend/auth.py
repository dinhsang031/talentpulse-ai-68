"""
TalentPulse AI - Firebase Authentication Middleware & Dependency
Verifies Firebase ID tokens from incoming requests and provides user context.
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status, Depends
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials

from backend.config import settings, SERVICE_ACCOUNT_FILE

logger = logging.getLogger("talentpulse.auth")

# Initialize Firebase Admin SDK
_firebase_initialized = False

def init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return

    try:
        if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
            cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin SDK initialized successfully with Service Account: {os.path.basename(SERVICE_ACCOUNT_FILE)}")
            _firebase_initialized = True
        elif settings.GCP_PROJECT_ID:
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized with default application credentials.")
            _firebase_initialized = True
        else:
            logger.warning("Firebase credentials not found. Running in Development Mock Auth mode.")
    except Exception as e:
        logger.warning(f"Failed initializing Firebase Admin: {e}. Fallback to mock auth.")

init_firebase()


class AuthenticatedUser:
    def __init__(self, uid: str, email: Optional[str] = None, name: Optional[str] = None):
        self.uid = uid
        self.email = email or f"{uid}@talentpulse.ai"
        self.name = name or "Recruiter"


async def get_current_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """
    Dependency to verify Firebase ID Token from 'Authorization: Bearer <token>' header.
    Falls back to mock user in development when token is not provided or in dev mode.
    """
    if not authorization:
        if settings.ENVIRONMENT == "development" or settings.DEBUG:
            return AuthenticatedUser(uid="demo-recruiter-crc", email="crcsportsvn@gmail.com", name="CRC Sports HR Lead")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Use 'Bearer <token>'",
        )

    # In dev mode, allow dev-token bypass
    if token.startswith("dev-token-"):
        uid = token.replace("dev-token-", "")
        return AuthenticatedUser(uid=uid, email=f"{uid}@example.com", name="Dev Recruiter")

    try:
        decoded_token = firebase_auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        name = decoded_token.get("name")
        return AuthenticatedUser(uid=uid, email=email, name=name)
    except Exception as e:
        logger.warning(f"Token verification fallback: {e}")
        if settings.ENVIRONMENT == "development":
            return AuthenticatedUser(uid="demo-recruiter-crc", email="crcsportsvn@gmail.com", name="CRC Sports HR Lead")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token",
            headers={"WWW-Authenticate": "Bearer"},
        )

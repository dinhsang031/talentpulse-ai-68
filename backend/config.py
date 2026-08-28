"""
TalentPulse AI - Application Configuration
Centralized configuration management using Pydantic Settings and .env discovery.
"""

import os
import glob
import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger("talentpulse.config")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env") if os.path.exists(os.path.join(BASE_DIR, ".env")) else ".env"

class Settings(BaseSettings):
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "production"

    # Google Gemini AI Studio API (Loaded securely from Environment / .env)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Google Cloud & Vertex AI Enterprise
    GCP_PROJECT_ID: str = "gen-lang-client-0394973299"
    GCP_LOCATION: str = "us-central1"
    GOOGLE_APPLICATION_CREDENTIALS: str = "backend/credentials/gen-lang-client-0394973299-d70ee52df136.json"
    FIRESTORE_DATABASE: str = "(default)"

    # Firebase Admin SDK Credentials
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "backend/credentials/talent-pulse-ai-firebase-adminsdk-fbsvc-70643cb972.json"

    # Firebase Web Config (For serving to Frontend)
    FIREBASE_WEB_API_KEY: str = ""
    FIREBASE_WEB_AUTH_DOMAIN: str = ""
    FIREBASE_WEB_PROJECT_ID: str = "talent-pulse-ai"
    FIREBASE_WEB_STORAGE_BUCKET: str = ""
    FIREBASE_WEB_MESSAGING_SENDER_ID: str = ""
    FIREBASE_WEB_APP_ID: str = ""

    class Config:
        env_file = ENV_PATH
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# Auto-discover Firebase service account JSON in credentials dir if not explicitly set
def get_service_account_file() -> str:
    if settings.FIREBASE_SERVICE_ACCOUNT_PATH:
        if os.path.isabs(settings.FIREBASE_SERVICE_ACCOUNT_PATH) and os.path.exists(settings.FIREBASE_SERVICE_ACCOUNT_PATH):
            return settings.FIREBASE_SERVICE_ACCOUNT_PATH
        rel_path = os.path.join(BASE_DIR, settings.FIREBASE_SERVICE_ACCOUNT_PATH)
        if os.path.exists(rel_path):
            return rel_path

    # Search credentials dir
    cred_dir = os.path.join(BASE_DIR, "backend", "credentials")
    json_files = glob.glob(os.path.join(cred_dir, "*.json"))
    if json_files:
        return json_files[0]
    return ""

SERVICE_ACCOUNT_FILE = get_service_account_file()
if SERVICE_ACCOUNT_FILE:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_FILE
    logger.info(f"Using Service Account File: {SERVICE_ACCOUNT_FILE}")


def resolve_secret_manager():
    """Optional retrieval from Google Cloud Secret Manager when running on Cloud Run."""
    if not settings.GEMINI_API_KEY and settings.GCP_PROJECT_ID:
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{settings.GCP_PROJECT_ID}/secrets/GEMINI_API_KEY/versions/latest"
            response = client.access_secret_version(request={"name": name})
            val = response.payload.data.decode("UTF-8").strip()
            if val:
                settings.GEMINI_API_KEY = val
                logger.info("Successfully fetched GEMINI_API_KEY from Google Cloud Secret Manager.")
        except Exception:
            pass

resolve_secret_manager()

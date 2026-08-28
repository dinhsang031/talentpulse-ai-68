"""
TalentPulse AI - Firestore Repository Module
Ensures strict per-user document isolation under /users/{userId}/candidates/...
Connects to Cloud Firestore using Service Account credentials with local fallback.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from backend.config import settings, SERVICE_ACCOUNT_FILE
from backend.schemas import CandidateProfile, ChatMessage

logger = logging.getLogger("talentpulse.firestore")

# In-memory store fallback for offline mode
_local_memory_store: Dict[str, Dict[str, Dict[str, Any]]] = {}

class FirestoreRepository:
    def __init__(self):
        self.db = None
        self._init_client()

    def _init_client(self):
        try:
            from google.cloud import firestore
            if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
                self.db = firestore.Client.from_service_account_json(
                    SERVICE_ACCOUNT_FILE,
                    database=settings.FIRESTORE_DATABASE
                )
                logger.info(f"Connected to Cloud Firestore using Service Account (Project: {self.db.project}).")
            elif settings.GCP_PROJECT_ID:
                self.db = firestore.Client(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
                logger.info(f"Connected to Cloud Firestore (Project: {settings.GCP_PROJECT_ID}).")
            else:
                logger.info("Running FirestoreRepository in Local Memory Cache mode.")
        except Exception as e:
            logger.warning(f"Could not connect to Firestore Client: {e}. Falling back to memory store.")
            self.db = None

    async def save_candidate(self, candidate: CandidateProfile) -> CandidateProfile:
        """Save candidate profile under /users/{userId}/candidates/{candidateId}"""
        data = candidate.model_dump()

        if self.db:
            try:
                doc_ref = self.db.collection("users").document(candidate.user_id).collection("candidates").document(candidate.id)
                doc_ref.set(data)
                logger.info(f"Successfully wrote candidate '{candidate.id}' to Firestore under user '{candidate.user_id}'.")
                return candidate
            except Exception as e:
                logger.error(f"Firestore save error: {e}")

        # Local fallback
        if candidate.user_id not in _local_memory_store:
            _local_memory_store[candidate.user_id] = {}
        _local_memory_store[candidate.user_id][candidate.id] = data
        return candidate

    async def get_candidate(self, user_id: str, candidate_id: str) -> Optional[CandidateProfile]:
        """Fetch single candidate profile with user isolation check."""
        if self.db:
            try:
                doc_ref = self.db.collection("users").document(user_id).collection("candidates").document(candidate_id)
                doc = doc_ref.get()
                if doc.exists:
                    return CandidateProfile(**doc.to_dict())
            except Exception as e:
                logger.error(f"Firestore get error: {e}")

        # Local fallback
        user_candidates = _local_memory_store.get(user_id, {})
        data = user_candidates.get(candidate_id)
        if data:
            return CandidateProfile(**data)
        return None

    async def list_candidates(self, user_id: str) -> List[CandidateProfile]:
        """List all candidates belonging strictly to the specified user."""
        if self.db:
            try:
                docs = self.db.collection("users").document(user_id).collection("candidates").order_by("created_at", direction="DESCENDING").stream()
                results = [CandidateProfile(**doc.to_dict()) for doc in docs]
                return results
            except Exception as e:
                logger.error(f"Firestore list error: {e}")

        # Local fallback
        user_candidates = _local_memory_store.get(user_id, {})
        return [CandidateProfile(**item) for item in reversed(list(user_candidates.values()))]

    async def save_chat_message(self, user_id: str, candidate_id: str, message: ChatMessage):
        """Append chat message under /users/{userId}/candidates/{candidateId}/chat_history"""
        data = message.model_dump()
        if self.db:
            try:
                col_ref = self.db.collection("users").document(user_id).collection("candidates").document(candidate_id).collection("chat_history")
                col_ref.add(data)
                return
            except Exception as e:
                logger.error(f"Firestore chat save error: {e}")

    async def get_chat_history(self, user_id: str, candidate_id: str) -> List[ChatMessage]:
        """Fetch chat history for a candidate."""
        if self.db:
            try:
                docs = self.db.collection("users").document(user_id).collection("candidates").document(candidate_id).collection("chat_history").order_by("timestamp").stream()
                return [ChatMessage(**doc.to_dict()) for doc in docs]
            except Exception as e:
                logger.error(f"Firestore chat get error: {e}")
        return []

firestore_repo = FirestoreRepository()

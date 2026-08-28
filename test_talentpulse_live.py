"""
TalentPulse AI - Comprehensive Live Test Suite
Tests live connectivity to:
1. Google AI Studio (Gemini 2.5 Flash API)
2. Cloud Firestore (talent-pulse-ai)
3. Full Extraction & Multi-turn Chat Pipeline
"""

import asyncio
import os
import sys

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.config import settings, SERVICE_ACCOUNT_FILE
from backend.gemini_service import gemini_service
from backend.firestore_service import firestore_repo
from backend.schemas import CandidateProfile, ChatRequest, ChatMessage

SAMPLE_CV = """
NGUYỄN VĂN AN
Email: nguyenvanan.dev@gmail.com | SĐT: 0987654321 | Nơi ở: Hồ Chí Minh
Năm sinh: 1995 | Giới tính: Nam

MỤC TIÊU NGHỀ NGHIỆP:
Senior Cloud Backend Engineer với 6 năm kinh nghiệm phát triển hệ thống microservices chịu tải cao trên Google Cloud Platform và tối ưu hóa quy trình AI/LLM.

KINH NGHIỆM LÀM VIỆC:
1. TechLead / Senior Backend Engineer tại VNG Corporation (2021 - Hiện tại)
- Thiết kế và triển khai kiến trúc microservices trên Google Cloud Run và Kubernetes (GKE), chịu tải hơn 30.000 RPS.
- Xây dựng pipeline tích hợp Gemini API để tự động hóa xử lý 10.000 tài liệu mỗi ngày.
- Quản trị cơ sở dữ liệu Cloud Firestore, Cloud SQL PostgreSQL và tối ưu chi phí hạ tầng giảm 25%.

2. Backend Developer tại Startup Tech (2018 - 2021)
- Phát triển RESTful API và GraphQL bằng Python FastAPI, Docker, Redis.
- Thiết lập CI/CD pipeline tự động với Cloud Build và GitHub Actions.

HỌC VẤN & CHỨNG CHỈ:
- Đại học Bách Khoa TP.HCM (2013 - 2018) — Ngành Khoa học Máy tính — Tốt nghiệp Loại Giỏi.
- Google Cloud Certified Professional Cloud Architect (2023).
- IELTS 7.5.

KỸ NĂNG:
Python, FastAPI, Docker, Google Cloud Run, Firestore, Kubernetes, Gemini API, Redis, PostgreSQL, Git, CI/CD.
"""

async def run_live_tests():
    print("=" * 60)
    print("TEST: TALENTPULSE AI - LIVE INTEGRATION TEST SUITE")
    print(f"* GEMINI MODEL: {settings.GEMINI_MODEL}")
    print(f"* GCP PROJECT:  {settings.GCP_PROJECT_ID}")
    print(f"* CREDENTIALS:  {SERVICE_ACCOUNT_FILE}")
    print("=" * 60)

    # 1. Test Gemini Extraction
    print("\n[1/4] Testing Gemini Multimodal & Structured Extraction...")
    res = await gemini_service.extract_candidate_data(
        cv_text=SAMPLE_CV,
        filename="CV_Nguyen_Van_An.pdf",
        target_position="Senior Cloud Architect",
        jd_text="Yêu cầu 5+ năm kinh nghiệm Python, Cloud Run, GCP, và thiết kế microservices."
    )
    print(f"[OK] Extracted Candidate: {res['personal_info'].fullname}")
    print(f"* Phone: {res['personal_info'].telephone} | Email: {res['personal_info'].email}")
    print(f"* Target Position: {res['personal_info'].position}")
    print(f"* HR Fit Score: {res['evaluation'].score}/10")
    print(f"* Radar Scores: {res['evaluation'].radar.model_dump()}")
    print(f"* HR Consideration: {res['evaluation'].consideration[:120]}...")

    # 2. Test Firestore Save & Retrieve
    print("\n[2/4] Testing Firestore Per-User Isolation...")
    candidate_profile = CandidateProfile(
        id="test_cand_live_001",
        user_id="crcsportsvn@gmail.com",
        personal_info=res["personal_info"],
        job_info=res["job_info"],
        evaluation=res["evaluation"],
        original_filename="CV_Nguyen_Van_An.pdf"
    )
    saved = await firestore_repo.save_candidate(candidate_profile)
    print(f"[OK] Saved Candidate to Firestore: ID={saved.id} under user={saved.user_id}")

    retrieved = await firestore_repo.get_candidate("crcsportsvn@gmail.com", "test_cand_live_001")
    assert retrieved is not None, "Failed retrieving candidate from Firestore"
    print(f"[OK] Retrieved Candidate from Firestore: {retrieved.personal_info.fullname}")

    # 3. Test Multi-turn Chat Copilot
    print("\n[3/4] Testing Multi-turn Candidate Chat Copilot...")
    chat_resp = await gemini_service.chat_with_candidate_context(
        candidate_data=candidate_profile.model_dump(),
        user_message="Ứng viên này có kinh nghiệm làm việc với Cloud Run và chịu tải bao nhiêu RPS?",
        history=[]
    )
    print(f"[OK] Copilot Response:\n{chat_resp.reply}")

    # 4. Test Interview Kit Generation
    print("\n[4/4] Testing Interview Kit Generator...")
    kit = await gemini_service.generate_interview_kit(
        candidate_id="test_cand_live_001",
        candidate_data=candidate_profile.model_dump(),
        job_title="Senior Cloud Architect"
    )
    print(f"[OK] Generated {len(kit.questions)} Technical/Behavioral Questions:")
    for idx, q in enumerate(kit.questions[:2], 1):
        print(f"  Q{idx}: {q.question}")
        print(f"     Objective: {q.objective}")
    print(f"\n[OK] Email Draft Preview:\n{kit.custom_email_draft[:150]}...")

    print("\n" + "=" * 60)
    print("ALL LIVE INTEGRATION TESTS PASSED 100%!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_live_tests())

"""
TalentPulse AI - Pydantic Schemas Module
Enhanced with robust key normalization, alias tolerance,
safe percentage/string cleaning for Radar Metrics,
flexible Interview Kit parsing, and Modern HR Metrics.
"""

import re
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


# ==============================================================================
# 1. AI EXTRACTION CORE SCHEMAS
# ==============================================================================
class PersonalInfoExtract(BaseModel):
    fullname: Optional[str] = Field(default="Candidate", description="Full name of candidate")
    telephone: Optional[str] = Field(default="", description="10-digit telephone number")
    email: Optional[str] = Field(default="", description="Email address")
    city: Optional[str] = Field(default="", description="City / Province")
    yearofbirth: Optional[str] = Field(default="", description="Year of birth (4 digits)")
    gender: Optional[str] = Field(default="", description="Gender (Male / Female)")
    position: Optional[str] = Field(default="Specialist", description="Target or inferred professional title")
    timerequest: Optional[str] = Field(default="", description="Recruitment date request")
    source: Optional[str] = Field(default="Web Upload", description="Source")
    job_code: Optional[str] = Field(default="", description="Job code")
    position_id: Optional[str] = Field(default="", description="Position ID")

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = {}
        for k, v in data.items():
            k_clean = str(k).lower().strip().replace(" ", "_").replace(".", "")
            if "name" in k_clean or "ho_ten" in k_clean:
                normalized["fullname"] = v
            elif "phone" in k_clean or "tel" in k_clean or "sdt" in k_clean:
                normalized["telephone"] = v
            elif "mail" in k_clean:
                normalized["email"] = v
            elif "city" in k_clean or "location" in k_clean or "dia_chi" in k_clean or "noi_o" in k_clean:
                normalized["city"] = v
            elif "birth" in k_clean or "dob" in k_clean or "nam_sinh" in k_clean:
                normalized["yearofbirth"] = v
            elif "gender" in k_clean or "gioi_tinh" in k_clean or "sex" in k_clean:
                normalized["gender"] = v
            elif "position" in k_clean or "vi_tri" in k_clean or "role" in k_clean or "title" in k_clean or "chuc_danh" in k_clean:
                val = str(v).strip()
                if val.lower() not in ["", "unspecified", "n/a", "none", "unknown"]:
                    normalized["position"] = val
            else:
                normalized[k] = v
        return normalized

    @field_validator("*", mode="before")
    @classmethod
    def coerce_to_string(cls, v: Any) -> Any:
        if v is None:
            return ""
        if isinstance(v, list):
            return ", ".join([str(x).strip() for x in v if str(x).strip()])
        return str(v).strip()


class JobInfoExtract(BaseModel):
    truong_tot_nghiep: Optional[str] = Field(default="", description="University / School")
    job_history: Optional[str] = Field(default="", description="Work history")
    skills: Optional[str] = Field(default="", description="Technical and soft skills")
    certification: Optional[str] = Field(default="", description="Certifications and awards")
    nganh_tot_nghiep: Optional[str] = Field(default="", description="Major / Field of study")
    nam_tot_nghiep: Optional[str] = Field(default="", description="Graduation year")
    loai_tot_nghiep: Optional[str] = Field(default="", description="Graduation rank / GPA")
    task_cong_viec: Optional[str] = Field(default="", description="Key tasks and responsibilities")
    bang_cap: Optional[str] = Field(default="Bachelor", description="Degree level")

    @model_validator(mode="before")
    @classmethod
    def normalize_job_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = {}
        for k, v in data.items():
            k_clean = str(k).lower().strip().replace(".", "").replace(" ", "_")
            if "truong" in k_clean or "university" in k_clean or "school" in k_clean or "college" in k_clean or "institution" in k_clean:
                normalized["truong_tot_nghiep"] = v
            elif "skill" in k_clean or "ky_nang" in k_clean or "technolog" in k_clean or "framework" in k_clean or "tool" in k_clean:
                normalized["skills"] = v
            elif "bang_cap" in k_clean or "degree" in k_clean or "qualification" in k_clean:
                normalized["bang_cap"] = v
            elif "nganh" in k_clean or "major" in k_clean or "field" in k_clean or "chuyen_nganh" in k_clean:
                normalized["nganh_tot_nghiep"] = v
            elif "cert" in k_clean or "chung_chi" in k_clean or "award" in k_clean or "chung_nhan" in k_clean:
                normalized["certification"] = v
            elif "history" in k_clean or "kinh_nghiem" in k_clean or "experience" in k_clean:
                normalized["job_history"] = v
            elif "task" in k_clean or "nhiem_vu" in k_clean or "responsibility" in k_clean or "achieve" in k_clean:
                normalized["task_cong_viec"] = v
            elif "nam_tot" in k_clean or "grad_year" in k_clean or "graduation_year" in k_clean:
                normalized["nam_tot_nghiep"] = v
            elif "loai_tot" in k_clean or "gpa" in k_clean or "rank" in k_clean or "grade" in k_clean:
                normalized["loai_tot_nghiep"] = v
            else:
                normalized[k] = v
        return normalized

    @field_validator("*", mode="before")
    @classmethod
    def coerce_to_string(cls, v: Any) -> Any:
        if v is None:
            return ""
        if isinstance(v, list):
            return "\n".join([f"- {str(x).strip()}" if not str(x).strip().startswith("-") else str(x).strip() for x in v if str(x).strip()])
        return str(v).strip()


class RadarMetrics(BaseModel):
    hard_skills: int = Field(default=80, description="Hard skills match percentage (0-100)")
    domain_experience: int = Field(default=75, description="Domain experience match percentage (0-100)")
    education: int = Field(default=80, description="Education and certification score (0-100)")
    career_stability: int = Field(default=85, description="Career growth and stability score (0-100)")

    @model_validator(mode="before")
    @classmethod
    def normalize_radar_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = {}
        for k, v in data.items():
            k_clean = str(k).lower().strip().replace(" ", "_").replace(".", "")
            if "skill" in k_clean or "hard" in k_clean or "tech" in k_clean:
                normalized["hard_skills"] = v
            elif "exp" in k_clean or "domain" in k_clean or "kinh_nghiem" in k_clean:
                normalized["domain_experience"] = v
            elif "edu" in k_clean or "acad" in k_clean or "hoc_van" in k_clean or "cert" in k_clean or "degree" in k_clean or "qualification" in k_clean:
                normalized["education"] = v
            elif "stab" in k_clean or "growth" in k_clean or "on_dinh" in k_clean:
                normalized["career_stability"] = v
            else:
                normalized[k] = v
        return normalized

    @field_validator("*", mode="before")
    @classmethod
    def clean_percentage_or_score(cls, v: Any) -> int:
        if v is None:
            return 75
        cleaned = re.sub(r"[^0-9.]", "", str(v))
        try:
            val = float(cleaned)
            # Scale 0-10 up to 0-100
            if val <= 10.0 and val > 0:
                val *= 10
            # Ensure minimum baseline of 50 for realistic visual display
            return int(round(max(50, min(100, val))))
        except Exception:
            return 75


class EvaluationScoreOutput(BaseModel):
    score: int = Field(default=5, description="Integer score 1-10")
    consideration: Optional[str] = Field(default="", description="Detailed evaluation explanation")
    suitability: Optional[str] = Field(default="", description="Bullet points of strengths")
    radar: Optional[RadarMetrics] = Field(default_factory=RadarMetrics, description="Multi-dimensional radar scores")
    red_flags: Optional[List[str]] = Field(default_factory=list, description="List of potential red flags")

    @field_validator("score", mode="before")
    @classmethod
    def coerce_to_integer(cls, v: Any) -> int:
        if v is None:
            return 5
        try:
            val = float(str(v).replace(",", "."))
            return int(round(val))
        except Exception:
            return 5

    @field_validator("consideration", "suitability", mode="before")
    @classmethod
    def coerce_text_or_list(cls, v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, list):
            return "\n".join([f"- {str(x).strip()}" if not str(x).strip().startswith("-") else str(x).strip() for x in v if str(x).strip()])
        return str(v).strip()


# ==============================================================================
# 2. FIRESTORE & WEB PLATFORM SCHEMAS
# ==============================================================================
class CandidateProfile(BaseModel):
    id: str = Field(description="Unique candidate identifier")
    user_id: str = Field(description="Owner Recruiter User ID")
    personal_info: PersonalInfoExtract
    job_info: JobInfoExtract
    evaluation: EvaluationScoreOutput
    raw_text: Optional[str] = Field(default="", description="Raw extracted text")
    original_filename: str = Field(default="resume.pdf")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class JobDescription(BaseModel):
    id: Optional[str] = None
    title: str = Field(description="Job Title")
    requirements: str = Field(description="Detailed Job Description & Requirements")
    target_experience_years: int = Field(default=2)
    department: Optional[str] = Field(default="General")


class ChatMessage(BaseModel):
    role: Literal["user", "model", "system"]
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatRequest(BaseModel):
    message: str = Field(description="User prompt/question to the candidate copilot")
    history: Optional[List[ChatMessage]] = Field(default_factory=list)
    candidate_data: Optional[Dict[str, Any]] = Field(default=None, description="Optional payload containing client candidate dossier for stateless scaling")


class ChatResponse(BaseModel):
    reply: str
    sources_cited: Optional[List[str]] = Field(default_factory=list)


class InterviewQuestionItem(BaseModel):
    question: str = Field(default="Please describe your experience in your most recent project.")
    objective: str = Field(default="Evaluate core competence and practical execution.")
    expected_answer_indicators: str = Field(default="Demonstrates clear methodology, technical depth, and business impact.")

    @model_validator(mode="before")
    @classmethod
    def normalize_question_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = {}
        for k, v in data.items():
            k_clean = str(k).lower().strip().replace(" ", "_").replace(".", "")
            if "quest" in k_clean or "cau_hoi" in k_clean:
                normalized["question"] = v
            elif "obj" in k_clean or "purp" in k_clean or "goal" in k_clean or "muc_tieu" in k_clean or "target" in k_clean:
                normalized["objective"] = v
            elif "expect" in k_clean or "answer" in k_clean or "indicat" in k_clean or "tieu_chi" in k_clean or "criteria" in k_clean:
                normalized["expected_answer_indicators"] = v
            else:
                normalized[k] = v
        
        # Ensure fallback defaults if empty
        if not normalized.get("question"):
            normalized["question"] = "Can you elaborate on your main achievements in your past roles?"
        if not normalized.get("objective"):
            normalized["objective"] = "Assess problem solving and domain experience."
        if not normalized.get("expected_answer_indicators"):
            normalized["expected_answer_indicators"] = "Specific metrics, technical details, and proactive ownership."
            
        return normalized


class InterviewKitResponse(BaseModel):
    candidate_id: str
    candidate_name: str
    job_title: str
    questions: List[InterviewQuestionItem] = Field(default_factory=list)
    custom_email_draft: str = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def normalize_kit_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "email" in data and not data.get("custom_email_draft"):
            data["custom_email_draft"] = data["email"]
        elif "email_draft" in data and not data.get("custom_email_draft"):
            data["custom_email_draft"] = data["email_draft"]
        elif "invitation_email" in data and not data.get("custom_email_draft"):
            data["custom_email_draft"] = data["invitation_email"]
        return data

"""
TalentPulse AI - Gemini Service Module (Official Google GenAI SDK)
Handles Multimodal Direct Document Extraction (PDF, Images, Scans),
Structured JSON Parsing, Multi-turn Copilot, and Resilient Interview Kits.
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from backend.config import settings
from backend.schemas import (
    PersonalInfoExtract,
    JobInfoExtract,
    EvaluationScoreOutput,
    RadarMetrics,
    ChatMessage,
    ChatResponse,
    InterviewKitResponse,
    InterviewQuestionItem
)
from backend.prompts import (
    PERSONAL_INFO_SYSTEM_PROMPT,
    format_personal_info_input,
    JOB_INFO_SYSTEM_PROMPT,
    format_summarization_prompt,
    HR_EVALUATOR_SYSTEM_PROMPT,
    format_hr_evaluation_user_prompt,
    CANDIDATE_COPILOT_SYSTEM_PROMPT,
    INTERVIEW_KIT_PROMPT
)

logger = logging.getLogger("talentpulse.gemini")

class GeminiService:
    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Configured Official Google GenAI Client.")
        else:
            logger.warning("GEMINI_API_KEY is not set. Running in Mock fallback mode.")
            self.client = None

    def _clean_json_text(self, text: str) -> str:
        """Robustly extract and clean JSON object from LLM response."""
        if not text:
            return "{}"
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        # Check for outermost JSON object or list
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if match:
            return match.group(0)
        return cleaned

    async def extract_candidate_data(
        self,
        cv_text: str,
        filename: str,
        target_position: str,
        jd_text: str = "",
        file_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute 3-phase Multimodal AI extraction & evaluation:
        Supports direct PDF/Image document stream + OCR extraction.
        1. Personal Info & Role Extraction
        2. Job & Technical Skills & Education Extraction
        3. HR Fit & Radar Evaluation
        """
        if not self.client:
            personal = PersonalInfoExtract(
                fullname="Nguyen Van A",
                telephone="0912345678",
                email="nguyenvana@example.com",
                city="Ho Chi Minh",
                yearofbirth="1996",
                gender="Male",
                position=target_position or "Senior Data Analyst"
            )
            job = JobInfoExtract(
                truong_tot_nghiep="Bach Khoa University",
                job_history="- 4 years Senior Data Analyst at TechCorp\n- 2 years BI Engineer at StartupX",
                skills="- Power BI\n- SQL\n- Python\n- Machine Learning\n- RPA\n- Docker\n- GCP",
                certification="- Google Data Analytics Professional Certificate\n- IELTS 7.5",
                nganh_tot_nghiep="Computer Science",
                nam_tot_nghiep="2018",
                loai_tot_nghiep="Very Good",
                task_cong_viec="- Automated data pipelines\n- Built predictive models",
                bang_cap="Bachelor"
            )
            eval_score = EvaluationScoreOutput(
                score=9,
                consideration="Candidate demonstrates deep expertise in data analysis and automation pipelines.",
                suitability="- 6+ years hands-on experience in BI and data engineering.\n- Google Certified Data Analyst.",
                radar=RadarMetrics(hard_skills=92, domain_experience=88, education=85, career_stability=90),
                red_flags=[]
            )
            return {
                "personal_info": personal,
                "job_info": job,
                "evaluation": eval_score,
                "summary": "Experienced Data Analyst / BI Specialist with verified Google certifications."
            }

        try:
            # Build input contents (Multimodal part if PDF/Image available)
            doc_parts = []
            if file_bytes and mime_type and ("pdf" in mime_type or "image" in mime_type):
                doc_parts.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))

            # Phase 1: Personal Info & Professional Role
            p1_input = format_personal_info_input(cv_text, filename, target_position)
            p1_prompt = f"{PERSONAL_INFO_SYSTEM_PROMPT}\n\nCandidate Document / Text:\n{p1_input}"
            p1_contents = doc_parts + [p1_prompt] if doc_parts else [p1_prompt]

            resp1 = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=p1_contents
            )
            clean1 = self._clean_json_text(resp1.text)
            p1_dict = json.loads(clean1)
            personal_info = PersonalInfoExtract.model_validate(p1_dict)

            # Phase 2: Job Info & Skills & Education
            p2_prompt = f"{JOB_INFO_SYSTEM_PROMPT}\n\nCandidate Document / Text Content:\n{cv_text if cv_text.strip() else 'Please parse the attached CV document.'}"
            p2_contents = doc_parts + [p2_prompt] if doc_parts else [p2_prompt]

            resp2 = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=p2_contents
            )
            clean2 = self._clean_json_text(resp2.text)
            p2_dict = json.loads(clean2)
            job_info = JobInfoExtract.model_validate(p2_dict)

            # Resolve Position Title if unspecified
            if not personal_info.position or personal_info.position.lower() in ["unspecified", "unspecified position", "specialist", ""]:
                if target_position and target_position.lower() not in ["unspecified", "unspecified position", ""]:
                    personal_info.position = target_position
                elif job_info.job_history:
                    # Infer first role title from job history (e.g. "HR Data Analyst")
                    first_line = job_info.job_history.split("\n")[0].replace("-", "").strip()
                    title_match = re.search(r"^(.*?)(?:\sat|\s@|\s\(|\:|\-|\d{4})", first_line, re.IGNORECASE)
                    if title_match and len(title_match.group(1).strip()) > 3:
                        personal_info.position = title_match.group(1).strip()
                    else:
                        personal_info.position = "Data & Automation Specialist"
                else:
                    personal_info.position = "Professional Specialist"

            # Phase 3: Summarization & HR Evaluation
            summary_prompt = format_summarization_prompt(
                city=personal_info.city or "",
                birthdate=personal_info.yearofbirth or "",
                certification=job_info.certification or "",
                job_history=job_info.job_history or "",
                skills=job_info.skills or "",
                job_task=job_info.task_cong_viec or "",
                grad_rank=job_info.loai_tot_nghiep or "",
                grad_major=job_info.nganh_tot_nghiep or "",
                grad_school=job_info.truong_tot_nghiep or ""
            )
            summary_resp = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[summary_prompt]
            )
            candidate_summary = summary_resp.text.strip()

            eval_user_prompt = format_hr_evaluation_user_prompt(
                job_title=personal_info.position,
                summary=candidate_summary,
                jd_text=jd_text
            )
            eval_full_prompt = f"{HR_EVALUATOR_SYSTEM_PROMPT}\n\n{eval_user_prompt}"
            eval_resp = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[eval_full_prompt]
            )
            clean_eval = self._clean_json_text(eval_resp.text)
            eval_dict = json.loads(clean_eval)
            evaluation = EvaluationScoreOutput.model_validate(eval_dict)

            return {
                "personal_info": personal_info,
                "job_info": job_info,
                "evaluation": evaluation,
                "summary": candidate_summary
            }

        except Exception as e:
            logger.error(f"Error in Gemini extraction pipeline: {e}")
            raise e

    async def chat_with_candidate_context(
        self,
        candidate_data: Dict[str, Any],
        user_message: str,
        history: List[ChatMessage]
    ) -> ChatResponse:
        """Multi-turn conversation with Candidate Context."""
        if not self.client:
            name = candidate_data.get('personal_info', {}).get('fullname', 'Ứng viên')
            skills = candidate_data.get('job_info', {}).get('skills', 'chuyên môn')
            return ChatResponse(
                reply=f"Dựa trên hồ sơ của ứng viên {name}, ứng viên có thế mạnh về: {skills}.",
                sources_cited=["Section: Skills & Work Experience"]
            )

        try:
            context_str = f"""
CANDIDATE CONTEXT:
- Name: {candidate_data.get('personal_info', {}).get('fullname')}
- Applied/Current Position: {candidate_data.get('personal_info', {}).get('position')}
- Skills: {candidate_data.get('job_info', {}).get('skills')}
- Work History: {candidate_data.get('job_info', {}).get('job_history')}
- Education: {candidate_data.get('job_info', {}).get('truong_tot_nghiep')} ({candidate_data.get('job_info', {}).get('nganh_tot_nghiep')}) - Degree: {candidate_data.get('job_info', {}).get('bang_cap')}
- Certifications: {candidate_data.get('job_info', {}).get('certification')}
- HR Fit Score: {candidate_data.get('evaluation', {}).get('score')}/10
- HR Evaluation: {candidate_data.get('evaluation', {}).get('consideration')}
"""
            full_prompt = f"{CANDIDATE_COPILOT_SYSTEM_PROMPT}\n\n{context_str}\n\nRecruiter Question: {user_message}"
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[full_prompt]
            )
            return ChatResponse(reply=response.text.strip(), sources_cited=["Candidate Profile & Resume Extraction"])

        except Exception as e:
            logger.error(f"Error in Gemini chat copilot: {e}")
            raise e

    async def generate_interview_kit(
        self,
        candidate_id: str,
        candidate_data: Dict[str, Any],
        job_title: str
    ) -> InterviewKitResponse:
        """Generate structured interview questions and customized email invitation."""
        name = candidate_data.get("personal_info", {}).get("fullname", "Candidate")
        position = job_title or candidate_data.get("personal_info", {}).get("position") or "Specialist"

        if not self.client:
            return InterviewKitResponse(
                candidate_id=candidate_id,
                candidate_name=name,
                job_title=position,
                questions=[
                    InterviewQuestionItem(
                        question="Bạn có thể chia sẻ chi tiết về dự án tự động hóa hoặc phân tích dữ liệu nổi bật nhất mà bạn từng xây dựng không?",
                        objective="Đánh giá năng lực thiết kế hệ thống, tư duy phân tích và kỹ năng giải quyết bài toán thực tế.",
                        expected_answer_indicators="Nêu rõ bài toán kinh doanh, công cụ sử dụng (Power BI, SQL, Python), số liệu cải thiện (ví dụ giảm 90% thời gian báo cáo)."
                    ),
                    InterviewQuestionItem(
                        question="Khi xây dựng mô hình AI Agent bóc tách dữ liệu đạt độ chính xác 90%, bạn đã xử lý các trường hợp dữ liệu phi cấu trúc hoặc lỗi như thế nào?",
                        objective="Đánh giá kỹ năng xử lý ngoại lệ và tối ưu hóa độ chính xác mô hình AI/LLM.",
                        expected_answer_indicators="Có chiến lược prompt engineering, fallback OCR, regex validation, và monitoring."
                    )
                ],
                custom_email_draft=f"Chào {name},\n\nPhòng Tuyển dụng rất ấn tượng với hồ sơ chuyên môn của bạn cho vị trí {position}. Chúng tôi trân trọng mời bạn tham gia buổi phỏng vấn trao đổi chuyên sâu..."
            )

        try:
            prompt = f"""{INTERVIEW_KIT_PROMPT}

Candidate Details:
- Name: {name}
- Position: {position}
- Skills: {candidate_data.get('job_info', {}).get('skills')}
- Work History: {candidate_data.get('job_info', {}).get('job_history')}
- Education: {candidate_data.get('job_info', {}).get('truong_tot_nghiep')} ({candidate_data.get('job_info', {}).get('nganh_tot_nghiep')})
- Certifications: {candidate_data.get('job_info', {}).get('certification')}
- HR Considerations: {candidate_data.get('evaluation', {}).get('consideration')}
"""
            resp = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[prompt]
            )
            clean_json = self._clean_json_text(resp.text)
            data = json.loads(clean_json)

            # Handle list vs dict response
            if isinstance(data, list):
                raw_questions = data
                data = {"questions": raw_questions}

            raw_questions = data.get("questions") or data.get("interview_questions") or []
            questions = [InterviewQuestionItem.model_validate(q) for q in raw_questions]

            # Fallback if no questions parsed
            if not questions:
                questions = [
                    InterviewQuestionItem(
                        question=f"Can you walk us through the most impactful project in your role as {position}?",
                        objective="Assess practical problem solving and technical depth.",
                        expected_answer_indicators="Detailed metrics, tools utilized, and strategic outcomes."
                    )
                ]

            email_draft = (
                data.get("custom_email_draft")
                or data.get("email_draft")
                or data.get("email")
                or f"Dear {name},\n\nWe were highly impressed with your background in {position} and would like to invite you for an interview..."
            )

            return InterviewKitResponse(
                candidate_id=candidate_id,
                candidate_name=name,
                job_title=position,
                questions=questions,
                custom_email_draft=email_draft
            )
        except Exception as e:
            logger.error(f"Error generating interview kit: {e}")
            # Fallback instead of crashing with 500
            return InterviewKitResponse(
                candidate_id=candidate_id,
                candidate_name=name,
                job_title=position,
                questions=[
                    InterviewQuestionItem(
                        question=f"Can you explain your approach to solving complex challenges in {position}?",
                        objective="Evaluate domain expertise and proactive problem-solving.",
                        expected_answer_indicators="Concrete examples with technical frameworks and measurable business impact."
                    )
                ],
                custom_email_draft=f"Dear {name},\n\nWe would like to invite you for an interview for the {position} role..."
            )

gemini_service = GeminiService()

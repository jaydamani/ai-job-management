import base64
import json
import logging
from typing import Any, Dict

import litellm

from app.config import settings

logger = logging.getLogger(__name__)

RESUME_SYSTEM_PROMPT = """You are a resume data extractor. Your only job is to read raw resume text and return a single valid JSON object — no preamble, no explanation, no markdown fences.

Return exactly this schema:
{
  "name":                  string | null,
  "email":                 string | null,
  "phone":                 string | null,
  "current_title":         string | null,
  "current_company":       string | null,
  "summary":               string | null,
  "skills":                string[],
  "experience": [
    {
      "title":       string | null,
      "company":     string | null,
      "duration":    string | null,
      "description": string | null
    }
  ],
  "education": [
    {
      "degree":      string | null,
      "institution": string | null,
      "year":        string | null
    }
  ],
  "total_experience_years": number | null
}

Rules:
- If a field cannot be determined from the text, set it to null.
- skills and experience and education must always be arrays (empty array if no data found).
- total_experience_years must be a number (float acceptable), not a string.
- Do not invent or infer information not present in the text.
- Return only the JSON object, starting with { and ending with }."""

FIT_SYSTEM_PROMPT = """You are a technical recruiter evaluating candidate-job fit. Your only job is to return a single valid JSON object — no preamble, no explanation, no markdown fences.

Scoring rubric:
- Use the job description and required_skills array as the primary scoring criteria.
- Score 0–100: 0 means no relevant match, 100 means exact fit on all criteria.
- strengths: skills or experiences where the candidate clearly meets or exceeds the role.
- gaps: required skills or experience levels the candidate appears to lack.
- explanation: 2–4 concise sentences summarizing the overall fit. Do not repeat the score numerically in the explanation.

Return exactly this schema:
{
  "score":       number,
  "explanation": string,
  "strengths":   string[],
  "gaps":        string[]
}

Rules:
- score must be an integer between 0 and 100 inclusive.
- strengths and gaps must always be arrays (empty array if none).
- explanation must be 2–4 sentences.
- If the candidate data is too sparse to score, return score: 0 and explain why in the explanation field.
- Return only the JSON object, starting with { and ending with }."""


def _safe_parse_json(raw: str) -> Dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in response: {raw[:200]}")
    return json.loads(raw[start:end])


async def parse_resume(pdf_bytes: bytes) -> Dict[str, Any]:
    is_claude = settings.AI_MODEL.startswith("claude")

    if is_claude:
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
        user_content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
            },
            {"type": "text", "text": "Extract structured data from this resume."},
        ]
    else:
        import pdfplumber
        from io import BytesIO

        text_parts = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
        extracted_text = "\n".join(text_parts)
        if len(extracted_text.strip()) < 50:
            raise ValueError("UNSCANNABLE_PDF")
        user_content = f"Extract structured data from the following resume text:\n\n--- RESUME TEXT START ---\n{extracted_text}\n--- RESUME TEXT END ---"

    response = await litellm.acompletion(
        model=settings.AI_MODEL,
        messages=[
            {"role": "system", "content": RESUME_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        max_tokens=2048,
        temperature=0.1,
    )
    raw = response.choices[0].message.content
    try:
        return _safe_parse_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        logger.error("Resume parse JSON error: %s | raw: %.200s", e, raw)
        raise


async def score_fit(job, parsed_resume: Dict[str, Any]) -> Dict[str, Any]:
    def _fmt_experience(exp_list):
        lines = []
        for e in exp_list:
            title = e.get("title") or "Unknown title"
            company = e.get("company") or "Unknown company"
            duration = e.get("duration") or ""
            lines.append(f"  - {title} at {company} ({duration})")
        return "\n".join(lines) if lines else "  - None listed"

    def _fmt_education(edu_list):
        lines = []
        for e in edu_list:
            degree = e.get("degree") or "Unknown degree"
            institution = e.get("institution") or "Unknown institution"
            year = e.get("year") or ""
            lines.append(f"  - {degree} from {institution} ({year})")
        return "\n".join(lines) if lines else "  - None listed"

    user_prompt = (
        f"Evaluate this candidate's fit for the job below.\n\n"
        f"--- JOB DESCRIPTION ---\n"
        f"Title: {job.title}\n"
        f"Department: {job.department or 'Not specified'}\n"
        f"Description: {job.description}\n"
        f"Required skills: {', '.join(job.required_skills or [])}\n"
        f"Experience level: {job.experience_level or 'Not specified'}\n"
        f"Employment type: {job.employment_type or 'Not specified'}\n\n"
        f"--- CANDIDATE PROFILE ---\n"
        f"Name: {parsed_resume.get('name') or 'Unknown'}\n"
        f"Current title: {parsed_resume.get('current_title') or 'Not specified'}\n"
        f"Summary: {parsed_resume.get('summary') or 'Not provided'}\n"
        f"Total experience: {parsed_resume.get('total_experience_years') or 'Unknown'} years\n"
        f"Skills: {', '.join(parsed_resume.get('skills') or [])}\n"
        f"Experience:\n{_fmt_experience(parsed_resume.get('experience') or [])}\n"
        f"Education:\n{_fmt_education(parsed_resume.get('education') or [])}\n"
        f"--- END ---"
    )

    response = await litellm.acompletion(
        model=settings.AI_MODEL,
        messages=[
            {"role": "system", "content": FIT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=1024,
        temperature=0.1,
    )
    raw = response.choices[0].message.content
    try:
        return _safe_parse_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        logger.error("Fit score JSON error: %s | raw: %.200s", e, raw)
        raise

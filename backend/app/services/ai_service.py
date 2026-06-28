import base64
import json
import logging
from datetime import date
from typing import Any, Dict, List, Optional

import pymupdf as fitz
import litellm

from app.config import settings
from app.services.skill_taxonomy import normalize_skills

logger = logging.getLogger(__name__)

# ── JSON Schemas for structured output ────────────────────────────────────────

RESUME_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "name", "email", "phone", "current_title", "current_company",
        "summary", "skills", "experience", "education", "total_experience_years",
    ],
    "properties": {
        "name":                  {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "email":                 {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "phone":                 {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "current_title":         {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "current_company":       {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "summary":               {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "skills":                {"type": "array", "items": {"type": "string"}},
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "company", "start_year", "start_month", "end_year", "end_month", "description"],
                "properties": {
                    "title":       {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "company":     {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "start_year":  {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                    "start_month": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                    "end_year":    {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                    "end_month":   {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                    "description": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["degree", "institution", "year"],
                "properties": {
                    "degree":      {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "institution": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "year":        {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
            },
        },
        "total_experience_years": {"anyOf": [{"type": "number"}, {"type": "null"}]},
    },
}

# Keep a separate schema name so cached structured-output schemas don't conflict
_RESUME_SCHEMA_V2_NAME = "resume_extraction_v2"

FIT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["score", "explanation", "strengths", "gaps"],
    "properties": {
        "score":       {"type": "integer", "minimum": 0, "maximum": 100},
        "explanation": {"type": "string"},
        "strengths":   {"type": "array", "items": {"type": "string"}},
        "gaps":        {"type": "array", "items": {"type": "string"}},
    },
}

# ── System prompts ─────────────────────────────────────────────────────────────

def _resume_system_prompt() -> str:
    today = date.today()
    return (
        f"Today's date is {today.strftime('%B %d, %Y')}. "
        "You are a resume data extractor. Extract all structured information from the provided resume. "
        "Reply ONLY with raw JSON — no markdown fences, no text before or after. "
        "Use EXACTLY these field names: name, email, phone, current_title, current_company, "
        "summary, skills, experience, education, total_experience_years. "
        "Do NOT invent new field names. "
        "Set any field that cannot be determined to null. "
        "skills, experience, and education must always be arrays (empty if none found). "
        "For each experience entry extract: start_year (integer), start_month (1–12 integer or null), "
        "end_year (integer or null — null means the role is current/present), "
        "end_month (1–12 integer or null). "
        "Use today's date for any role described as current, present, or ongoing. "
        "total_experience_years must be a number, not a string."
    )

FIT_SYSTEM_PROMPT = (
    "You are a technical recruiter evaluating candidate-job fit. "
    "Reply ONLY with raw JSON — no markdown fences, no text before or after. "
    "Score 0–100: 0 means no relevant match, 100 means exact fit on all criteria. "
    "strengths: skills or experiences where the candidate clearly meets or exceeds the role. "
    "gaps: required skills or experience levels the candidate appears to lack. "
    "explanation: 2–4 concise sentences summarizing overall fit."
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _pdf_to_image_blocks(pdf_bytes: bytes) -> List[dict]:
    """Render each PDF page to a PNG and return OpenAI-compatible image_url blocks."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    blocks = []
    # 2× zoom ≈ 144 DPI — legible for vision models without excessive token cost
    matrix = fitz.Matrix(2, 2)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        b64 = base64.b64encode(pix.tobytes("png")).decode()
        blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })
    doc.close()
    if not blocks:
        raise ValueError("UNSCANNABLE_PDF")
    return blocks


def _compute_total_experience_years(experience: List[dict]) -> Optional[float]:
    """Merge overlapping employment intervals and return total years, rounded to 1 dp."""
    today = date.today()
    intervals = []
    for exp in experience:
        sy = exp.get("start_year")
        if not sy:
            continue
        sm = exp.get("start_month") or 1
        ey = exp.get("end_year")
        em = exp.get("end_month") or 12
        if ey is None:
            ey, em = today.year, today.month
        start = sy * 12 + sm
        end = ey * 12 + em
        if end >= start:
            intervals.append((start, end))
    if not intervals:
        return None
    intervals.sort()
    merged: List[List[int]] = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    total_months = sum(e - s for s, e in merged)
    return round(total_months / 12, 1)


def _completion_kwargs(schema_name: str, schema: dict) -> dict:
    return {
        "model": settings.AI_MODEL,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": schema,
            },
        },
        "temperature": 0.1,
    }


# ── Public API ─────────────────────────────────────────────────────────────────

async def parse_resume(pdf_bytes: bytes) -> Dict[str, Any]:
    image_blocks = _pdf_to_image_blocks(pdf_bytes)
    user_content = [
        {"type": "text", "text": "Extract structured data from this resume."},
        *image_blocks,
    ]
    response = await litellm.acompletion(
        **_completion_kwargs(_RESUME_SCHEMA_V2_NAME, RESUME_SCHEMA),
        messages=[
            {"role": "system", "content": _resume_system_prompt()},
            {"role": "user", "content": user_content},
        ],
        max_tokens=2048,
    )
    data = json.loads(response.choices[0].message.content)
    data["skills"] = normalize_skills(data.get("skills") or [])
    computed = _compute_total_experience_years(data.get("experience") or [])
    if computed is not None:
        data["total_experience_years"] = computed
    return data


async def score_fit(job, parsed_resume: Dict[str, Any]) -> Dict[str, Any]:
    def _fmt_experience(exp_list):
        lines = [
            f"  - {e.get('title') or 'Unknown'} at {e.get('company') or 'Unknown'} ({e.get('duration') or ''})"
            for e in exp_list
        ]
        return "\n".join(lines) if lines else "  - None listed"

    def _fmt_education(edu_list):
        lines = [
            f"  - {e.get('degree') or 'Unknown'} from {e.get('institution') or 'Unknown'} ({e.get('year') or ''})"
            for e in edu_list
        ]
        return "\n".join(lines) if lines else "  - None listed"

    user_prompt = (
        f"Evaluate this candidate's fit for the job below.\n\n"
        f"--- JOB ---\n"
        f"Title: {job.title}\n"
        f"Department: {job.department or 'Not specified'}\n"
        f"Description: {job.description}\n"
        f"Required skills: {', '.join(job.required_skills or [])}\n"
        f"Experience level: {job.experience_level or 'Not specified'}\n"
        f"Employment type: {job.employment_type or 'Not specified'}\n\n"
        f"--- CANDIDATE ---\n"
        f"Name: {parsed_resume.get('name') or 'Unknown'}\n"
        f"Current title: {parsed_resume.get('current_title') or 'Not specified'}\n"
        f"Summary: {parsed_resume.get('summary') or 'Not provided'}\n"
        f"Total experience: {parsed_resume.get('total_experience_years') or 'Unknown'} years\n"
        f"Skills: {', '.join(parsed_resume.get('skills') or [])}\n"
        f"Experience:\n{_fmt_experience(parsed_resume.get('experience') or [])}\n"
        f"Education:\n{_fmt_education(parsed_resume.get('education') or [])}"
    )

    response = await litellm.acompletion(
        **_completion_kwargs("fit_scoring", FIT_SCHEMA),
        messages=[
            {"role": "system", "content": FIT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1024,
    )
    return json.loads(response.choices[0].message.content)

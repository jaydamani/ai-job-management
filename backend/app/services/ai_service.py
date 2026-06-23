import base64
import json
import logging
from typing import Any, Dict, List

import pymupdf as fitz
import litellm

from app.config import settings

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
                "required": ["title", "company", "duration", "description"],
                "properties": {
                    "title":       {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "company":     {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "duration":    {"anyOf": [{"type": "string"}, {"type": "null"}]},
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

RESUME_SYSTEM_PROMPT = (
    "You are a resume data extractor. Extract all structured information from the provided resume images. "
    "Set any field that cannot be determined to null. "
    "skills, experience, and education must always be arrays (empty if none found). "
    "total_experience_years must be a number, not a string."
)

FIT_SYSTEM_PROMPT = (
    "You are a technical recruiter evaluating candidate-job fit. "
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


def _completion_kwargs(schema_name: str, schema: dict) -> dict:
    return {
        "model": settings.AI_MODEL,
        "api_key": settings.OPENROUTER_API_KEY,
        "api_base": settings.OPENROUTER_API_BASE,
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
        **_completion_kwargs("resume_extraction", RESUME_SCHEMA),
        messages=[
            {"role": "system", "content": RESUME_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=2048,
    )
    return json.loads(response.choices[0].message.content)


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

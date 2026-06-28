"""Live integration tests for app.services.ai_service.

These tests make real API calls to the configured AI provider.
They are skipped automatically when OPENROUTER_API_KEY (or the relevant
key for the configured model) is not set in the environment / .env file.

Run:
    cd backend
    pytest tests/test_ai_service.py -v -s
"""
import os
import pathlib
import types

_root_env = pathlib.Path(__file__).parent.parent.parent / ".env"
if _root_env.exists():
    from dotenv import load_dotenv
    load_dotenv(_root_env, override=False)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-for-ai-tests")

import asyncio

import pymupdf as fitz
import pytest
import pytest_asyncio

from app.config import settings
from app.services.ai_service import parse_resume, score_fit


@pytest.fixture(autouse=True)
async def rate_limit_guard():
    """Pause between tests to respect Gemini free-tier RPM limits (10–15 RPM)."""
    yield
    await asyncio.sleep(8)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_resume_pdf() -> bytes:
    """Return a minimal in-memory PDF with plausible resume text."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    text = (
        "Jane Smith\n"
        "jane.smith@example.com | +1-555-0100\n\n"
        "SUMMARY\n"
        "Experienced Python backend engineer with 5 years building REST APIs.\n\n"
        "EXPERIENCE\n"
        "Senior Software Engineer — Acme Corp (2021–Present)\n"
        "  • Designed and maintained FastAPI microservices.\n"
        "  • Reduced p99 latency by 40% via query optimisation.\n\n"
        "Software Engineer — Beta Inc (2019–2021)\n"
        "  • Built Django REST APIs serving 2M+ requests/day.\n\n"
        "SKILLS\n"
        "Python, FastAPI, Django, PostgreSQL, Docker, AWS, Redis\n\n"
        "EDUCATION\n"
        "B.Sc. Computer Science — State University (2019)\n"
    )
    page.insert_text((50, 50), text, fontsize=11)
    return doc.tobytes()


def _make_job():
    """Return a minimal job-like object (SimpleNamespace mirroring the ORM model)."""
    return types.SimpleNamespace(
        title="Senior Backend Engineer",
        department="Engineering",
        description="Build and maintain FastAPI-based microservices for our SaaS platform.",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        experience_level="Senior",
        employment_type="Full-time",
    )


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def resume_pdf() -> bytes:
    return _make_resume_pdf()


@pytest.fixture(scope="module")
def sample_job():
    return _make_job()


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_parse_resume_returns_expected_fields(resume_pdf):
    result = await parse_resume(resume_pdf)

    required_fields = [
        "name", "email", "phone", "current_title", "current_company",
        "summary", "skills", "experience", "education", "total_experience_years",
    ]
    for field in required_fields:
        assert field in result, f"Missing field: {field}"

    # arrays must be lists
    assert isinstance(result["skills"], list)
    assert isinstance(result["experience"], list)
    assert isinstance(result["education"], list)

    # name should be extracted from the obvious header
    assert result["name"] and "smith" in result["name"].lower(), (
        f"Expected name to contain 'smith', got: {result['name']!r}"
    )

    # at least one skill should be recognisable
    skills_lower = [s.lower() for s in result["skills"]]
    assert any(s in skills_lower for s in ["python", "fastapi", "docker"]), (
        f"Expected at least one known skill, got: {result['skills']}"
    )

    # total_experience_years should be a number (or None)
    tey = result["total_experience_years"]
    assert tey is None or isinstance(tey, (int, float)), (
        f"total_experience_years must be numeric, got: {type(tey)}"
    )

    print(f"\n[parse_resume] name={result['name']!r}, "
          f"skills={result['skills']}, "
          f"experience_years={result['total_experience_years']}")


@pytest.mark.asyncio
async def test_parse_resume_experience_entries_have_required_keys(resume_pdf):
    result = await parse_resume(resume_pdf)
    for i, exp in enumerate(result["experience"]):
        for key in ("title", "company", "duration", "description"):
            assert key in exp, (
                f"experience[{i}] missing key '{key}': {exp}"
            )


@pytest.mark.asyncio
async def test_score_fit_structure(resume_pdf, sample_job):
    parsed = await parse_resume(resume_pdf)
    await asyncio.sleep(8)  # respect Gemini free-tier RPM between the two calls
    result = await score_fit(sample_job, parsed)

    assert "score" in result
    assert "explanation" in result
    assert "strengths" in result
    assert "gaps" in result

    assert isinstance(result["score"], int), f"score must be int, got {type(result['score'])}"
    assert 0 <= result["score"] <= 100, f"score out of range: {result['score']}"
    assert isinstance(result["strengths"], list)
    assert isinstance(result["gaps"], list)
    assert isinstance(result["explanation"], str) and result["explanation"].strip()

    print(f"\n[score_fit] score={result['score']}, "
          f"strengths={result['strengths']}, gaps={result['gaps']}")


@pytest.mark.asyncio
async def test_score_fit_strong_match_scores_high(sample_job):
    """A candidate whose skills exactly match the JD should score >= 60."""
    perfect_resume = {
        "name": "Alice Dev",
        "email": "alice@example.com",
        "phone": "+1-555-9999",
        "current_title": "Senior Backend Engineer",
        "current_company": "TechCo",
        "summary": "Senior Python engineer with 7 years on FastAPI and PostgreSQL.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        "experience": [
            {
                "title": "Senior Backend Engineer",
                "company": "TechCo",
                "duration": "2019-Present",
                "description": "Led FastAPI service development for SaaS platform.",
            }
        ],
        "education": [
            {"degree": "B.Sc. Computer Science", "institution": "MIT", "year": "2017"}
        ],
        "total_experience_years": 7.0,
    }
    result = await score_fit(sample_job, perfect_resume)
    assert result["score"] >= 60, (
        f"Expected a strong match to score >= 60, got {result['score']}. "
        f"Explanation: {result['explanation']}"
    )


@pytest.mark.asyncio
async def test_score_fit_weak_match_scores_low(sample_job):
    """A completely unrelated candidate should score <= 40."""
    weak_resume = {
        "name": "Bob Chef",
        "email": "bob@example.com",
        "phone": None,
        "current_title": "Head Chef",
        "current_company": "La Maison",
        "summary": "Award-winning chef with 10 years in fine dining.",
        "skills": ["Culinary arts", "Menu design", "Kitchen management"],
        "experience": [
            {
                "title": "Head Chef",
                "company": "La Maison",
                "duration": "2015-Present",
                "description": "Oversaw a 30-seat fine dining kitchen.",
            }
        ],
        "education": [
            {"degree": "Culinary Diploma", "institution": "Culinary Institute", "year": "2014"}
        ],
        "total_experience_years": 10.0,
    }
    result = await score_fit(sample_job, weak_resume)
    assert result["score"] <= 40, (
        f"Expected a weak match to score <= 40, got {result['score']}. "
        f"Explanation: {result['explanation']}"
    )

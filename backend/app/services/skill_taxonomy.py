"""
Skill normalization: alias map → canonical name + implication expansion.

Lookup order:
  1. Exact alias match (case-insensitive key)
  2. Exact match against a canonical name (case-insensitive)
  3. rapidfuzz WRatio >= FUZZY_THRESHOLD — catches minor typos
  4. Return original string unchanged

Data lives in skill_taxonomy.json in the same directory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from rapidfuzz import fuzz, process

FUZZY_THRESHOLD = 90  # high threshold — avoids false positives like "Java" → "JavaScript"

_DATA_PATH = Path(__file__).with_suffix(".json")

def _load() -> tuple[List[str], Dict[str, str], Dict[str, List[str]]]:
    with _DATA_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return (
        data["canonical_skills"],
        data["alias_map"],
        {k: v for k, v in data["implications"].items()},
    )

CANONICAL_SKILLS, _ALIAS_MAP, _IMPLICATIONS = _load()

_CANONICAL_LOWER: Dict[str, str] = {c.lower(): c for c in CANONICAL_SKILLS}


def _normalize_one(raw: str) -> str:
    """Map a single raw skill string to its canonical name."""
    key = raw.strip().lower()
    if not key:
        return raw

    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]

    if key in _CANONICAL_LOWER:
        return _CANONICAL_LOWER[key]

    match = process.extractOne(
        raw,
        CANONICAL_SKILLS,
        scorer=fuzz.WRatio,
        score_cutoff=FUZZY_THRESHOLD,
    )
    if match:
        return match[0]

    return raw.strip()


def normalize_skills(raw_skills: List[str]) -> List[str]:
    """
    Normalize a list of raw skill strings:
    1. Map each to its canonical name
    2. Expand implications (e.g. Node.js adds JavaScript)
    3. Deduplicate preserving order
    """
    seen: set[str] = set()
    result: List[str] = []

    def _add(skill: str) -> None:
        if skill not in seen:
            seen.add(skill)
            result.append(skill)

    normalized = [_normalize_one(s) for s in raw_skills if s and s.strip()]
    for skill in normalized:
        _add(skill)

    for skill in list(result):
        for implied in _IMPLICATIONS.get(skill, []):
            _add(implied)

    return result


def normalize_skill_query(query: str) -> Optional[str]:
    """
    Normalize a single user-supplied search term.
    Returns the canonical name if a match is found, otherwise the original stripped string.
    Returns None for empty input.
    """
    if not query or not query.strip():
        return None
    return _normalize_one(query.strip())

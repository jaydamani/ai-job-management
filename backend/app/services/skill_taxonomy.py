"""
Skill normalization: alias map → canonical name + implication expansion.

Lookup order:
  1. Exact alias match (case-insensitive key)
  2. Exact match against a canonical name (case-insensitive)
  3. rapidfuzz WRatio >= FUZZY_THRESHOLD — catches minor typos
  4. Return original string unchanged
"""
from __future__ import annotations

from typing import Dict, List, Optional

from rapidfuzz import fuzz, process

FUZZY_THRESHOLD = 90  # high threshold — avoids false positives like "Java" → "JavaScript"

# ---------------------------------------------------------------------------
# Canonical name list — single source of truth for casing
# ---------------------------------------------------------------------------
CANONICAL_SKILLS: List[str] = [
    # Languages
    "JavaScript", "TypeScript", "Java", "Python", "C++", "C#", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "Dart", "R", "MATLAB",
    "Bash", "Shell", "Lua", "Elixir", "Haskell", "Clojure", "Groovy",
    # Web / frontend
    "React", "Vue.js", "Angular", "Svelte", "Next.js", "Nuxt.js", "Remix",
    "HTML", "CSS", "Sass", "Tailwind CSS", "Bootstrap", "jQuery",
    "Redux", "Zustand", "Webpack", "Vite",
    # Backend / server-side
    "Node.js", "Express.js", "FastAPI", "Django", "Flask", "Spring Boot",
    "Rails", "Laravel", "ASP.NET", "NestJS", "Gin", "Echo", "Fiber",
    "GraphQL", "REST API", "gRPC",
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Elasticsearch",
    "Cassandra", "DynamoDB", "Firestore", "Supabase", "Prisma", "SQLAlchemy",
    # Cloud / DevOps
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible",
    "CI/CD", "GitHub Actions", "Jenkins", "Linux",
    # ML / data
    "NumPy", "Pandas", "scikit-learn", "PyTorch", "TensorFlow", "Keras",
    "Hugging Face", "LangChain", "OpenCV", "Matplotlib", "Seaborn",
    # Misc
    "Git", "GraphQL", "WebSockets", "OAuth", "JWT",
]

# ---------------------------------------------------------------------------
# Alias map: lowercase alias → canonical name
# Aliases listed here take priority over fuzzy matching.
# ---------------------------------------------------------------------------
_ALIAS_MAP: Dict[str, str] = {
    # JavaScript — explicit so "java" never reaches fuzzy and hits this
    "javascript":   "JavaScript",
    "js":           "JavaScript",
    "ecmascript":   "JavaScript",
    "es6":          "JavaScript",
    "es2015":       "JavaScript",
    "es2017":       "JavaScript",
    "es2020":       "JavaScript",
    # TypeScript
    "typescript":   "TypeScript",
    "ts":           "TypeScript",
    # Java — explicit exact match keeps it from fuzzy-matching "JavaScript"
    "java":         "Java",
    # Python
    "python":       "Python",
    "python3":      "Python",
    "python 3":     "Python",
    "py":           "Python",
    # C++ / C#
    "c++":          "C++",
    "cpp":          "C++",
    "c#":           "C#",
    "csharp":       "C#",
    "dotnet":       "C#",
    ".net":         "C#",
    # Go
    "go":           "Go",
    "golang":       "Go",
    # Rust
    "rust":         "Rust",
    "rust-lang":    "Rust",
    # Ruby
    "ruby":         "Ruby",
    # PHP
    "php":          "PHP",
    # Swift / Kotlin
    "swift":        "Swift",
    "kotlin":       "Kotlin",
    # Node.js
    "node":         "Node.js",
    "nodejs":       "Node.js",
    "node.js":      "Node.js",
    "node js":      "Node.js",
    # React
    "react":        "React",
    "reactjs":      "React",
    "react.js":     "React",
    # Vue
    "vue":          "Vue.js",
    "vuejs":        "Vue.js",
    "vue.js":       "Vue.js",
    "vue js":       "Vue.js",
    # Angular
    "angular":      "Angular",
    "angularjs":    "Angular",
    # Next.js
    "next":         "Next.js",
    "nextjs":       "Next.js",
    "next.js":      "Next.js",
    # Nuxt.js
    "nuxt":         "Nuxt.js",
    "nuxtjs":       "Nuxt.js",
    # Express
    "express":      "Express.js",
    "expressjs":    "Express.js",
    # NestJS
    "nestjs":       "NestJS",
    "nest":         "NestJS",
    # Spring Boot
    "spring":       "Spring Boot",
    "spring boot":  "Spring Boot",
    "springboot":   "Spring Boot",
    # Django / Flask / FastAPI
    "django":       "Django",
    "flask":        "Flask",
    "fastapi":      "FastAPI",
    # Rails
    "rails":        "Rails",
    "ror":          "Rails",
    "ruby on rails": "Rails",
    # Laravel
    "laravel":      "Laravel",
    # PostgreSQL
    "postgres":     "PostgreSQL",
    "postgresql":   "PostgreSQL",
    "pg":           "PostgreSQL",
    "psql":         "PostgreSQL",
    # MySQL
    "mysql":        "MySQL",
    # MongoDB
    "mongo":        "MongoDB",
    "mongodb":      "MongoDB",
    # Redis
    "redis":        "Redis",
    # Elasticsearch
    "elasticsearch": "Elasticsearch",
    "elastic search": "Elasticsearch",
    # AWS / GCP / Azure
    "aws":          "AWS",
    "amazon web services": "AWS",
    "gcp":          "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "azure":        "Azure",
    "microsoft azure": "Azure",
    # Docker / Kubernetes
    "docker":       "Docker",
    "kubernetes":   "Kubernetes",
    "k8s":          "Kubernetes",
    # CI/CD
    "ci/cd":        "CI/CD",
    "cicd":         "CI/CD",
    "ci cd":        "CI/CD",
    # Terraform / Ansible
    "terraform":    "Terraform",
    "ansible":      "Ansible",
    # ML / data
    "numpy":        "NumPy",
    "pandas":       "Pandas",
    "sklearn":      "scikit-learn",
    "scikit learn": "scikit-learn",
    "scikit-learn": "scikit-learn",
    "pytorch":      "PyTorch",
    "torch":        "PyTorch",
    "tensorflow":   "TensorFlow",
    "tensor flow":  "TensorFlow",
    "keras":        "Keras",
    "huggingface":  "Hugging Face",
    "hugging face": "Hugging Face",
    "langchain":    "LangChain",
    # Misc
    "graphql":      "GraphQL",
    "graph ql":     "GraphQL",
    "rest":         "REST API",
    "rest api":     "REST API",
    "restful":      "REST API",
    "restful api":  "REST API",
    "git":          "Git",
    "jwt":          "JWT",
    "tailwind":     "Tailwind CSS",
    "tailwindcss":  "Tailwind CSS",
    "sass":         "Sass",
    "scss":         "Sass",
    "jquery":       "jQuery",
    "redux":        "Redux",
    "webpack":      "Webpack",
    "vite":         "Vite",
    "svelte":       "Svelte",
    "html":         "HTML",
    "css":          "CSS",
    "bootstrap":    "Bootstrap",
    "linux":        "Linux",
    "bash":         "Bash",
    "shell":        "Shell",
    "grpc":         "gRPC",
    "websockets":   "WebSockets",
    "websocket":    "WebSockets",
    "oauth":        "OAuth",
    "sqlalchemy":   "SQLAlchemy",
    "prisma":       "Prisma",
    "supabase":     "Supabase",
    "dynamodb":     "DynamoDB",
    "firestore":    "Firestore",
    "cassandra":    "Cassandra",
    "sqlite":       "SQLite",
    "sqlite3":      "SQLite",
    "github actions": "GitHub Actions",
    "jenkins":      "Jenkins",
    "nestjs":       "NestJS",
    "remix":        "Remix",
    "asp.net":      "ASP.NET",
    "aspnet":       "ASP.NET",
    "gin":          "Gin",
    "zustand":      "Zustand",
    "matplotlib":   "Matplotlib",
    "seaborn":      "Seaborn",
    "opencv":       "OpenCV",
    "open cv":      "OpenCV",
}

# Pre-build canonical lowercase lookup for step 2
_CANONICAL_LOWER: Dict[str, str] = {c.lower(): c for c in CANONICAL_SKILLS}

# ---------------------------------------------------------------------------
# Implication map: canonical skill → skills that should also be present
# One-directional: Node.js implies JavaScript, not vice-versa.
# ---------------------------------------------------------------------------
_IMPLICATIONS: Dict[str, List[str]] = {
    "Node.js":      ["JavaScript"],
    "React":        ["JavaScript"],
    "Vue.js":       ["JavaScript"],
    "Angular":      ["JavaScript"],
    "Svelte":       ["JavaScript"],
    "Next.js":      ["JavaScript", "React"],
    "Nuxt.js":      ["JavaScript", "Vue.js"],
    "Express.js":   ["JavaScript", "Node.js"],
    "NestJS":       ["JavaScript", "Node.js"],
    "Remix":        ["JavaScript", "React"],
    "TypeScript":   ["JavaScript"],
    "jQuery":       ["JavaScript"],
    "Redux":        ["JavaScript"],
    "Spring Boot":  ["Java"],
    "Django":       ["Python"],
    "Flask":        ["Python"],
    "FastAPI":      ["Python"],
    "NumPy":        ["Python"],
    "Pandas":       ["Python"],
    "scikit-learn": ["Python"],
    "PyTorch":      ["Python"],
    "TensorFlow":   ["Python"],
    "Keras":        ["Python"],
    "LangChain":    ["Python"],
    "Matplotlib":   ["Python"],
    "Seaborn":      ["Python"],
    "Rails":        ["Ruby"],
    "Laravel":      ["PHP"],
    "Prisma":       ["Node.js", "JavaScript"],
}


# ---------------------------------------------------------------------------
# Core normalization functions
# ---------------------------------------------------------------------------

def _normalize_one(raw: str) -> str:
    """Map a single raw skill string to its canonical name."""
    key = raw.strip().lower()
    if not key:
        return raw

    # 1. Explicit alias map
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]

    # 2. Case-insensitive exact match against canonical list
    if key in _CANONICAL_LOWER:
        return _CANONICAL_LOWER[key]

    # 3. Fuzzy match — WRatio, high threshold, avoids partial-substring false positives
    match = process.extractOne(
        raw,
        CANONICAL_SKILLS,
        scorer=fuzz.WRatio,
        score_cutoff=FUZZY_THRESHOLD,
    )
    if match:
        return match[0]

    # 4. No match — return original with leading/trailing whitespace stripped
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

    # Expand implications over the snapshot of directly-extracted skills
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

"""
backend/technology_detector.py
==============================
Evidence-based technology and framework detector.

Rules:
1. Detect technologies strictly from actual repository evidence.
2. Inspects manifests: package.json, requirements.txt, pyproject.toml, Cargo.toml, go.mod, etc.
3. Checks source code imports and configuration files.
4. DO NOT hallucinate technologies.
5. If evidence is lacking, reports: "Not clearly established from the available repository files."
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.models import FileRecord

KNOWN_FRAMEWORKS: dict[str, str] = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "streamlit": "Streamlit",
    "tornado": "Tornado",
    "pyramid": "Pyramid",
    "react": "React",
    "next": "Next.js",
    "vue": "Vue.js",
    "nuxt": "Nuxt.js",
    "angular": "Angular",
    "svelte": "Svelte",
    "express": "Express.js",
    "nest": "NestJS",
    "electron": "Electron",
    "spring": "Spring Boot",
    "torch": "PyTorch",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "sklearn": "scikit-learn",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "matplotlib": "Matplotlib",
    "seaborn": "Seaborn",
    "scipy": "SciPy",
    "sqlalchemy": "SQLAlchemy",
    "prisma": "Prisma ORM",
    "hibernate": "Hibernate",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "tailwind": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "graphql": "GraphQL",
    "apollo": "Apollo GraphQL",
    "redis": "Redis",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "pydantic": "Pydantic",
    "celery": "Celery",
}


class TechnologyDetector:
    """Extracts technologies and libraries supported by repository evidence."""

    def detect(self, root: Path, records: list[FileRecord]) -> list[str]:
        """Detect frameworks, libraries, and languages from evidence."""
        detected: set[str] = set()

        # 1. Add detected programming languages
        for r in records:
            if r.language and r.category == "SOURCE":
                detected.add(r.language)

        # 2. Inspect package manifests
        for r in records:
            if r.sensitive or not r.readable:
                continue

            file_path = root / r.path
            filename = file_path.name.lower()

            # Python requirements.txt
            if "requirements" in filename and filename.endswith(".txt"):
                self._parse_requirements_txt(file_path, detected)

            # Node package.json
            elif filename == "package.json":
                self._parse_package_json(file_path, detected)

            # Python pyproject.toml
            elif filename == "pyproject.toml":
                self._parse_pyproject_toml(file_path, detected)

            # Rust Cargo.toml
            elif filename == "cargo.toml":
                self._parse_cargo_toml(file_path, detected)

            # Go go.mod
            elif filename == "go.mod":
                self._parse_go_mod(file_path, detected)

            # Docker
            elif filename == "dockerfile" or filename.startswith("docker-compose"):
                detected.add("Docker")

        # 3. Inspect source code imports for prominent frameworks
        self._scan_source_imports(root, records, detected)

        return sorted(detected)

    @staticmethod
    def _parse_requirements_txt(path: Path, detected: set[str]) -> None:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Split at version specifiers
                pkg = re.split(r"[=><~!;@]", line)[0].strip().lower()
                if pkg in KNOWN_FRAMEWORKS:
                    detected.add(KNOWN_FRAMEWORKS[pkg])
                elif pkg and len(pkg) > 1:
                    detected.add(pkg)
        except OSError:
            pass

    @staticmethod
    def _parse_package_json(path: Path, detected: set[str]) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for dep in deps:
                dep_lower = dep.lower()
                matched = False
                for token, label in KNOWN_FRAMEWORKS.items():
                    if token in dep_lower:
                        detected.add(label)
                        matched = True
                if not matched and not dep.startswith("@types/"):
                    detected.add(dep)
        except (OSError, json.JSONDecodeError):
            pass

    @staticmethod
    def _parse_pyproject_toml(path: Path, detected: set[str]) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token, label in KNOWN_FRAMEWORKS.items():
                if re.search(rf"\b{re.escape(token)}\b", text):
                    detected.add(label)
        except OSError:
            pass

    @staticmethod
    def _parse_cargo_toml(path: Path, detected: set[str]) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            detected.add("Rust / Cargo")
            for token in ["actix", "axum", "tokio", "serde", "diesel"]:
                if token in text:
                    detected.add(token.capitalize())
        except OSError:
            pass

    @staticmethod
    def _parse_go_mod(path: Path, detected: set[str]) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            detected.add("Go Modules")
            for token in ["gin-gonic", "fiber", "echo", "gorm"]:
                if token in text:
                    detected.add(token)
        except OSError:
            pass

    @staticmethod
    def _scan_source_imports(root: Path, records: list[FileRecord], detected: set[str]) -> None:
        # Sample source files up to 25 files to find imports
        source_candidates = [r for r in records if r.category == "SOURCE" and r.readable and not r.sensitive][:25]
        combined = []
        for r in source_candidates:
            try:
                snippet = (root / r.path).read_text(encoding="utf-8", errors="ignore")[:10_000]
                combined.append(snippet)
            except OSError:
                pass

        corpus = "\n".join(combined).lower()
        for token, label in KNOWN_FRAMEWORKS.items():
            if re.search(rf"\b(import|from|require|use|include)\s+.*?\b{re.escape(token)}\b", corpus):
                detected.add(label)

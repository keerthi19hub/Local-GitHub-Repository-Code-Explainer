"""
backend/file_inspector.py
=========================
Performs a complete inventory scan of the cloned repository and classifies
every file into a structured category.

Safety & completeness rules:
1. Complete scanning: builds a full catalog of all files in the repository.
2. Supports README-only, docs-only, notebook-only, config-only, and mixed repos.
3. Classifies files into 12 distinct categories.
4. Strictly identifies sensitive files (.env, credentials, secrets, tokens, keys)
   so their contents can be excluded from LLM prompts and hidden from UI.
5. Excludes common development caches (.git, node_modules, venv, __pycache__) to avoid noise.
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.models import FileRecord
from backend.utils import normalize_rel_path

# Mapping of file extensions to programming languages
LANGUAGE_BY_EXT: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".swift": "Swift",
    ".dart": "Dart",
    ".r": "R",
    ".R": "R",
    ".sql": "SQL",
    ".sh": "Shell Script",
    ".bash": "Shell Script",
    ".zsh": "Shell Script",
    ".ps1": "PowerShell",
    ".bat": "Batch",
    ".cmd": "Batch",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".lua": "Lua",
    ".scala": "Scala",
    ".pl": "Perl",
    ".m": "Objective-C / MATLAB",
}

SOURCE_EXTS = set(LANGUAGE_BY_EXT.keys())
CONFIG_EXTS = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf", ".xml", ".properties", ".editorconfig"}
DATA_EXTS = {".csv", ".tsv", ".jsonl", ".ndjson", ".parquet", ".db", ".sqlite", ".sqlite3"}
DOC_EXTS = {".md", ".markdown", ".rst", ".txt", ".adoc", ".textile"}

DEPENDENCY_NAMES = {
    "requirements.txt", "requirements-dev.txt", "requirements_dev.txt",
    "pyproject.toml", "setup.py", "setup.cfg", "pipfile", "pipfile.lock",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties",
    "cargo.toml", "cargo.lock", "go.mod", "go.sum",
    "composer.json", "composer.lock", "gemfile", "gemfile.lock",
    "pubspec.yaml", "packages.config",
}

BUILD_DEPLOY_NAMES = {
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "makefile", "justfile", "procfile", "vagrantfile",
}

TEST_PATTERNS = {"test", "tests", "spec", "specs", "__tests__"}

# Sensitive filenames that should NEVER have contents inspected or sent to an LLM
SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", ".env.staging", ".env.test",
    "credentials", "credentials.json", "secrets.json", "secret.json", "secrets.yaml", "secrets.yml",
    "id_rsa", "id_ed25519", "id_ecdsa", "private.key", "private.pem", "service_account.json",
}

# Directories to ignore during scanning
IGNORE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "node_modules", "dist", "build", "target", ".idea",
    ".vscode", ".next", ".nuxt", "coverage", ".tox", ".cache",
}

# Common binary file extensions
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".wav", ".ogg", ".mp4", ".mov", ".avi", ".mkv",
    ".class", ".jar", ".war", ".ear", ".pyc", ".pyo", ".pyd",
    ".pkl", ".pickle", ".npy", ".npz",
}


class FileInspector:
    """Inventories and classifies all files in a repository directory."""

    def scan_repository(self, root: Path) -> list[FileRecord]:
        """Perform a complete repository inventory scan."""
        records: list[FileRecord] = []

        for path in root.rglob("*"):
            try:
                if not path.is_file() or path.is_symlink():
                    continue

                rel = path.relative_to(root)
                if any(part in IGNORE_DIRS for part in rel.parts):
                    continue

                stat = path.stat()
                category, language, readable, sensitive = self.classify_file(path, rel, stat.st_size)

                record = FileRecord(
                    path=normalize_rel_path(path, root),
                    category=category,
                    extension=path.suffix.lower(),
                    size_bytes=stat.st_size,
                    language=language,
                    sensitive=sensitive,
                    readable=readable,
                )
                records.append(record)
            except OSError:
                continue

        return sorted(records, key=lambda r: r.path.lower())

    def classify_file(self, path: Path, rel: Path, size: int) -> tuple[str, str | None, bool, bool]:
        """
        Classifies a file into one of 12 categories:
        1. SENSITIVE
        2. BINARY/ASSET
        3. DEPENDENCIES
        4. BUILD/DEPLOYMENT
        5. TESTS
        6. NOTEBOOK
        7. DOCUMENTATION
        8. WEB
        9. DATA/SCHEMA
        10. CONFIGURATION
        11. SOURCE
        12. UNKNOWN READABLE TEXT
        Returns: (category, language, readable, sensitive)
        """
        name = path.name.lower()
        suffix = path.suffix.lower()

        # 1. Sensitive files (highest priority check)
        if self.is_sensitive(path, rel):
            return "SENSITIVE", None, False, True

        # 2. Binary / Assets
        if suffix in BINARY_EXTS:
            return "BINARY/ASSET", None, False, False

        # 3. Dependency manifests
        if name in DEPENDENCY_NAMES:
            return "DEPENDENCIES", LANGUAGE_BY_EXT.get(suffix), True, False

        # 4. Build & Deployment
        if name in BUILD_DEPLOY_NAMES or name.startswith(".github") or "/.github/" in normalize_rel_path(path, path.parent.parent).lower():
            return "BUILD/DEPLOYMENT", None, True, False

        # 5. Tests
        if any(part.lower() in TEST_PATTERNS for part in rel.parts) or re.search(r"(^|[_-])(test|spec)([_-]|$)", name):
            return "TESTS", LANGUAGE_BY_EXT.get(suffix), True, False

        # 6. Notebooks
        if suffix == ".ipynb":
            return "NOTEBOOK", "Jupyter Notebook", True, False

        # 7. Documentation
        if suffix in DOC_EXTS or name.startswith("readme") or name.startswith("changelog") or name.startswith("license"):
            return "DOCUMENTATION", None, True, False

        # 8. Web files
        if suffix in {".html", ".htm", ".css", ".scss", ".sass", ".vue", ".svelte"}:
            return "WEB", LANGUAGE_BY_EXT.get(suffix), True, False

        # 9. Data & Schema
        if suffix in DATA_EXTS:
            return "DATA/SCHEMA", None, True, False

        # 10. Configuration
        if suffix in CONFIG_EXTS or name in {".gitignore", ".gitattributes", ".dockerignore"}:
            return "CONFIGURATION", None, True, False

        # 11. Source code
        if suffix in SOURCE_EXTS:
            return "SOURCE", LANGUAGE_BY_EXT.get(suffix), True, False

        # 12. Fallback text check
        readable = self.is_readable_text(path, size)
        return ("UNKNOWN READABLE TEXT" if readable else "BINARY/ASSET", None, readable, False)

    @staticmethod
    def is_sensitive(path: Path, rel: Path) -> bool:
        """Determines if a file is a sensitive credential or secret file."""
        name = path.name.lower()
        if name in SENSITIVE_NAMES:
            return True
        if name.startswith(".env.") and name not in {".env.example", ".env.sample", ".env.template"}:
            return True

        rel_str = str(rel).lower().replace("\\", "/")
        sensitive_tokens = ("secret", "credential", "private_key", "access_token", "api_key", "id_rsa", "id_ed25519")
        return any(tok in name for tok in sensitive_tokens) or ".ssh/" in rel_str

    @staticmethod
    def is_readable_text(path: Path, size: int) -> bool:
        """Check whether a file contains readable text without null bytes."""
        if size > 2_000_000:
            return False
        try:
            chunk = path.read_bytes()[:4096]
            if b"\x00" in chunk:
                return False
            chunk.decode("utf-8")
            return True
        except (OSError, UnicodeDecodeError):
            return False

    @staticmethod
    def calculate_counts(records: list[FileRecord]) -> dict[str, int]:
        """Aggregate total count per category."""
        return {
            category: sum(1 for r in records if r.category == category)
            for category in sorted({r.category for r in records})
        }

    @staticmethod
    def calculate_languages(records: list[FileRecord]) -> dict[str, int]:
        """Aggregate programming language occurrences."""
        languages: dict[str, int] = {}
        for r in records:
            if r.language:
                languages[r.language] = languages.get(r.language, 0) + 1
        return dict(sorted(languages.items(), key=lambda x: (-x[1], x[0])))

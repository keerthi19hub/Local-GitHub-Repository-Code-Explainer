"""
backend/context_builder.py
==========================
Ranks repository files dynamically and builds a grounded, low-latency prompt
for Qwen 2.5 3B through Ollama.

Low Latency Optimizations:
1. MAX_TOTAL_CONTEXT: 35,000 characters (~7,000 tokens)
2. MAX_FILES_FOR_LLM: 25 prioritized files
3. MAX_FILE_SIZE: 20,000 characters per file with smart excerpting
4. Single AI Request: ONE well-structured prompt generates the complete explanation.
5. Strict 23-section prompt structure based exclusively on repository evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.code_extractor import CodeExtractor
from backend.models import FileRecord

MAX_TOTAL_CONTEXT = 35_000   # Total characters in context window
MAX_FILES_FOR_LLM = 25       # Max prioritized files
MAX_FILE_SIZE = 20_000       # Max characters extracted per file


class ContextBuilder:
    """Selects high-priority files and constructs the grounded Qwen prompt."""

    def __init__(
        self,
        max_total_context: int = MAX_TOTAL_CONTEXT,
        max_files_for_llm: int = MAX_FILES_FOR_LLM,
        max_file_size: int = MAX_FILE_SIZE,
    ):
        self.max_total_context = max_total_context
        self.max_files_for_llm = max_files_for_llm
        self.max_file_size = max_file_size
        self.extractor = CodeExtractor()

    def rank_files(self, records: list[FileRecord]) -> list[FileRecord]:
        """
        Dynamically rank files by informational value.
        Higher priority for README, manifests, configs, and entry points.
        Excludes sensitive files and binary assets.
        """
        candidates = [
            r for r in records
            if r.readable and not r.sensitive and r.category not in {"BINARY/ASSET", "SENSITIVE"}
        ]

        def compute_score(r: FileRecord) -> tuple[int, int, int, str]:
            name = Path(r.path).name.lower()
            base = 0

            # 1. README & primary documentation
            if name in {"readme.md", "readme", "readme.txt", "readme.rst"}:
                base += 1000
            elif "readme" in name:
                base += 900

            # 2. Package and dependency manifests
            elif r.category == "DEPENDENCIES":
                base += 800

            # 3. Application entry points
            elif name in {"main.py", "app.py", "index.js", "main.js", "server.py", "manage.py", "main.go", "main.rs", "app.ts", "index.ts"}:
                base += 750

            # 4. Deployment and Docker files
            elif r.category == "BUILD/DEPLOYMENT":
                base += 600

            # 5. Configuration files
            elif r.category == "CONFIGURATION":
                base += 500

            # 6. Source code
            elif r.category == "SOURCE":
                base += 400

            # 7. Tests
            elif r.category == "TESTS":
                base += 250

            # 8. Notebooks
            elif r.category == "NOTEBOOK":
                base += 220

            # 9. Other documentation
            elif r.category == "DOCUMENTATION":
                base += 200

            # 10. Data & schema
            elif r.category == "DATA/SCHEMA":
                base += 150

            depth_penalty = len(Path(r.path).parts)
            size_penalty = min(r.size_bytes // 5000, 20)

            # Return negative base for ascending sort order
            return (-base, depth_penalty, size_penalty, r.path.lower())

        ranked = sorted(candidates, key=compute_score)

        # Ensure no duplicates and slice to max count
        seen_paths: set[str] = set()
        deduped: list[FileRecord] = []
        for r in ranked:
            if r.path not in seen_paths:
                seen_paths.add(r.path)
                deduped.append(r)
            if len(deduped) >= self.max_files_for_llm:
                break

        return deduped

    def build_context(self, root: Path, selected: list[FileRecord]) -> str:
        """Extract text chunks from selected files within the total context budget."""
        chunks: list[str] = []
        remaining = self.max_total_context

        for record in selected:
            if remaining <= 0:
                break

            content = self.extractor.extract_content(root, record, self.max_file_size)
            if not content.strip():
                continue

            header = f"\n===== [{record.category}] {record.path} =====\n"
            budget = min(self.max_file_size, remaining - len(header))
            if budget <= 0:
                break

            if len(content) > budget:
                content = content[:budget] + "\n[TRUNCATED FOR CONTEXT]"

            chunk = header + content + "\n"
            chunks.append(chunk)
            remaining -= len(chunk)

        return "".join(chunks)

    def build_prompt(
        self,
        repo_name: str,
        repo_owner: str,
        repo_type: str,
        technologies: list[str],
        file_inventory: list[FileRecord],
        folder_tree: list[str],
        code_context: str,
    ) -> str:
        """
        Construct the grounded, evidence-based prompt for Qwen 2.5 3B.
        Covers the exact 23 required sections in simple beginner-friendly language.
        """
        tech_str = ", ".join(technologies) if technologies else "Not clearly established from the available repository files."
        tree_str = "\n".join(folder_tree[:50])

        compact_inventory = "\n".join(
            f"- {item.path} ({item.category}, {item.size_bytes} bytes)"
            for item in file_inventory[:40]
            if not item.sensitive
        )

        return f"""You are explaining a real GitHub repository to a beginner.

Use ONLY the supplied repository evidence below.
Do not invent files, technologies, frameworks, databases, APIs, functions, classes, features, architecture, workflows, or commands.
Only include claims supported by the supplied repository evidence.
When evidence is insufficient, explicitly say:
"This could not be determined from the available repository content."

Explain the repository in detailed but simple language.

=== REPOSITORY OVERVIEW ===
Repository Name: {repo_name}
Repository Owner: {repo_owner}
Project Classification: {repo_type}
Detected Technologies: {tech_str}

=== FOLDER STRUCTURE (SAMPLE) ===
{tree_str}

=== FILE INVENTORY (SAMPLE) ===
{compact_inventory}

=== EXTRACTED SOURCE CODE & DOCUMENTATION ===
{code_context}

=== REQUIRED DETAILED EXPLANATION ===
Provide a comprehensive explanation covering these exact sections:
1. Project Overview (What is this project and why does it exist?)
2. What the Project Does (Problem it solves and practical purpose)
3. Main Features (Core capabilities backed by code evidence)
4. Repository Structure (How directories and files are organized)
5. Important Files (File-by-file breakdown of key files, their purpose and code)
6. Main Technologies (Languages, frameworks, and tools used)
7. Application Architecture (High-level architecture and how components relate)
8. How the Project Works (Internal mechanics in simple terms)
9. Step-by-Step Workflow (How the application runs from start to finish)
10. Data Flow (How information travels through the project)
11. Important Classes (Key classes identified in the code and what they do)
12. Important Functions (Key functions and methods and their roles)
13. Important Modules (Key files/packages and their responsibilities)
14. Dependencies (Libraries required and where they are configured)
15. Configuration (Config files, environment variables, settings)
16. Database/Storage (Databases, schemas, files, or state persistence if present)
17. APIs/External Services (REST endpoints, external services, or webhooks if present)
18. Notebook Analysis (Jupyter notebook contents and steps if present)
19. Testing (Test setup, test files, and test strategies if present)
20. Running/Deployment (How to run or deploy it based on README/Docker)
21. End-to-End Workflow (Complete journey of a user interaction or data job)
22. Key Takeaways (Summary of what a beginner should remember)
23. Limitations/Unknown Information (Things not established from available files)

Remember: Write in clear, beginner-friendly language while remaining technically precise.
"""

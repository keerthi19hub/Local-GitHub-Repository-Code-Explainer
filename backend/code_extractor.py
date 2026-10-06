"""
backend/code_extractor.py
=========================
Safely extracts code and documentation text from repository files for LLM context.

Rules & Protections:
1. Notebooks (.ipynb): parses JSON, extracts markdown and code cells, ignores large outputs.
   NEVER executes notebook kernels or code.
2. Large files: extracts imports, classes, functions, and key declarations.
   Marks [TRUNCATED FOR CONTEXT] explicitly.
3. Sensitive files: NEVER extracts contents. Returns empty or safe placeholder.
4. Binary files: NEVER extracts raw bytes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.models import FileRecord


class CodeExtractor:
    """Safely extracts readable text content from files with smart truncation."""

    def extract_content(self, root: Path, record: FileRecord, max_file_chars: int = 20_000) -> str:
        """
        Safely extract file content up to max_file_chars.
        Returns empty string for sensitive or binary files.
        """
        if record.sensitive or not record.readable or record.category in {"SENSITIVE", "BINARY/ASSET"}:
            return ""

        file_path = root / record.path
        if not file_path.is_file():
            return ""

        if record.category == "NOTEBOOK":
            return self.extract_notebook_content(file_path, max_file_chars)

        try:
            raw_text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

        if len(raw_text) <= max_file_chars:
            return raw_text

        return self.smart_truncate(raw_text, max_file_chars)

    @staticmethod
    def extract_notebook_content(path: Path, max_chars: int) -> str:
        """
        Parse .ipynb Jupyter notebook JSON and extract markdown and code cells.
        Output cells and media are ignored to prevent context bloat.
        NEVER executes code.
        """
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            cells = data.get("cells", [])
            extracted: list[str] = []
            total_chars = 0

            for idx, cell in enumerate(cells):
                cell_type = cell.get("cell_type")
                if cell_type not in {"markdown", "code"}:
                    continue

                source = "".join(cell.get("source", [])).strip()
                if not source:
                    continue

                block = f"[{cell_type.upper()} CELL {idx + 1}]\n{source}"
                if total_chars + len(block) > max_chars:
                    extracted.append(f"\n[NOTEBOOK CELLS TRUNCATED FOR CONTEXT (Total cells: {len(cells)})]")
                    break

                extracted.append(block)
                total_chars += len(block)

            return "\n\n".join(extracted)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return ""

    @staticmethod
    def smart_truncate(text: str, budget: int) -> str:
        """
        Intelligently excerpt large files by preserving:
        - Header & imports (top 50% of budget)
        - Important declarations (classes, functions, methods, endpoints)
        - Footer / main block (bottom 25% of budget)
        """
        if len(text) <= budget:
            return text

        head_size = int(budget * 0.50)
        tail_size = int(budget * 0.25)
        middle_budget = max(0, budget - head_size - tail_size)

        lines = text.splitlines()
        decl_regex = re.compile(
            r"^\s*(class\s+|def\s+|async\s+def\s+|function\s+|export\s+|pub\s+|fn\s+|func\s+|public\s+|private\s+|interface\s+|struct\s+|enum\s+|@)",
            re.IGNORECASE,
        )

        middle_lines = [line for line in lines if decl_regex.match(line)]
        middle_text = "\n".join(middle_lines)[:middle_budget]

        return (
            text[:head_size]
            + "\n\n[... KEY DECLARATIONS EXCERPT ...]\n"
            + middle_text
            + "\n\n[TRUNCATED FOR CONTEXT]\n\n"
            + text[-tail_size:]
        )

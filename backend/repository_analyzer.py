"""
backend/repository_analyzer.py
==============================
Main coordinator for the repository processing pipeline.

Pipeline stages:
1. URL Validation
2. Shallow Git Clone (depth=1)
3. Full Repository Inventory Scan
4. File Classification (12 categories)
5. Evidence-Based Technology Detection
6. Smart File Ranking & Context Building
7. Grounded Qwen Prompt Construction
8. Optional In-Process Ollama Inference

Instruments each stage with time.perf_counter() for latency measurement.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from backend.context_builder import ContextBuilder
from backend.file_inspector import FileInspector
from backend.github_processor import GitHubProcessor
from backend.llm_service import OllamaService
from backend.models import AnalyzeResponse, FileRecord, RepositoryProcessingError
from backend.technology_detector import TechnologyDetector

ProgressCallback = Callable[[str], None] | None


class RepositoryAnalyzer:
    """Orchestrates end-to-end repository inspection and prompt preparation."""

    def __init__(self):
        self.github_proc = GitHubProcessor()
        self.inspector = FileInspector()
        self.tech_detector = TechnologyDetector()
        self.context_builder = ContextBuilder()
        self.llm_service = OllamaService()

    def analyze(
        self,
        url: str,
        progress: ProgressCallback = None,
        generate_ai: bool = False,
    ) -> AnalyzeResponse:
        """
        Execute full repository analysis.
        If generate_ai is True, sends prompt to local Ollama.
        Otherwise prepares the prompt so the user's browser can call local Ollama directly.
        """
        timings: dict[str, float] = {}
        t_total_start = time.perf_counter()

        # 1. Validate GitHub URL
        if progress:
            progress("1. Validating GitHub URL")
        t0 = time.perf_counter()
        clone_url = self.github_proc.validate_url(url)
        timings["validation"] = time.perf_counter() - t0

        # 2. Shallow Clone
        if progress:
            progress("2. Cloning repository")
        temp_dir, repo_root, clone_time = self.github_proc.clone_repository(clone_url)
        timings["clone"] = clone_time

        try:
            # 3. Full Inventory Scan
            if progress:
                progress("3. Scanning repository")
            t0 = time.perf_counter()
            records: list[FileRecord] = self.inspector.scan_repository(repo_root)
            timings["scan"] = time.perf_counter() - t0

            # 4. Classify Files
            if progress:
                progress("4. Classifying files")
            t0 = time.perf_counter()
            meaningful = [r for r in records if r.category != "BINARY/ASSET" and not r.sensitive]
            if not meaningful:
                raise RepositoryProcessingError(
                    "This repository contains no inspectable files, documentation, or code."
                )
            timings["classification"] = time.perf_counter() - t0

            # 5. Detect Technologies from Evidence
            if progress:
                progress("5. Detecting technologies")
            t0 = time.perf_counter()
            technologies = self.tech_detector.detect(repo_root, records)
            timings["technology_detection"] = time.perf_counter() - t0

            # 6. Rank Files & Build Context
            if progress:
                progress("6. Building AI context")
            t0 = time.perf_counter()
            selected = self.context_builder.rank_files(records)
            code_context = self.context_builder.build_context(repo_root, selected)
            timings["context_preparation"] = time.perf_counter() - t0

            # Extract repository metadata
            repo_parts = clone_url.rstrip(".git").split("/")
            repo_owner = repo_parts[-2]
            repo_name = repo_parts[-1]
            repo_type = self._classify_repo_type(records, technologies)

            folder_tree = [r.path for r in records[:100]]

            # 7. Build Grounded Qwen Prompt
            prompt = self.context_builder.build_prompt(
                repo_name=repo_name,
                repo_owner=repo_owner,
                repo_type=repo_type,
                technologies=technologies,
                file_inventory=records,
                folder_tree=folder_tree,
                code_context=code_context,
            )

            explanation = None
            if generate_ai:
                if progress:
                    progress("7. Generating AI explanation via local Ollama")
                explanation, gen_time = self.llm_service.generate_explanation(prompt)
                timings["ollama_generation"] = gen_time

            timings["total_processing"] = time.perf_counter() - t_total_start

            return AnalyzeResponse(
                repository_name=repo_name,
                repository_owner=repo_owner,
                repository_url=url.strip(),
                repository_type=repo_type,
                file_inventory=records,
                file_counts=self.inspector.calculate_counts(records),
                language_counts=self.inspector.calculate_languages(records),
                technologies=technologies,
                folder_tree=folder_tree,
                important_files=[r.path for r in selected[:15]],
                selected_files=[r.path for r in selected],
                code_context=code_context,
                llm_prompt=prompt,
                timings=timings,
                explanation=explanation,
            )

        finally:
            self.github_proc.cleanup(temp_dir)

    @staticmethod
    def _classify_repo_type(records: list[FileRecord], technologies: list[str]) -> str:
        """Infer project classification without hallucination."""
        cats = {r.category for r in records}
        if "NOTEBOOK" in cats and "SOURCE" not in cats:
            return "Data Science / Jupyter Notebook Project"
        if "DOCUMENTATION" in cats and len(cats) == 1:
            return "Documentation-Only Project"
        if "DATA/SCHEMA" in cats and "SOURCE" not in cats:
            return "Data & Schema Repository"
        if "CONFIGURATION" in cats and "SOURCE" not in cats:
            return "Configuration / Project Metadata Repository"
        if "SOURCE" in cats or "WEB" in cats:
            if "FastAPI" in technologies or "Flask" in technologies or "Django" in technologies:
                return "Python Web Application / API"
            if "Streamlit" in technologies:
                return "Streamlit Web Application"
            if "React" in technologies or "Vue.js" in technologies:
                return "Frontend Web Application"
            return "Software / Source Code Project"
        return "General GitHub Repository"

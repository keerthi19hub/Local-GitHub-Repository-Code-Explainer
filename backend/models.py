"""
backend/models.py
=================
Pydantic data models and schemas for the Local GitHub Repository Code Explainer.
Validates inputs and formats API responses cleanly.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, HttpUrl


class RepositoryProcessingError(Exception):
    """User-friendly exception for repository processing errors."""
    pass


class FileRecord(BaseModel):
    """Represents a single cataloged file in the repository inventory."""
    path: str
    category: str
    extension: str
    size_bytes: int
    language: str | None = None
    sensitive: bool = False
    readable: bool = False


class AnalyzeRequest(BaseModel):
    """Request payload to analyze a public GitHub repository."""
    repository_url: HttpUrl = Field(
        ...,
        description="Public HTTPS GitHub repository URL (e.g., https://github.com/psf/requests)",
        examples=["https://github.com/psf/requests"],
    )


class AnalyzeResponse(BaseModel):
    """Complete structured response from the repository analyzer."""
    repository_name: str
    repository_owner: str
    repository_url: str
    repository_type: str
    file_inventory: list[FileRecord]
    file_counts: dict[str, int]
    language_counts: dict[str, int]
    technologies: list[str]
    folder_tree: list[str]
    important_files: list[str]
    selected_files: list[str]
    code_context: str
    llm_prompt: str
    timings: dict[str, float]
    explanation: str | None = None


class OllamaStatusResponse(BaseModel):
    """Ollama connectivity and Qwen model availability status."""
    connected: bool
    base_url: str
    model_available: bool
    model_name: str
    available_models: list[str] = Field(default_factory=list)
    error_message: str | None = None


class GenerateRequest(BaseModel):
    """Payload to trigger an LLM explanation generation request."""
    prompt: str
    model: str = "qwen2.5:3b"
    stream: bool = False

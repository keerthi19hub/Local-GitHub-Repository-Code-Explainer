"""
backend/main.py
===============
FastAPI server exposing RESTful API endpoints for the Local GitHub Repository Code Explainer.

Endpoints:
- GET /
- GET /api/health
- GET /api/ollama-status
- POST /api/analyze
- POST /api/generate
- GET /docs
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.llm_service import OllamaService
from backend.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    GenerateRequest,
    OllamaStatusResponse,
    RepositoryProcessingError,
)
from backend.repository_analyzer import RepositoryAnalyzer

app = FastAPI(
    title="Local GitHub Repository Code Explainer API",
    description="REST API for inspecting public GitHub repositories and orchestrating local Qwen 2.5 3B inference via Ollama.",
    version="1.0.0",
)

# Enable CORS for local testing and cross-origin browser connectors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = RepositoryAnalyzer()
ollama_service = OllamaService()


@app.get("/")
def read_root():
    """Root metadata endpoint."""
    return {
        "service": "Local GitHub Repository Code Explainer API",
        "status": "online",
        "docs_url": "/docs",
        "model": "qwen2.5:3b",
        "inference_engine": "Ollama",
    }


@app.get("/api/health")
def read_health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "local-github-repository-code-explainer",
        "version": "1.0.0",
    }


@app.get("/api/ollama-status", response_model=OllamaStatusResponse)
def read_ollama_status():
    """Check connectivity to local Ollama and verify qwen2.5:3b availability."""
    return ollama_service.check_status()


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_repo(request: AnalyzeRequest):
    """
    Analyzes a public GitHub repository and returns full file inventory,
    detected technologies, and the prepared Qwen prompt.
    """
    try:
        return analyzer.analyze(str(request.repository_url), generate_ai=False)
    except RepositoryProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}") from exc


@app.post("/api/generate")
def generate_ai_explanation(request: GenerateRequest):
    """
    Sends the prompt to local Ollama and returns the generated explanation.
    """
    try:
        service = OllamaService(model=request.model)
        explanation, elapsed = service.generate_explanation(request.prompt)
        return {
            "status": "success",
            "model": request.model,
            "generation_time_seconds": elapsed,
            "explanation": explanation,
        }
    except RepositoryProcessingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc

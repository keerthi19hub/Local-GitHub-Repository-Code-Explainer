"""
backend/llm_service.py
======================
Service for communicating with Ollama and Qwen 2.5 3B.

Features:
1. Targets the local Ollama instance (default: http://127.0.0.1:11434).
2. Uses qwen2.5:3b model.
3. Checks Ollama health and model availability before analysis.
4. Uses keep_alive ("10m") to keep the model loaded in RAM and eliminate reload latency.
5. Employs one main request to minimize round trips.
6. Target generation length: 600-900 tokens.
"""

from __future__ import annotations

import os
import time
from typing import Any, Generator

import requests

from backend.models import OllamaStatusResponse, RepositoryProcessingError

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


class OllamaService:
    """Interfaces with the local Ollama daemon and Qwen 2.5 3B model."""

    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def check_status(self) -> OllamaStatusResponse:
        """
        Verify that the local Ollama service is running and qwen2.5:3b is available.
        Performs a fast check using /api/tags.
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3.0)
            if resp.status_code != 200:
                return OllamaStatusResponse(
                    connected=False,
                    base_url=self.base_url,
                    model_available=False,
                    model_name=self.model,
                    error_message=f"Ollama returned HTTP {resp.status_code}",
                )

            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            # Match model name either exactly or with tag (e.g. qwen2.5:3b or qwen2.5:3b-instruct)
            model_found = any(self.model in m or m.startswith(self.model) for m in models)

            return OllamaStatusResponse(
                connected=True,
                base_url=self.base_url,
                model_available=model_found,
                model_name=self.model,
                available_models=models,
                error_message=None if model_found else f"Model '{self.model}' not found in local Ollama.",
            )
        except requests.exceptions.ConnectionError:
            return OllamaStatusResponse(
                connected=False,
                base_url=self.base_url,
                model_available=False,
                model_name=self.model,
                error_message="Could not connect to Ollama. Make sure Ollama is installed and running locally.",
            )
        except requests.exceptions.Timeout:
            return OllamaStatusResponse(
                connected=False,
                base_url=self.base_url,
                model_available=False,
                model_name=self.model,
                error_message="Connection to local Ollama timed out.",
            )
        except Exception as exc:
            return OllamaStatusResponse(
                connected=False,
                base_url=self.base_url,
                model_available=False,
                model_name=self.model,
                error_message=str(exc),
            )

    def generate_explanation(self, prompt: str, timeout: int = 120) -> tuple[str, float]:
        """
        Send the repository analysis prompt to local Ollama and return the explanation.
        Uses keep_alive="10m" to keep Qwen warm in memory.
        Target output: 600-900 tokens.
        Returns: (explanation_text, generation_time_seconds)
        """
        t0 = time.perf_counter()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "num_predict": 850,
                "temperature": 0.2,
                "top_p": 0.9,
                "repeat_penalty": 1.15,
            },
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            explanation = data.get("response", "").strip()

            if not explanation:
                raise RepositoryProcessingError("Ollama returned an empty response. Please try again.")

            elapsed = time.perf_counter() - t0
            return explanation, elapsed

        except requests.exceptions.ConnectionError as exc:
            raise RepositoryProcessingError(
                f"Cannot connect to local Ollama at {self.base_url}. "
                "Ensure Ollama is running (`ollama serve`)."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RepositoryProcessingError(
                "Ollama inference timed out. Your laptop may be under heavy load."
            ) from exc
        except Exception as exc:
            raise RepositoryProcessingError(f"Ollama generation failed: {exc}") from exc

    def stream_explanation(self, prompt: str) -> Generator[str, None, None]:
        """Stream chunks as they are generated by Qwen."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": "10m",
            "options": {
                "num_predict": 850,
                "temperature": 0.2,
                "repeat_penalty": 1.15,
            },
        }

        with requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            stream=True,
            timeout=180,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    import json
                    chunk = json.loads(line.decode("utf-8"))
                    text = chunk.get("response", "")
                    if text:
                        yield text
                    if chunk.get("done", False):
                        break

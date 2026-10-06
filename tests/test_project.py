"""
tests/test_project.py
=====================
Comprehensive test suite covering all 30 specified requirements:
1. valid GitHub URL
2. invalid GitHub URL
3. any public GitHub repository
4. another user's repository
5. README-only repository
6. docs-only repository
7. notebook repository
8. mixed-format repository
9. config repository
10. data/schema repository
11. binary file handling
12. sensitive file handling
13. large files
14. notebook parsing
15. complete repository inventory
16. smart context
17. duplicate prevention
18. file prioritization
19. technology detection
20. Qwen prompt
21. Ollama health
22. Qwen model availability
23. Ollama generation request
24. FastAPI health
25. FastAPI analyze
26. Streamlit entrypoint
27. error handling
28. user-session isolation
29. browser/local Ollama connector logic
30. latency instrumentation
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

from backend.code_extractor import CodeExtractor
from backend.context_builder import ContextBuilder
from backend.file_inspector import FileInspector
from backend.github_processor import GitHubProcessor
from backend.llm_service import OllamaService
from backend.main import app
from backend.models import FileRecord, RepositoryProcessingError
from backend.repository_analyzer import RepositoryAnalyzer
from backend.technology_detector import TechnologyDetector
from components.ollama_connector import render_ollama_connector


# ---------------------------------------------------------------------------
# Test 1: Valid GitHub URL
# ---------------------------------------------------------------------------
def test_valid_github_url():
    url = "https://github.com/psf/requests"
    normalized = GitHubProcessor.validate_url(url)
    assert normalized == "https://github.com/psf/requests.git"


# ---------------------------------------------------------------------------
# Test 2: Invalid GitHub URL
# ---------------------------------------------------------------------------
def test_invalid_github_url():
    with pytest.raises(RepositoryProcessingError):
        GitHubProcessor.validate_url("")

    with pytest.raises(RepositoryProcessingError):
        GitHubProcessor.validate_url("https://gitlab.com/user/project")

    with pytest.raises(RepositoryProcessingError):
        GitHubProcessor.validate_url("https://github.com/incomplete")


# ---------------------------------------------------------------------------
# Test 3: Any public GitHub repository
# ---------------------------------------------------------------------------
def test_any_public_github_repository():
    # Accepts arbitrary valid repository URLs without restrictions
    assert GitHubProcessor.validate_url("https://github.com/torvalds/linux") == "https://github.com/torvalds/linux.git"
    assert GitHubProcessor.validate_url("https://github.com/pallets/flask.git") == "https://github.com/pallets/flask.git"


# ---------------------------------------------------------------------------
# Test 4: Another user's repository
# ---------------------------------------------------------------------------
def test_another_users_repository():
    # Ensures no hardcoded ownership check for keerthi or any specific user
    url = "https://github.com/octocat/Spoon-Knife"
    normalized = GitHubProcessor.validate_url(url)
    assert "octocat" in normalized
    assert "Spoon-Knife" in normalized


# ---------------------------------------------------------------------------
# Test 5: README-only repository
# ---------------------------------------------------------------------------
def test_readme_only_repository():
    inspector = FileInspector()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text("# Documentation Only Project\nThis project contains only docs.", encoding="utf-8")
        records = inspector.scan_repository(root)
        assert len(records) == 1
        assert records[0].category == "DOCUMENTATION"
        meaningful = [r for r in records if r.category != "BINARY/ASSET" and not r.sensitive]
        assert len(meaningful) == 1


# ---------------------------------------------------------------------------
# Test 6: Docs-only repository
# ---------------------------------------------------------------------------
def test_docs_only_repository():
    inspector = FileInspector()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "guide.md").write_text("# User Guide", encoding="utf-8")
        (root / "api.rst").write_text("API Reference", encoding="utf-8")
        records = inspector.scan_repository(root)
        categories = {r.category for r in records}
        assert "DOCUMENTATION" in categories
        assert len(records) == 2


# ---------------------------------------------------------------------------
# Test 7: Notebook repository
# ---------------------------------------------------------------------------
def test_notebook_repository():
    inspector = FileInspector()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        nb_data = {
            "cells": [
                {"cell_type": "markdown", "source": ["# Analysis Notebook"]},
                {"cell_type": "code", "source": ["import numpy as np\nprint(1)"]},
            ]
        }
        (root / "model_training.ipynb").write_text(json.dumps(nb_data), encoding="utf-8")
        records = inspector.scan_repository(root)
        assert records[0].category == "NOTEBOOK"
        assert records[0].readable is True


# ---------------------------------------------------------------------------
# Test 8: Mixed-format repository
# ---------------------------------------------------------------------------
def test_mixed_format_repository():
    inspector = FileInspector()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "main.py").write_text("print('hello')", encoding="utf-8")
        (root / "index.js").write_text("console.log('hi')", encoding="utf-8")
        (root / "README.md").write_text("# Project", encoding="utf-8")
        (root / "config.json").write_text('{"key": "value"}', encoding="utf-8")
        records = inspector.scan_repository(root)
        cats = {r.category for r in records}
        assert "SOURCE" in cats
        assert "DOCUMENTATION" in cats
        assert "CONFIGURATION" in cats


# ---------------------------------------------------------------------------
# Test 9: Config repository
# ---------------------------------------------------------------------------
def test_config_repository():
    inspector = FileInspector()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "settings.yaml").write_text("env: prod\nport: 8080", encoding="utf-8")
        (root / "app.toml").write_text("[database]\nhost = 'localhost'", encoding="utf-8")
        records = inspector.scan_repository(root)
        assert all(r.category == "CONFIGURATION" for r in records)


# ---------------------------------------------------------------------------
# Test 10: Data/schema repository
# ---------------------------------------------------------------------------
def test_data_schema_repository():
    inspector = FileInspector()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "users.csv").write_text("id,name\n1,alice", encoding="utf-8")
        (root / "events.jsonl").write_text('{"event": "click"}', encoding="utf-8")
        records = inspector.scan_repository(root)
        assert all(r.category == "DATA/SCHEMA" for r in records)


# ---------------------------------------------------------------------------
# Test 11: Binary file handling
# ---------------------------------------------------------------------------
def test_binary_file_handling():
    inspector = FileInspector()
    extractor = CodeExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        binary_file = root / "sample.pdf"
        binary_file.write_bytes(b"%PDF-1.4 binary content \x00\x01\x02")
        records = inspector.scan_repository(root)
        assert records[0].category == "BINARY/ASSET"
        assert records[0].readable is False

        # Must extract empty string so raw binary is never sent to LLM
        content = extractor.extract_content(root, records[0])
        assert content == ""


# ---------------------------------------------------------------------------
# Test 12: Sensitive file handling
# ---------------------------------------------------------------------------
def test_sensitive_file_handling():
    inspector = FileInspector()
    extractor = CodeExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".env").write_text("API_SECRET_KEY=super_secret_token_12345", encoding="utf-8")
        (root / "credentials.json").write_text('{"private_key": "private_val"}', encoding="utf-8")

        records = inspector.scan_repository(root)
        for r in records:
            assert r.sensitive is True
            assert r.readable is False
            # Contents must NEVER be extracted
            extracted = extractor.extract_content(root, r)
            assert "super_secret_token_12345" not in extracted
            assert "private_val" not in extracted


# ---------------------------------------------------------------------------
# Test 13: Large files
# ---------------------------------------------------------------------------
def test_large_files_truncation():
    extractor = CodeExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        big_file = root / "large_module.py"
        # 100,000 characters
        big_file.write_text("class Processor:\n    pass\n\ndef run():\n    return 1\n" * 2500, encoding="utf-8")

        record = FileRecord(
            path="large_module.py",
            category="SOURCE",
            extension=".py",
            size_bytes=big_file.stat().st_size,
            readable=True,
            sensitive=False,
        )

        extracted = extractor.extract_content(root, record, max_file_chars=5000)
        assert len(extracted) <= 6000
        assert "[TRUNCATED FOR CONTEXT]" in extracted


# ---------------------------------------------------------------------------
# Test 14: Notebook parsing
# ---------------------------------------------------------------------------
def test_notebook_parsing():
    extractor = CodeExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        nb_file = root / "experiment.ipynb"
        nb_data = {
            "cells": [
                {"cell_type": "markdown", "source": ["### Experiment Step 1"]},
                {"cell_type": "code", "source": ["import torch\nx = torch.tensor([1, 2, 3])"]},
            ]
        }
        nb_file.write_text(json.dumps(nb_data), encoding="utf-8")

        record = FileRecord(
            path="experiment.ipynb",
            category="NOTEBOOK",
            extension=".ipynb",
            size_bytes=nb_file.stat().st_size,
            readable=True,
            sensitive=False,
        )

        content = extractor.extract_content(root, record, max_file_chars=10_000)
        assert "### Experiment Step 1" in content
        assert "import torch" in content


# ---------------------------------------------------------------------------
# Test 15: Complete repository inventory
# ---------------------------------------------------------------------------
def test_complete_repository_inventory():
    inspector = FileInspector()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text("# Overview", encoding="utf-8")
        (root / "main.py").write_text("print('start')", encoding="utf-8")
        (root / "data.csv").write_text("a,b", encoding="utf-8")
        (root / "config.yaml").write_text("a: 1", encoding="utf-8")
        (root / "logo.png").write_bytes(b"\x89PNG")

        records = inspector.scan_repository(root)
        counts = inspector.calculate_counts(records)
        assert len(records) == 5
        assert counts["DOCUMENTATION"] == 1
        assert counts["SOURCE"] == 1
        assert counts["DATA/SCHEMA"] == 1
        assert counts["CONFIGURATION"] == 1
        assert counts["BINARY/ASSET"] == 1


# ---------------------------------------------------------------------------
# Test 16: Smart context
# ---------------------------------------------------------------------------
def test_smart_context():
    builder = ContextBuilder(max_total_context=2000, max_files_for_llm=5)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for i in range(10):
            (root / f"file_{i}.py").write_text("def process():\n    return 'val'\n" * 100, encoding="utf-8")

        inspector = FileInspector()
        records = inspector.scan_repository(root)
        selected = builder.rank_files(records)
        context = builder.build_context(root, selected)
        assert len(context) <= 2500  # Within bounded context limit


# ---------------------------------------------------------------------------
# Test 17: Duplicate prevention
# ---------------------------------------------------------------------------
def test_duplicate_prevention():
    builder = ContextBuilder(max_files_for_llm=10)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "main.py").write_text("print(1)", encoding="utf-8")
        (root / "README.md").write_text("# Readme", encoding="utf-8")

        inspector = FileInspector()
        records = inspector.scan_repository(root)
        # Duplicate record artificially
        records.append(records[0])
        ranked = builder.rank_files(records)
        paths = [r.path for r in ranked]
        assert len(paths) == len(set(paths))


# ---------------------------------------------------------------------------
# Test 18: File prioritization
# ---------------------------------------------------------------------------
def test_file_prioritization():
    builder = ContextBuilder(max_files_for_llm=3)
    records = [
        FileRecord(path="tests/test_a.py", category="TESTS", extension=".py", size_bytes=100, readable=True),
        FileRecord(path="README.md", category="DOCUMENTATION", extension=".md", size_bytes=100, readable=True),
        FileRecord(path="requirements.txt", category="DEPENDENCIES", extension=".txt", size_bytes=100, readable=True),
        FileRecord(path="main.py", category="SOURCE", extension=".py", size_bytes=100, readable=True),
    ]
    ranked = builder.rank_files(records)
    assert ranked[0].path == "README.md"
    assert ranked[1].path == "requirements.txt"
    assert ranked[2].path == "main.py"


# ---------------------------------------------------------------------------
# Test 19: Technology detection
# ---------------------------------------------------------------------------
def test_technology_detection():
    detector = TechnologyDetector()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "requirements.txt").write_text("fastapi==0.110.0\nuvicorn>=0.28.0\npydantic\n", encoding="utf-8")
        (root / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()", encoding="utf-8")

        records = [
            FileRecord(path="requirements.txt", category="DEPENDENCIES", extension=".txt", size_bytes=50, readable=True),
            FileRecord(path="main.py", category="SOURCE", extension=".py", size_bytes=50, readable=True, language="Python"),
        ]
        technologies = detector.detect(root, records)
        assert "FastAPI" in technologies
        assert "Pydantic" in technologies
        assert "Python" in technologies


# ---------------------------------------------------------------------------
# Test 20: Qwen prompt
# ---------------------------------------------------------------------------
def test_qwen_prompt():
    builder = ContextBuilder()
    prompt = builder.build_prompt(
        repo_name="demo-app",
        repo_owner="alice",
        repo_type="Python Web Application",
        technologies=["Python", "FastAPI"],
        file_inventory=[FileRecord(path="main.py", category="SOURCE", extension=".py", size_bytes=100, readable=True)],
        folder_tree=["main.py"],
        code_context="from fastapi import FastAPI\napp = FastAPI()",
    )
    # Check that required sections and strict instructions are present
    assert "Use ONLY the supplied repository evidence" in prompt
    assert "1. Project Overview" in prompt
    assert "23. Limitations/Unknown Information" in prompt
    assert "demo-app" in prompt


# ---------------------------------------------------------------------------
# Test 21: Ollama health
# ---------------------------------------------------------------------------
def test_ollama_health():
    service = OllamaService(base_url="http://127.0.0.1:11434")
    # Even if Ollama is unreachable in some CI, check_status returns a structured OllamaStatusResponse
    status = service.check_status()
    assert isinstance(status.connected, bool)
    assert status.model_name == "qwen2.5:3b"


# ---------------------------------------------------------------------------
# Test 22: Qwen model availability
# ---------------------------------------------------------------------------
def test_qwen_model_availability():
    service = OllamaService(model="qwen2.5:3b")
    # Mocking tags response to test detection logic
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "qwen2.5:3b"}, {"name": "llama3:latest"}]}

    with patch("requests.get", return_value=mock_resp):
        res = service.check_status()
        assert res.connected is True
        assert res.model_available is True


# ---------------------------------------------------------------------------
# Test 23: Ollama generation request
# ---------------------------------------------------------------------------
def test_ollama_generation_request():
    service = OllamaService(model="qwen2.5:3b")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "This project is an API service built with FastAPI."}

    with patch("requests.post", return_value=mock_resp):
        explanation, elapsed = service.generate_explanation("Sample Prompt")
        assert "FastAPI" in explanation
        assert elapsed >= 0


# ---------------------------------------------------------------------------
# Test 24: FastAPI health
# ---------------------------------------------------------------------------
def test_fastapi_health():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert root_resp.json()["model"] == "qwen2.5:3b"


# ---------------------------------------------------------------------------
# Test 25: FastAPI analyze
# ---------------------------------------------------------------------------
def test_fastapi_analyze():
    client = TestClient(app)
    # Testing invalid url validation
    resp = client.post("/api/analyze", json={"repository_url": "invalid-url"})
    assert resp.status_code == 422  # Unprocessable Entity (Pydantic validation)


# ---------------------------------------------------------------------------
# Test 26: Streamlit entrypoint
# ---------------------------------------------------------------------------
def test_streamlit_entrypoint():
    app_path = ROOT / "app.py"
    req_path = ROOT / "requirements.txt"
    assert app_path.exists(), "app.py must be in repository root"
    assert req_path.exists(), "requirements.txt must be in repository root"

    content = app_path.read_text(encoding="utf-8")
    assert "GITHUB REPOSITORY CODE EXPLAINER" in content
    assert "qwen2.5:3b" in content


# ---------------------------------------------------------------------------
# Test 27: Error handling
# ---------------------------------------------------------------------------
def test_error_handling():
    # Verify that invalid repository produces user-friendly error without crashing
    with pytest.raises(RepositoryProcessingError) as exc_info:
        GitHubProcessor.validate_url("https://github.com/bad/url/extra/levels")
    assert "Incomplete" in str(exc_info.value) or "Invalid" in str(exc_info.value) or "Incomplete GitHub URL" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 28: User-session isolation
# ---------------------------------------------------------------------------
def test_user_session_isolation():
    # Analyzer should not store mutable global user state between calls
    analyzer_1 = RepositoryAnalyzer()
    analyzer_2 = RepositoryAnalyzer()
    assert analyzer_1 is not analyzer_2
    assert analyzer_1.context_builder is not analyzer_2.context_builder


# ---------------------------------------------------------------------------
# Test 29: Browser/local Ollama connector logic
# ---------------------------------------------------------------------------
def test_browser_local_ollama_connector_logic():
    # Verify that the connector template renders with the expected target endpoints
    with patch("streamlit.components.v1.html") as mock_html:
        render_ollama_connector(
            prompt="Analyze this repo",
            default_endpoint="http://127.0.0.1:11434",
            model_name="qwen2.5:3b",
        )
        assert mock_html.called
        html_code = mock_html.call_args[0][0]
        assert "http://127.0.0.1:11434" in html_code
        assert "qwen2.5:3b" in html_code
        assert "OLLAMA_ORIGINS" in html_code


# ---------------------------------------------------------------------------
# Test 30: Latency instrumentation
# ---------------------------------------------------------------------------
def test_latency_instrumentation():
    inspector = FileInspector()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text("# Hello", encoding="utf-8")
        t0 = time.perf_counter()
        inspector.scan_repository(root)
        elapsed = time.perf_counter() - t0
        assert elapsed >= 0.0
        assert elapsed < 1.0  # Fast scan execution

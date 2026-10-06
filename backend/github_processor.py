"""
backend/github_processor.py
===========================
Handles validation and safe shallow-cloning of ANY public GitHub repository.

Key safety & performance rules:
1. Accepts ANY public GitHub URL (no restriction by owner, language, or repo name).
2. Uses GitPython shallow clone (depth=1) to minimize download size, memory, and time.
3. NEVER executes repository code (no python, npm, bash, powershell execution).
4. Strictly cleans up temporary clone folders upon completion.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from git import Repo

from backend.models import RepositoryProcessingError


class GitHubProcessor:
    """Validates public GitHub repository URLs and performs safe shallow clones."""

    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate and normalize any public GitHub repository URL.
        Accepts:
            https://github.com/owner/repo
            http://github.com/owner/repo
            github.com/owner/repo
            https://github.com/owner/repo.git
        Returns normalized clone URL: https://github.com/owner/repo.git
        """
        raw = url.strip()
        if not raw:
            raise RepositoryProcessingError("Please enter a public GitHub repository URL.")

        if not raw.startswith("http://") and not raw.startswith("https://"):
            raw = f"https://{raw}"

        parsed = urlparse(raw)
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise RepositoryProcessingError(
                "Invalid URL. The repository must be hosted on github.com (e.g., https://github.com/psf/requests)."
            )

        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) != 2 or parts[0].startswith(".") or parts[1].startswith("."):
            raise RepositoryProcessingError(
                "Invalid GitHub URL. Please provide both the username/organization and repository name (e.g., https://github.com/owner/repo)."
            )

        owner = parts[0]
        repo_name = parts[1].removesuffix(".git")
        return f"https://github.com/{owner}/{repo_name}.git"

    def clone_repository(self, clone_url: str) -> tuple[Path, Path, float]:
        """
        Perform a shallow clone (depth=1) into a temporary isolated directory.
        Returns (temp_dir_path, destination_path, clone_time_seconds).
        Raises RepositoryProcessingError on failure.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="local_repo_explainer_"))
        destination = temp_dir / "repo"

        t0 = time.perf_counter()
        try:
            Repo.clone_from(clone_url, destination, depth=1, single_branch=True)
            clone_time = time.perf_counter() - t0
            return temp_dir, destination, clone_time
        except Exception as exc:
            # Clean up temporary folder on failure
            shutil.rmtree(temp_dir, ignore_errors=True)
            err_text = str(exc).lower()

            if any(k in err_text for k in ["not found", "authentication", "terminal prompts disabled", "access denied"]):
                raise RepositoryProcessingError(
                    "Unable to clone repository. Please verify that the repository exists, is public (not private), "
                    "and the URL is spelled correctly."
                ) from exc
            elif "timed out" in err_text or "connection" in err_text:
                raise RepositoryProcessingError(
                    "Network error while cloning repository. Please verify your internet connection."
                ) from exc
            else:
                raise RepositoryProcessingError(f"Git clone failed: {exc}") from exc

    @staticmethod
    def cleanup(temp_dir: Path) -> None:
        """Safely delete the temporary clone directory."""
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

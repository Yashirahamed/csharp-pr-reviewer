"""GitHub changed files and diff patches fetcher component."""
import logging
from typing import Any
import requests
from src.core.config import AppConfig
from src.core.exceptions import APIException

logger = logging.getLogger("ReviewEngine.GitHub")

class FileFetcher:
    """Retrieves file details and diff patch text streams from the GitHub REST API."""

    def __init__(self, session: requests.Session, config: AppConfig) -> None:
        self.session = session
        self.config = config
        
        repo_parts = self.config.github_repository.split("/")
        if len(repo_parts) != 2:
            raise APIException(
                message="Invalid GITHUB_REPOSITORY configuration format.",
                details=f"Expected 'owner/repo', got '{self.config.github_repository}'"
            )
        self.owner = repo_parts[0]
        self.repo = repo_parts[1]

    async def get_changed_files(self, pr_number: int) -> list[dict[str, Any]]:
        """Queries files modified in the pull request, resolving pagination.

        Args:
            pr_number: Pull Request number identifier.

        Returns:
            A list of changed file metadata dict objects.

        Raises:
            APIException: If API connections fail.
        """
        changed_files: list[dict[str, Any]] = []
        page = 1
        per_page = 100  # Max pagination limit for GitHub pulls API

        logger.info(
            "Fetching changed files list from GitHub.",
            extra={"context": {"pr_number": pr_number}}
        )

        try:
            while True:
                url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{pr_number}/files"
                params = {"page": page, "per_page": per_page}
                
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                page_data = response.json()
                if not page_data:
                    break
                
                changed_files.extend(page_data)
                
                # If we received fewer items than requested, we are on the last page
                if len(page_data) < per_page:
                    break
                    
                page += 1

            logger.info(
                f"Retrieved {len(changed_files)} changed files metadata.",
                extra={"context": {"pr_number": pr_number, "total_files": len(changed_files)}}
            )
            return changed_files

        except requests.exceptions.RequestException as req_err:
            status_code = req_err.response.status_code if req_err.response else None
            raise APIException(
                message="Failed to retrieve changed files from GitHub API.",
                status_code=status_code,
                details=str(req_err)
            )

    async def get_raw_diff(self, pr_number: int) -> str:
        """Fetches the unified raw diff stream for the pull request.

        Args:
            pr_number: Pull Request number identifier.

        Returns:
            The raw unified diff string patch.

        Raises:
            APIException: If the call fails.
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
        logger.info(
            "Fetching raw unified diff stream from GitHub.",
            extra={"context": {"url": url, "pr_number": pr_number}}
        )

        try:
            # Injecting specific Accept header resolves the raw unified diff format
            headers = {"Accept": "application/vnd.github.diff"}
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            return response.text
            
        except requests.exceptions.RequestException as req_err:
            status_code = req_err.response.status_code if req_err.response else None
            raise APIException(
                message="Failed to retrieve raw diff patch from GitHub API.",
                status_code=status_code,
                details=str(req_err)
            )

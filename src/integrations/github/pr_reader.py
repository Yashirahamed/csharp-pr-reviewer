"""GitHub PR reader component."""
import logging
import requests
from src.core.config import AppConfig
from src.core.exceptions import APIException
from src.models.pull_request import PullRequest

logger = logging.getLogger("ReviewEngine.GitHub")

class PRReader:
    """Fetches and parses Pull Request metadata from the GitHub REST API."""

    def __init__(self, session: requests.Session, config: AppConfig) -> None:
        self.session = session
        self.config = config
        
        # Parse owner and repository names from GITHUB_REPOSITORY (e.g., owner/repo)
        repo_parts = self.config.github_repository.split("/")
        if len(repo_parts) != 2:
            raise APIException(
                message="Invalid GITHUB_REPOSITORY configuration format.",
                details=f"Expected 'owner/repo', got '{self.config.github_repository}'"
            )
        self.owner = repo_parts[0]
        self.repo = repo_parts[1]

    async def get_pull_request(self, pr_number: int) -> PullRequest:
        """Queries the GitHub API and parses the Pull Request metadata.

        Args:
            pr_number: Pull Request number identifier.

        Returns:
            A PullRequest domain model instance.

        Raises:
            APIException: If requests fail or return unauthorized states.
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
        logger.info(
            "Fetching Pull Request metadata from GitHub.",
            extra={"context": {"url": url, "pr_number": pr_number}}
        )

        try:
            response = self.session.get(url)
            
            # Rate limit checking can also be called dynamically
            if response.status_code == 404:
                raise APIException(
                    message=f"Pull Request #{pr_number} not found on repository.",
                    status_code=404,
                    details=f"URL: {url}"
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Construct and validate PullRequest domain model
            return PullRequest(
                pr_number=pr_number,
                title=data.get("title", ""),
                description=data.get("body") or "",
                state=data.get("state", "open"),
                is_draft=data.get("draft", False),
                head_sha=data.get("head", {}).get("sha", ""),
                base_sha=data.get("base", {}).get("sha", ""),
                html_url=data.get("html_url", "")
            )
        except requests.exceptions.RequestException as req_err:
            status_code = req_err.response.status_code if req_err.response else None
            raise APIException(
                message="Failed to retrieve PR details from GitHub API.",
                status_code=status_code,
                details=str(req_err)
            )

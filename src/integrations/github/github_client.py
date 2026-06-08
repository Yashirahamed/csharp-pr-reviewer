"""GitHub REST API client facade implementation."""
import logging
import time
from typing import Any
import requests
from src.interfaces.github_client import IGitHubClient
from src.core.config import AppConfig
from src.core.exceptions import APIException
from src.models.pull_request import PullRequest
from src.models.review import Review

# Sub-services
from src.integrations.github.pr_reader import PRReader
from src.integrations.github.file_fetcher import FileFetcher
from src.integrations.github.comment_publisher import CommentPublisher

logger = logging.getLogger("ReviewEngine.GitHub")

class GitHubClient(IGitHubClient):
    """Facade class implementing IGitHubClient and coordinating PR interactions."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session = requests.Session()
        
        # Configure headers (User-Agent is mandatory for GitHub API requests)
        self.session.headers.update({
            "Authorization": f"Bearer {self.config.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-GitHub-PR-Reviewer-Engine"
        })
        
        # Hook to monitor API rate limit metrics after every response
        self.session.hooks["response"].append(self._check_rate_limits)

        # Instantiate sub-services sharing the session configuration
        self.reader = PRReader(self.session, self.config)
        self.fetcher = FileFetcher(self.session, self.config)
        self.publisher = CommentPublisher(self.session, self.config)

    def _check_rate_limits(self, response: requests.Response, *args: Any, **kwargs: Any) -> None:
        """Examines headers to prevent rate limits exhaustion."""
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_time = response.headers.get("X-RateLimit-Reset")
        
        if remaining is not None and reset_time is not None:
            rem_val = int(remaining)
            reset_val = int(reset_time)
            
            # Log warning if token quota is running low
            if rem_val < 50:
                sleep_duration = max(0, reset_val - int(time.time()))
                logger.warning(
                    f"GitHub API remaining rate limit is low ({rem_val}). Resetting in {sleep_duration}s.",
                    extra={"context": {"remaining": rem_val, "reset_in_seconds": sleep_duration}}
                )
                
                # If we have run out of API quota, block execution until the limit resets
                if rem_val == 0:
                    logger.error(
                        f"GitHub API Rate Limit Exhausted. Sleeping for {sleep_duration} seconds.",
                        extra={"context": {"remaining": rem_val, "reset_in_seconds": sleep_duration}}
                    )
                    time.sleep(sleep_duration + 2)  # Buffer padding

    async def get_pull_request(self, pr_number: int) -> PullRequest:
        return await self.reader.get_pull_request(pr_number)

    async def get_changed_files(self, pr_number: int) -> list[dict[str, Any]]:
        return await self.fetcher.get_changed_files(pr_number)

    async def get_raw_diff(self, pr_number: int) -> str:
        return await self.fetcher.get_raw_diff(pr_number)

    async def submit_review(self, pr_number: int, review: Review) -> None:
        await self.publisher.submit_review(pr_number, review)

    async def get_review_comments(self, pr_number: int) -> list[dict[str, Any]]:
        """Queries existing inline comments posted on the pull request."""
        repo_parts = self.config.github_repository.split("/")
        if len(repo_parts) != 2:
            raise APIException(
                message="Invalid GITHUB_REPOSITORY configuration format.",
                details=f"Expected 'owner/repo', got '{self.config.github_repository}'"
            )
        owner, repo = repo_parts[0], repo_parts[1]
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        
        logger.info(
            "Fetching existing review comments from GitHub API.",
            extra={"context": {"url": url, "pr_number": pr_number}}
        )

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as req_err:
            status_code = req_err.response.status_code if req_err.response else None
            raise APIException(
                message="Failed to retrieve review comments from GitHub API.",
                status_code=status_code,
                details=str(req_err)
            )

    def close(self) -> None:
        """Closes the underlying requests session connections."""
        self.session.close()

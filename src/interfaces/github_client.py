"""GitHub client service interface contract."""
from abc import ABC, abstractmethod
from typing import Any
from src.models.pull_request import PullRequest
from src.models.review import Review

class IGitHubClient(ABC):
    """Abstract interface defining required GitHub REST API interactions."""

    @abstractmethod
    async def get_pull_request(self, pr_number: int) -> PullRequest:
        """Fetches metadata about the specified pull request.

        Args:
            pr_number: The target pull request number identifier.

        Returns:
            A PullRequest domain model instance.

        Raises:
            APIException: If the GitHub API returns an error status.
        """
        pass

    @abstractmethod
    async def get_changed_files(self, pr_number: int) -> list[dict[str, Any]]:
        """Fetches the list of files modified in the pull request.

        Args:
            pr_number: The target pull request number identifier.

        Returns:
            A list of changed file metadata dict objects.

        Raises:
            APIException: If the GitHub API returns an error status.
        """
        pass

    @abstractmethod
    async def get_raw_diff(self, pr_number: int) -> str:
        """Fetches the unified raw diff contents of the pull request.

        Args:
            pr_number: The target pull request number identifier.

        Returns:
            A string containing the raw diff patch data.

        Raises:
            APIException: If the GitHub API returns an error status.
        """
        pass

    @abstractmethod
    async def submit_review(self, pr_number: int, review: Review) -> None:
        """Submits inline comments and the high-level review summary to the PR.

        Args:
            pr_number: The target pull request number identifier.
            review: The Review aggregate object containing findings and summary.

        Raises:
            APIException: If the GitHub API returns an error status.
        """
        pass

    @abstractmethod
    async def get_review_comments(self, pr_number: int) -> list[dict[str, Any]]:
        """Fetches existing review comments on the pull request.

        Args:
            pr_number: The target pull request number identifier.

        Returns:
            A list of comments metadata dicts.

        Raises:
            APIException: If the GitHub API returns an error status.
        """
        pass

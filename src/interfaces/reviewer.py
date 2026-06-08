"""Code review orchestrator service interface contract."""
from abc import ABC, abstractmethod
from src.models.review import Review

class IReviewer(ABC):
    """Abstract interface defining the entrypoint for executing the code review pipeline."""

    @abstractmethod
    async def review_pull_request(self, pr_number: int) -> Review:
        """Runs the 6-stage autonomous code review process on the specified Pull Request.

        Args:
            pr_number: Target Pull Request number identifier.

        Returns:
            A Review aggregate object containing findings, summaries, and stats.

        Raises:
            ReviewEngineException: If any stage in the review loop fails.
        """
        pass

"""Review publishing coordinator and duplicate prevention manager."""
import logging
from typing import Any
from src.core.config import AppConfig
from src.core.exceptions import APIException
from src.interfaces.github_client import IGitHubClient
from src.models.review import Review
from src.models.findings import Finding
from src.services.publishing.review_formatter import ReviewFormatter
from src.services.publishing.review_summary_generator import ReviewSummaryGenerator

logger = logging.getLogger("ReviewEngine.Publishing")

class PublishManager:
    """Coordinates code review submissions, filters out duplicates, and supports dry-run configurations."""

    def __init__(
        self,
        github_client: IGitHubClient,
        formatter: ReviewFormatter,
        summary_generator: ReviewSummaryGenerator,
        config: AppConfig
    ) -> None:
        self.github_client = github_client
        self.formatter = formatter
        self.summary_generator = summary_generator
        self.config = config

    def is_duplicate_comment(self, finding: Finding, existing_comments: list[dict[str, Any]]) -> bool:
        """Determines if the finding was already posted to the target coordinate.

        Args:
            finding: The active finding object under review.
            existing_comments: List of comments currently posted on the Pull Request.

        Returns:
            True if the finding is matched.
        """
        for ext_c in existing_comments:
            # Check path and line number coordinates
            if ext_c.get("path") == finding.file_path and ext_c.get("line") == finding.line_number:
                # Deduplicate based on rule ID presence in body text
                body_text = ext_c.get("body", "")
                if finding.rule_id in body_text:
                    return True
        return False

    async def publish_review(
        self, 
        pr_number: int, 
        review: Review, 
        dry_run: bool | None = None
    ) -> None:
        """Processes duplicate checks, renders summary markdown, and submits the review.

        Args:
            pr_number: Pull Request number identifier.
            review: Review aggregate model containing findings and stats.
            dry_run: If True or None (falling back to config), logs payload to console without posting.

        Raises:
            APIException: If requests fail.
        """
        if dry_run is None:
            dry_run = self.config.dry_run

        logger.info(
            f"PublishManager: Resolving review submission for PR #{pr_number}.",
            extra={"context": {"pr_number": pr_number, "dry_run": dry_run}}
        )

        # 1. Fetch existing PR comments for deduplication checks
        try:
            existing_comments = await self.github_client.get_review_comments(pr_number)
        except Exception as err:
            logger.warning(
                f"Failed to fetch existing comments list: {err}. Proceeding without deduplication.",
                exc_info=True
            )
            existing_comments = []

        # 2. Filter out findings that have already been posted
        non_duplicate_findings = []
        for finding in review.findings:
            if self.is_duplicate_comment(finding, existing_comments):
                logger.info(
                    f"Deduplication: Skipped comment for finding [{finding.rule_id}] on "
                    f"`{finding.file_path}:{finding.line_number}` (Already posted)."
                )
            else:
                non_duplicate_findings.append(finding)

        # 3. Generate summary markdown
        # Update the stats for findings counts mapping
        stats = review.stats
        summary_markdown = self.summary_generator.generate_summary(non_duplicate_findings, stats)

        # Build clean Review object containing only non-duplicate findings
        filtered_review = Review(
            pull_request=review.pull_request,
            findings=non_duplicate_findings,
            verdict=review.verdict,
            summary_markdown=summary_markdown,
            stats=stats
        )

        if dry_run:
            logger.warning("Dry-run mode is ENABLED. Printing review payloads to stdout logs:")
            print("\n=== DRY-RUN REVIEW SUMMARY ===")
            print(filtered_review.summary_markdown)
            print("=== DRY-RUN INLINE COMMENTS ===")
            for idx, f in enumerate(filtered_review.findings):
                formatted_body = self.formatter.format_inline_body(f)
                print(f"Comment {idx + 1} on `{f.file_path}:{f.line_number}`:")
                print(formatted_body)
                print("-" * 30)
            logger.info("Dry-run submission completed successfully.")
            return

        # 4. Submit review comments using GitHubClient wrapper
        await self.github_client.submit_review(pr_number, filtered_review)
        logger.info("PR review submission completed successfully.")

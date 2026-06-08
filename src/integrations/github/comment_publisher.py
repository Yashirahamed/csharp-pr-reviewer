"""GitHub comment and review publisher component."""
import logging
import requests
from src.core.config import AppConfig
from src.core.exceptions import APIException
from src.models.review import Review

logger = logging.getLogger("ReviewEngine.GitHub")

class CommentPublisher:
    """Submits inline comments and high-level review summaries to GitHub."""

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

    async def submit_review(self, pr_number: int, review: Review) -> None:
        """Assembles the review payload and POSTs it to the Pull Request reviews API.

        Args:
            pr_number: Pull Request number identifier.
            review: Review aggregate model containing findings and verdict parameters.

        Raises:
            APIException: If submission requests fail.
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{pr_number}/reviews"
        
        # Build inline comments payload
        comments_payload = []
        for finding in review.findings:
            body_text = (
                f"#### [{finding.rule_id}] {finding.title}\n"
                f"- **Severity**: {finding.severity}\n"
                f"- **Category**: {finding.category}\n\n"
                f"{finding.description}"
            )
            if finding.suggestion:
                body_text += f"\n\n```cs\n// Suggested Fix:\n{finding.suggestion}\n```"
                
            comments_payload.append({
                "path": finding.file_path,
                "line": finding.line_number,
                "side": "RIGHT",
                "body": body_text
            })

        payload = {
            "body": review.summary_markdown or "Gemini automated code review completed.",
            "event": review.verdict,
            "comments": comments_payload
        }

        logger.info(
            "Submitting review to GitHub.",
            extra={
                "context": {
                    "url": url,
                    "pr_number": pr_number,
                    "verdict": review.verdict,
                    "comments_count": len(comments_payload)
                }
            }
        )

        try:
            response = self.session.post(url, json=payload)
            
            # Submitting reviews with empty or out of date comment ranges can throw 422
            if response.status_code == 422:
                raise APIException(
                    message="Review payload validation failed on GitHub API (Unprocessable Entity).",
                    status_code=422,
                    details=response.text
                )
                
            response.raise_for_status()
            logger.info("GitHub review submitted successfully.")
            
        except requests.exceptions.RequestException as req_err:
            status_code = req_err.response.status_code if req_err.response else None
            raise APIException(
                message="Failed to submit code review to GitHub API.",
                status_code=status_code,
                details=str(req_err)
            )

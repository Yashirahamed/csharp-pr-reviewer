"""Formatting utilities for code reviews and markdown summaries."""
import logging
from src.models.findings import Finding

logger = logging.getLogger("ReviewEngine.Publishing")

class ReviewFormatter:
    """Formats findings, severity badges, and comments into styled markdown payloads."""

    def format_severity_badge(self, severity: str) -> str:
        """Formats the severity string with a colored status badge.

        Args:
            severity: Resolved severity (Critical, High, Medium, Low, Info).

        Returns:
            A string formatted with status emojis.
        """
        badges = {
            "Critical": "🔴 **Critical**",
            "High": "🟠 **High**",
            "Medium": "🟡 **Medium**",
            "Low": "🔵 **Low**",
            "Info": "⚪ **Info**",
        }
        return badges.get(severity, f"**{severity}**")

    def format_confidence_score(self, score: float) -> str:
        """Formats the confidence score float as a styled percentage.

        Args:
            score: Confidence value between 0.0 and 1.0.

        Returns:
            Formatted percentage text.
        """
        percentage = score * 100
        if score >= 0.90:
            return f"🟢 **{percentage:.1f}%** (High Confidence)"
        if score >= 0.75:
            return f"🟡 **{percentage:.1f}%** (Medium Confidence)"
        return f"🔴 **{percentage:.1f}%** (Low Confidence)"

    def format_inline_body(self, finding: Finding) -> str:
        """Formats the markdown text body for inline PR comments.

        Args:
            finding: The validated and prioritized finding object.

        Returns:
            The compiled markdown comment body.
        """
        badge = self.format_severity_badge(finding.severity)
        confidence = self.format_confidence_score(finding.confidence_score)

        body = (
            f"### {badge} - {finding.title}\n"
            f"- **Category**: {finding.category}\n"
            f"- **Confidence**: {confidence}\n"
            f"- **Rule ID**: `{finding.rule_id}`\n\n"
            f"{finding.description}"
        )

        if finding.suggestion:
            body += f"\n\n```cs\n// Suggested Fix:\n{finding.suggestion}\n```"

        return body

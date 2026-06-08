"""Line coordinate mapping service matching findings to modified code ranges."""
import logging
from typing import Any
from src.models.diff import ChangedFile
from src.models.findings import Finding

logger = logging.getLogger("ReviewEngine.Diff")

class LineMapper:
    """Matches line-specific findings back to target coordinates in PR diff hunks."""

    def is_line_modified(self, line_number: int, changed_file: ChangedFile) -> bool:
        """Determines if a given line number was added or modified in the pull request.

        Args:
            line_number: Line number to evaluate.
            changed_file: A parsed ChangedFile model containing diff hunks.

        Returns:
            True if the line falls within a modified hunk range.
        """
        for chunk in changed_file.chunks:
            for line in chunk.lines:
                # We check the RIGHT side (new_line_no) for additions
                if line.line_type == "addition" and line.new_line_no == line_number:
                    return True
        return False

    def verify_and_map_finding(self, finding: Finding, changed_file: ChangedFile) -> dict[str, Any] | None:
        """Verifies a finding's line coordinate and returns mapping details.

        Args:
            finding: The finding object to map.
            changed_file: A parsed ChangedFile model matching the finding's file path.

        Returns:
            A dict containing GitHub review comment coordinate mappings, 
            or None if the line number was not modified.
        """
        logger.info(
            f"Mapping coordinates for finding at line {finding.line_number} in file: {changed_file.filename}"
        )

        is_modified = self.is_line_modified(finding.line_number, changed_file)
        if not is_modified:
            logger.warning(
                f"Finding at line {finding.line_number} in {changed_file.filename} is on an UNMODIFIED line. "
                "This comment will be redirected to the PR summary.",
                extra={
                    "context": {
                        "file_path": changed_file.filename,
                        "line_number": finding.line_number
                    }
                }
            )
            return None

        # Return the required format for publishing comments via the API
        return {
            "path": changed_file.filename,
            "line": finding.line_number,
            "side": "RIGHT",
            "body": (
                f"#### [{finding.rule_id}] {finding.title}\n"
                f"- **Severity**: {finding.severity}\n"
                f"- **Category**: {finding.category}\n\n"
                f"{finding.description}"
            )
        }

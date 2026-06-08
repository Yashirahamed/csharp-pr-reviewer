"""Review validator service checking response schema and line locations."""
import logging
from typing import Any
from src.core.exceptions import ValidationException
from src.models.diff import ChangedFile
from src.models.findings import Finding

logger = logging.getLogger("ReviewEngine.Review")

class ReviewValidator:
    """Validates structural fields, schema layouts, and line coordinates of review findings."""

    def validate_schema(self, raw_data: dict[str, Any] | Any) -> list[dict[str, Any]]:
        """Validates that raw API responses contain a findings root array.

        Args:
            raw_data: Unprocessed JSON dictionary object.

        Returns:
            The parsed array list of findings dictionaries.

        Raises:
            ValidationException: If the schema layout is invalid.
        """
        if not isinstance(raw_data, dict):
            raise ValidationException(
                message="Gemini JSON response is not structured as an object dictionary."
            )
            
        findings = raw_data.get("findings")
        if findings is None:
            raise ValidationException(
                message="Gemini JSON response is missing required root key 'findings'."
            )
            
        if not isinstance(findings, list):
            raise ValidationException(
                message="Required root key 'findings' is not structured as a JSON list."
            )
            
        return findings

    def validate_finding_fields(self, data: dict[str, Any]) -> Finding | None:
        """Validates required properties and builds a Finding Pydantic model.

        Args:
            data: Raw finding dictionary object.

        Returns:
            A Finding instance, or None if validation fails.
        """
        required_fields = {
            "file_path", "line_number", "rule_id", "category",
            "severity", "title", "description"
        }
        
        missing = [f for f in required_fields if f not in data or data[f] is None]
        if missing:
            logger.warning(
                f"Skipping malformed finding: missing required keys: {', '.join(missing)}",
                extra={"context": {"raw_data": data}}
            )
            return None

        try:
            # Build and validate using Pydantic model
            return Finding(
                file_path=data["file_path"],
                line_number=int(data["line_number"]),
                rule_id=data["rule_id"],
                category=data["category"],
                severity=data["severity"],
                title=data["title"],
                description=data["description"],
                suggestion=data.get("suggestion") or "",
                confidence_score=float(data.get("confidence_score") or 1.0)
            )
        except (ValueError, TypeError) as val_err:
            logger.warning(
                f"Skipping finding due to type conversion failure: {val_err}",
                extra={"context": {"raw_data": data}}
            )
            return None

    def verify_finding_bounds(self, finding: Finding, changed_file: ChangedFile) -> bool:
        """Verifies if the finding line number is within the file changes.

        Args:
            finding: The finding object to verify.
            changed_file: A parsed ChangedFile model matching the finding file path.

        Returns:
            True if the line number falls within modified hunk ranges.
        """
        for chunk in changed_file.chunks:
            for line in chunk.lines:
                if line.line_type == "addition" and line.new_line_no == finding.line_number:
                    return True
        return False

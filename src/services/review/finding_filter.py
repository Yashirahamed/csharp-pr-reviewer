"""Findings filtering and deduplication service."""
import logging
from src.models.findings import Finding

logger = logging.getLogger("ReviewEngine.Review")

class FindingFilter:
    """Filters low-confidence findings and merges duplicate reports targeting the same code coordinate."""

    def __init__(self, confidence_threshold: float = 0.75) -> None:
        self.confidence_threshold = confidence_threshold

    def filter_findings(self, findings: list[Finding]) -> list[Finding]:
        """Filters out findings below the confidence threshold and removes duplicates.

        Args:
            findings: Array list of unfiltered findings.

        Returns:
            A clean list of deduplicated findings.
        """
        filtered: list[Finding] = []
        seen_coordinates = set()

        for finding in findings:
            # 1. Filter out low-confidence findings
            if finding.confidence_score < self.confidence_threshold:
                logger.warning(
                    f"Discarding finding [{finding.rule_id}] due to low confidence: {finding.confidence_score}",
                    extra={
                        "context": {
                            "rule_id": finding.rule_id,
                            "confidence": finding.confidence_score,
                            "threshold": self.confidence_threshold
                        }
                    }
                )
                continue

            # 2. Check for duplicate coordinates (file + line + rule_id)
            coordinate_key = (finding.file_path, finding.line_number, finding.rule_id)
            if coordinate_key in seen_coordinates:
                logger.info(
                    f"Discarding duplicate finding [{finding.rule_id}] at line {finding.line_number} in {finding.file_path}",
                    extra={"context": {"key": coordinate_key}}
                )
                continue

            seen_coordinates.add(coordinate_key)
            filtered.append(finding)

        logger.info(
            f"Filtered findings count: {len(filtered)} (removed {len(findings) - len(filtered)} duplicates/low-confidence)."
        )
        return filtered

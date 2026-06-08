"""Severity classification rules engine."""
import logging
from src.core.config import AppConfig
from src.models.findings import Finding

logger = logging.getLogger("ReviewEngine.Review")

class SeverityEngine:
    """Classifies and overrides finding severity levels based on categories and system settings."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        
        # Default category severity mappings
        self._default_mappings = {
            "Security": "High",
            "AsyncAwait": "High",
            "SOLID": "Medium",
            "Performance": "Medium",
            "ExceptionHandling": "Medium",
            "Style": "Low"
        }

    def resolve_severity(self, finding: Finding) -> str:
        """Determines the final standardized severity level for a finding.

        Args:
            finding: The validated finding instance.

        Returns:
            A string indicating the resolved severity (Critical, High, Medium, Low, Info).
        """
        category = finding.category
        rule_id = finding.rule_id
        
        # 1. Resolve default category mapping
        resolved = self._default_mappings.get(category, "Info")

        # 2. Apply special override rules
        if category == "Security" and any(word in finding.title.lower() for word in ("injection", "credential", "secret", "private")):
            resolved = "Critical"
            
        if category == "AsyncAwait" and "blocking" in finding.description.lower():
            resolved = "High"

        logger.info(
            f"Resolved severity for finding [{rule_id}] as: {resolved}",
            extra={"context": {"rule_id": rule_id, "category": category, "severity": resolved}}
        )

        return resolved

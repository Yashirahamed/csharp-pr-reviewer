"""Execution context and telemetry metrics container."""
import uuid
from datetime import datetime, timezone
from typing import Any

class ExecutionContext:
    """Manages runtime metadata, correlation IDs, and execution metrics."""

    def __init__(self, pr_number: int) -> None:
        self.run_id = str(uuid.uuid4())
        self.pr_number = pr_number
        self.start_time = datetime.now(timezone.utc)
        self.end_time: datetime | None = None
        
        # Telemetry metrics trackers
        self.files_analyzed = 0
        self.chunks_processed = 0
        self.input_tokens = 0
        self.output_tokens = 0
        
        # Audit statistics
        self.total_findings = 0
        self.critical_count = 0
        self.high_count = 0
        self.medium_count = 0
        self.low_count = 0
        self.info_count = 0
        self.errors_logged = 0

    def complete(self) -> None:
        """Sets the completion timestamp."""
        self.end_time = datetime.now(timezone.utc)

    @property
    def total_tokens(self) -> int:
        """Calculates total token usage."""
        return self.input_tokens + self.output_tokens

    @property
    def duration_seconds(self) -> float:
        """Calculates total run duration in seconds."""
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()

    def get_summary_stats(self) -> dict[str, Any]:
        """Returns a compiled dictionary of execution metrics."""
        return {
            "run_id": self.run_id,
            "pr_number": self.pr_number,
            "duration_s": round(self.duration_seconds, 2),
            "files_analyzed": self.files_analyzed,
            "chunks_processed": self.chunks_processed,
            "total_tokens": self.total_tokens,
            "findings_count": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "errors_logged": self.errors_logged
        }

"""Review aggregate domain model."""
from typing import Any
from pydantic import BaseModel, Field, field_validator
from src.models.pull_request import PullRequest
from src.models.findings import Finding

class Review(BaseModel):
    """Aggregate model containing all code review findings and metadata."""
    pull_request: PullRequest = Field(..., description="Target Pull Request metadata.")
    findings: list[Finding] = Field(default_factory=list, description="List of generated findings.")
    verdict: str = Field(..., description="Verdict status of the review (e.g. APPROVE, REQUEST_CHANGES, COMMENT).")
    summary_markdown: str = Field(default="", description="High-level markdown summary text.")
    stats: dict[str, Any] = Field(default_factory=dict, description="Execution run statistics (e.g. token count, latency).")

    @field_validator("verdict")
    @classmethod
    def validate_verdict(cls, v: str) -> str:
        valid_verdicts = {"APPROVE", "REQUEST_CHANGES", "COMMENT"}
        if v not in valid_verdicts:
            raise ValueError(f"Verdict must be one of: {', '.join(valid_verdicts)}")
        return v

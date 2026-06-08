"""Pull Request metadata domain model."""
from pydantic import BaseModel, Field, HttpUrl

class PullRequest(BaseModel):
    """Data model representing GitHub Pull Request metadata."""
    pr_number: int = Field(..., ge=1, description="The Pull Request identifier number.")
    title: str = Field(..., min_length=1, max_length=256, description="Title of the Pull Request.")
    description: str = Field(default="", description="The PR body description content.")
    state: str = Field(..., description="State status of the PR (e.g. open, closed).")
    is_draft: bool = Field(default=False, description="Flag indicating draft status.")
    head_sha: str = Field(..., min_length=40, max_length=40, description="SHA hash of the head commit branch.")
    base_sha: str = Field(..., min_length=40, max_length=40, description="SHA hash of the base target branch.")
    html_url: str = Field(..., description="Web URL path pointing to the GitHub PR page.")

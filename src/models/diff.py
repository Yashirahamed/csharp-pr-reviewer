"""Data models representing code diffs and parsing results."""
from typing import Any
from pydantic import BaseModel, Field

class LineMapping(BaseModel):
    """Maps a single diff line to its coordinates in original and new files."""
    line_type: str = Field(..., description="Type of line: addition, deletion, or context.")
    content: str = Field(..., description="The actual text line content.")
    old_line_no: int | None = Field(default=None, description="Line number in the old file (LEFT).")
    new_line_no: int | None = Field(default=None, description="Line number in the new file (RIGHT).")


class DiffChunk(BaseModel):
    """Represents a parsed unified diff hunk coordinate block."""
    old_start: int = Field(..., description="Starting line in the old file.")
    old_lines: int = Field(..., description="Number of lines modified/deleted in the old file.")
    new_start: int = Field(..., description="Starting line in the new file.")
    new_lines: int = Field(..., description="Number of lines added/modified in the new file.")
    lines: list[LineMapping] = Field(default_factory=list, description="Structured parsed line mappings.")


class ChangedFile(BaseModel):
    """Represents a file changed in the PR containing parsed diff chunks."""
    filename: str = Field(..., description="Path to the file relative to repository root.")
    status: str = Field(..., description="Status of the change (added, modified, renamed, deleted).")
    additions: int = Field(..., ge=0)
    deletions: int = Field(..., ge=0)
    patch: str | None = Field(default=None, description="Raw unified diff text stream.")
    chunks: list[DiffChunk] = Field(default_factory=list, description="Structured parsed diff chunks.")


class ReviewableChunk(BaseModel):
    """Represents a chunk of C# changes formatted and prepared for review."""
    file_path: str = Field(..., description="Target file path.")
    chunk_index: int = Field(..., ge=0, description="Chronological index of this chunk in the file.")
    patch_content: str = Field(..., description="Text content containing diff changes.")
    target_lines: list[int] = Field(..., description="Absolute new line numbers containing modifications.")
    context_before: str = Field(default="", description="Surrounding code context preceding modifications.")
    context_after: str = Field(default="", description="Surrounding code context following modifications.")

"""Diff extraction and chunk compilation service."""
import logging
from typing import Any
from src.models.diff import ChangedFile, DiffChunk, ReviewableChunk
from src.services.diff.diff_parser import DiffParser

logger = logging.getLogger("ReviewEngine.Diff")

class DiffExtractor:
    """Orchestrates diff parsing and compiles reviewable code chunks from file changes."""

    def __init__(self, parser: DiffParser) -> None:
        self.parser = parser

    def extract_file_diff(self, file_data: dict[str, Any] | Any) -> ChangedFile:
        """Parses the patch text within changed file metadata and returns a ChangedFile model.

        Args:
            file_data: Changed file metadata dictionary or object.

        Returns:
            A ChangedFile instance with parsed hunks.
        """
        # Supports both API dictionaries and Pydantic objects
        filename = file_data.filename if hasattr(file_data, "filename") else file_data.get("filename", "")
        status = file_data.status if hasattr(file_data, "status") else file_data.get("status", "")
        additions = file_data.additions if hasattr(file_data, "additions") else file_data.get("additions", 0)
        deletions = file_data.deletions if hasattr(file_data, "deletions") else file_data.get("deletions", 0)
        patch = file_data.patch if hasattr(file_data, "patch") else file_data.get("patch")

        logger.info(
            f"Extracting diff chunks for file: {filename}",
            extra={"context": {"file_path": filename, "status": status}}
        )

        parsed_chunks = self.parser.parse_patch(patch)

        return ChangedFile(
            filename=filename,
            status=status,
            additions=additions,
            deletions=deletions,
            patch=patch,
            chunks=parsed_chunks
        )

    def build_reviewable_chunks(self, changed_file: ChangedFile) -> list[ReviewableChunk]:
        """Compiles reviewable code chunks containing modified lines and their context.

        Args:
            changed_file: A parsed ChangedFile model containing diff hunks.

        Returns:
            A list of ReviewableChunk structures ready for AI analysis.
        """
        reviewable_chunks: list[ReviewableChunk] = []

        for idx, chunk in enumerate(changed_file.chunks):
            # Extract only the added or modified line coordinates (RIGHT side)
            added_lines = [
                line.new_line_no for line in chunk.lines 
                if line.line_type == "addition" and line.new_line_no is not None
            ]

            # If this hunk only contains deletions, skip it
            if not added_lines:
                logger.info(f"Skipping diff chunk {idx} in {changed_file.filename}: no additions.")
                continue

            # Format the patch block for review
            patch_lines = []
            for line in chunk.lines:
                if line.line_type == "addition":
                    patch_lines.append(f"+ {line.content}")
                elif line.line_type == "deletion":
                    patch_lines.append(f"- {line.content}")
                else:
                    patch_lines.append(f"  {line.content}")
            
            patch_content = "\n".join(patch_lines)

            # Assemble surrounding context strings
            context_before_lines = []
            context_after_lines = []
            
            # Simple context separation: first 5 and last 5 context lines
            context_lines = [line for line in chunk.lines if line.line_type == "context"]
            if len(context_lines) >= 5:
                context_before_lines = [l.content for l in context_lines[:5]]
                context_after_lines = [l.content for l in context_lines[-5:]]
            else:
                context_before_lines = [l.content for l in context_lines]

            reviewable_chunks.append(
                ReviewableChunk(
                    file_path=changed_file.filename,
                    chunk_index=idx,
                    patch_content=patch_content,
                    target_lines=added_lines,
                    context_before="\n".join(context_before_lines),
                    context_after="\n".join(context_after_lines)
                )
            )

        logger.info(
            f"Compiled {len(reviewable_chunks)} reviewable chunks for file: {changed_file.filename}"
        )
        return reviewable_chunks

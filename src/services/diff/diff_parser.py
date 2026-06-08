"""Unified diff parser service."""
import logging
import re
from src.models.diff import DiffChunk, LineMapping

logger = logging.getLogger("ReviewEngine.Diff")

class DiffParser:
    """Parses raw unified diff patch text streams into structured chunk objects."""

    # Regex to extract diff hunk coordinate ranges
    HUNK_HEADER_RE = re.compile(
        r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@"
    )

    def parse_patch(self, patch: str | None) -> list[DiffChunk]:
        """Parses a unified diff patch string.

        Args:
            patch: The raw diff patch text stream.

        Returns:
            A list of parsed DiffChunk objects.
        """
        if not patch:
            return []

        chunks: list[DiffChunk] = []
        current_chunk: DiffChunk | None = None
        
        # Line number tracking coordinates
        old_line_no = 0
        new_line_no = 0

        lines = patch.splitlines()
        for idx, line in enumerate(lines):
            # Check if this line is a hunk header
            match = self.HUNK_HEADER_RE.match(line)
            if match:
                # Save previous chunk if present
                if current_chunk:
                    chunks.append(current_chunk)

                # Parse hunk coordinate details
                old_start = int(match.group(1))
                old_lines = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_lines = int(match.group(4)) if match.group(4) else 1

                current_chunk = DiffChunk(
                    old_start=old_start,
                    old_lines=old_lines,
                    new_start=new_start,
                    new_lines=new_lines,
                    lines=[]
                )
                
                # Initialize line numbering markers
                old_line_no = old_start
                new_line_no = new_start
                continue

            # Process lines if inside an active hunk
            if current_chunk is not None:
                # Ignore metadata indicators
                if line.startswith("\\ No newline at end of file"):
                    continue

                if line.startswith("+"):
                    current_chunk.lines.append(
                        LineMapping(
                            line_type="addition",
                            content=line[1:],  # Remove prefix marker
                            old_line_no=None,
                            new_line_no=new_line_no
                        )
                    )
                    new_line_no += 1
                elif line.startswith("-"):
                    current_chunk.lines.append(
                        LineMapping(
                            line_type="deletion",
                            content=line[1:],
                            old_line_no=old_line_no,
                            new_line_no=None
                        )
                    )
                    old_line_no += 1
                else:
                    # Handles space context lines
                    content = line[1:] if line else ""
                    current_chunk.lines.append(
                        LineMapping(
                            line_type="context",
                            content=content,
                            old_line_no=old_line_no,
                            new_line_no=new_line_no
                        )
                    )
                    old_line_no += 1
                    new_line_no += 1

        # Append last remaining chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

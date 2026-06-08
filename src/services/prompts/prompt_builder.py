"""Prompt builder service formatting prompts from code chunks."""
import logging
from src.models.diff import ReviewableChunk

logger = logging.getLogger("ReviewEngine.Prompts")

class PromptBuilder:
    """Assembles prompt contexts for target reviewable code chunks."""

    def build_chunk_prompt(self, chunk: ReviewableChunk) -> str:
        """Assembles the user prompt, incorporating the diff hunk and instructions.

        Args:
            chunk: The reviewable code chunk.

        Returns:
            The compiled user prompt string.
        """
        logger.info(
            f"Building user prompt context for chunk {chunk.chunk_index} in file: {chunk.file_path}"
        )

        # Build clean prompt text with markers wrapping modified ranges
        user_prompt = (
            f"Analyze the following C# code modifications in the specified file path.\n\n"
            f"Target File Path: {chunk.file_path}\n"
            f"Target Line Coordinates containing additions/modifications: {chunk.target_lines}\n\n"
            f"Unified Diff Code Changes:\n"
            f"[PATCH_START]\n"
            f"{chunk.patch_content}\n"
            f"[PATCH_END]\n\n"
            f"Verify the code modifications against your system review instructions.\n"
            f"Return findings only for issues located precisely on one of the target line coordinates listed above."
        )

        return user_prompt

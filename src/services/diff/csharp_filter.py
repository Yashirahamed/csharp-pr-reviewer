"""C# file filter module applying project exclusions rules."""
import fnmatch
import logging
from typing import Any
from src.core.config import AppConfig

logger = logging.getLogger("ReviewEngine.Diff")

class CSharpFileFilter:
    """Filters changed files list, selecting C# files while skipping exclusions."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        
        # Base default exclusions compiled in settings
        self.default_exclusions = [
            "**/*.Designer.cs",
            "**/bin/**",
            "**/obj/**",
            "**/*.g.cs",
            "**/*.generated.cs",
            "**/Migrations/**",
            "**/AssemblyAttributes.cs"
        ]

    def should_review(self, file_path: str) -> bool:
        """Determines if a file is a target C# code source and is not excluded.

        Args:
            file_path: Relative repository file path string.

        Returns:
            True if the file matches review constraints.
        """
        # Ensure it is a C# file
        if not file_path.lower().endswith(".cs"):
            return False

        # Load user configuration exclusions combined with system defaults
        exclusions = set(self.config.exclude_paths + self.default_exclusions)

        for pattern in exclusions:
            # Match paths using standard glob pattern rules
            if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_path.split("/")[-1], pattern):
                logger.info(
                    f"File skipped by exclusion rules: {file_path}",
                    extra={"context": {"file_path": file_path, "matched_pattern": pattern}}
                )
                return False

        return True

    def filter_files(self, changed_files: list[dict[str, Any]] | list[Any]) -> list[Any]:
        """Filters a changed files metadata collection.

        Args:
            changed_files: Collection of changed file metadata dicts or ChangedFile schemas.

        Returns:
            List containing only target C# files for review.
        """
        filtered = []
        for f in changed_files:
            # Handle both raw API dict objects and Pydantic ChangedFile models
            filename = f.filename if hasattr(f, "filename") else f.get("filename", "")
            
            # Skip deleted files from review (only review additions/modifications)
            status = f.status if hasattr(f, "status") else f.get("status", "")
            if status == "deleted":
                logger.info(f"Skipping deleted file from review queue: {filename}")
                continue

            if self.should_review(filename):
                filtered.append(f)
        return filtered

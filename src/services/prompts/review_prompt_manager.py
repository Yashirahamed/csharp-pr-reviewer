"""System role instructions template manager for review agents."""
import logging

logger = logging.getLogger("ReviewEngine.Prompts")

class ReviewPromptManager:
    """Manages system instructions role definitions for specialized review categories."""

    def __init__(self) -> None:
        self._templates = {
            "Security": (
                "You are an expert DevSecOps Auditor and C# Security Engineer.\n"
                "Review C# code changes for vulnerabilities and insecure practices:\n"
                "1. SQL Injection: Check for string interpolation in raw database queries.\n"
                "2. Secrets: Check for hardcoded credentials, passwords, or tokens.\n"
                "3. Safe Parsing: Check for unsafe deserialization methods (TypeNameHandling).\n"
                "4. Validation: Verify inputs are validated and sanitized."
            ),
            "SOLID": (
                "You are a Principal Software Architect and C# SOLID Design Expert.\n"
                "Review C# code changes for violations of SOLID design principles:\n"
                "1. SRP: Ensure classes have a single focused responsibility.\n"
                "2. DIP: Dependencies must be interface-driven and injected via constructors.\n"
                "3. LSP: Verify derived classes do not break base type invariants ( NotImplementedException)."
            ),
            "Nullability": (
                "You are a Senior C# Developer specializing in null reference safety.\n"
                "Review C# code changes for null pointer hazards using .NET 8 rules:\n"
                "1. Nullable Reference Types: Enforce strict NRT rules for variables.\n"
                "2. Validation: Ensure method arguments check for null (throw ArgumentNullException).\n"
                "3. Pattern Matching: Prefer 'is null' or 'is not null' for comparisons."
            ),
            "AsyncAwait": (
                "You are a C# Concurrency and Systems Performance Engineer.\n"
                "Review C# code changes for async/await anti-patterns and thread hazards:\n"
                "1. Avoid sync-over-async calling (using .Result, .GetAwaiter().GetResult()).\n"
                "2. Avoid 'async void' methods except for event handlers.\n"
                "3. Ensure IDisposable resources in async scopes are disposed of using 'await using'."
            ),
            "CleanCode": (
                "You are a Software Craftsmanship Lead and Clean Code Assessor.\n"
                "Review C# code changes for general readability and code smells:\n"
                "1. Avoid deep loop nesting (deeper than 2 levels).\n"
                "2. Methods should be descriptive, short (under 30 lines), and focused.\n"
                "3. Verify capitalization rules (PascalCase for classes/methods, camelCase for local variables)."
            )
        }

    def get_system_instruction(self, category: str) -> str:
        """Retrieves system instructions for a specific review category.

        Args:
            category: The target category key (e.g. Security, SOLID).

        Returns:
            The formatted system instructions string.

        Raises:
            ValueError: If the category has no registered template.
        """
        if category not in self._templates:
            logger.error(f"System instruction template category not found: {category}")
            raise ValueError(f"Template category '{category}' is not supported.")
            
        logger.info(f"Loaded system instruction template for category: {category}")
        return (
            "Role: You are a senior code reviewer. Analyze modifications in C# files.\n"
            "Constraints:\n"
            "- Review ONLY lines located between the [PATCH_START] and [PATCH_END] markers.\n"
            "- Return findings only for issues located precisely on one of the target line numbers.\n"
            "- Provide suggestions as compilable C# 12 and .NET 8 code blocks.\n"
            "Format: Output your findings list in valid JSON matching the specified schema.\n\n"
            f"Review Instructions:\n{self._templates[category]}"
        )

    def get_all_categories(self) -> list[str]:
        """Returns the list of supported review categories."""
        return list(self._templates.keys())

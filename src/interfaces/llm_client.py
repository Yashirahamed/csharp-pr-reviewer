"""LLM Client interface contract for model interactions."""
from abc import ABC, abstractmethod
from typing import Any

class ILLMClient(ABC):
    """Abstract interface defining required Gemini API actions."""

    @abstractmethod
    async def generate_structured_content(
        self, 
        prompt: str, 
        system_instruction: str | None = None,
        response_schema: dict[str, Any] | None = None
    ) -> str:
        """Sends structured prompts to the Gemini API and returns a raw JSON response.

        Args:
            prompt: User-provided prompt payload (containing diff and surrounding context).
            system_instruction: Role configuration guidelines for the target agent.
            response_schema: Optional output validation schema dict.

        Returns:
            A raw JSON-formatted string response containing model outputs.

        Raises:
            APIException: If API connections time out or exceed rate limits.
        """
        pass

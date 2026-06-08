"""Google Gemini API REST client implementation."""
import logging
import time
from typing import Any
import requests
from src.interfaces.llm_client import ILLMClient
from src.core.config import AppConfig
from src.core.exceptions import APIException
from src.models.gemini_request import GeminiRequest, ContentItem, TextPart, SystemInstruction, GenerationConfig
from src.models.gemini_response import GeminiResponse

logger = logging.getLogger("ReviewEngine.Gemini")

class GeminiClient(ILLMClient):
    """Client for executing content generation requests via the Gemini REST API."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })

    async def generate_structured_content(
        self, 
        prompt: str, 
        system_instruction: str | None = None,
        response_schema: dict[str, Any] | None = None
    ) -> str:
        """Sends structured prompts to the Gemini API and returns a raw JSON response.

        Args:
            prompt: User-provided prompt payload.
            system_instruction: Optional system instruction role guidelines.
            response_schema: Optional strict validation schema dict.

        Returns:
            The raw JSON string response containing the model's findings.

        Raises:
            APIException: If API requests fail, time out, or exceed rate limits.
        """
        # Construct parameters matching the Gemini REST API JSON structure
        content_item = ContentItem(
            role="user",
            parts=[TextPart(text=prompt)]
        )
        
        sys_inst = None
        if system_instruction:
            sys_inst = SystemInstruction(
                parts=[TextPart(text=system_instruction)]
            )
            
        gen_config = GenerationConfig(
            responseMimeType="application/json",
            responseSchema=response_schema,
            temperature=self.config.gemini_temperature
        )

        request_payload = GeminiRequest(
            contents=[content_item],
            systemInstruction=sys_inst,
            generationConfig=gen_config
        )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.gemini_model_name}:generateContent"
            f"?key={self.config.gemini_api_key}"
        )

        # Execution retry variables
        max_attempts = 3
        backoff_delay = 1.5
        timeout_seconds = 30.0

        logger.info(
            "Sending generateContent request to Gemini API.",
            extra={
                "context": {
                    "model": self.config.gemini_model_name,
                    "temperature": self.config.gemini_temperature,
                    "has_schema": response_schema is not None
                }
            }
        )

        for attempt in range(1, max_attempts + 1):
            try:
                response = self.session.post(
                    url,
                    json=request_payload.model_dump(exclude_none=True),
                    timeout=timeout_seconds
                )
                
                # Check for rate limiting status (429) or temporary server errors (503)
                if response.status_code in (429, 503):
                    if attempt == max_attempts:
                        raise APIException(
                            message=f"Gemini API returned persistent error status: {response.status_code}",
                            status_code=response.status_code,
                            details=response.text
                        )
                    
                    delay = backoff_delay * (2 ** (attempt - 1))
                    logger.warning(
                        f"Gemini API rate limited or offline ({response.status_code}). "
                        f"Retrying in {delay:.2f} seconds (Attempt {attempt}/{max_attempts}).",
                        extra={"context": {"status_code": response.status_code, "retry_attempt": attempt}}
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                data = response.json()
                
                # Validate the response payload using GeminiResponse schema
                gemini_res = GeminiResponse(**data)
                
                # Track token usage statistics
                logger.info(
                    "Gemini API request succeeded.",
                    extra={
                        "context": {
                            "prompt_tokens": gemini_res.usageMetadata.promptTokenCount,
                            "candidates_tokens": gemini_res.usageMetadata.candidatesTokenCount,
                            "total_tokens": gemini_res.usageMetadata.totalTokenCount
                        }
                    }
                )

                if not gemini_res.candidates:
                    raise APIException(
                        message="Gemini API returned an empty list of candidate responses."
                    )

                # Extract and return raw JSON content text
                candidate = gemini_res.candidates[0]
                if not candidate.content.parts:
                    raise APIException(
                        message="Gemini API response candidate content has no text parts."
                    )

                return candidate.content.parts[0].text

            except requests.exceptions.Timeout as timeout_err:
                if attempt == max_attempts:
                    raise APIException(
                        message=f"Gemini API request timed out after {timeout_seconds}s.",
                        details=str(timeout_err)
                    )
                logger.warning(
                    f"Gemini API request timed out. Retrying attempt {attempt + 1}..."
                )
                time.sleep(1.0)
            except requests.exceptions.RequestException as req_err:
                status_code = req_err.response.status_code if req_err.response else None
                raise APIException(
                    message="Failed to connect to the Gemini API REST endpoint.",
                    status_code=status_code,
                    details=str(req_err)
                )

        raise APIException(message="Execution exhausted all retry attempts without succeeding.")

    def close(self) -> None:
        """Closes the HTTP connections session."""
        self.session.close()

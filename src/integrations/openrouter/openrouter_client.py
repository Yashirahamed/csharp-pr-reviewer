"""OpenRouter API client implementation supporting dynamic fallback routing."""
import logging
import requests
from typing import Any
from src.interfaces.llm_client import ILLMClient
from src.core.config import AppConfig
from src.core.exceptions import APIException

logger = logging.getLogger("ReviewEngine.OpenRouter")

class OpenRouterClient(ILLMClient):
    """Client for executing content generation requests via OpenRouter Chat Completions API."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session = requests.Session()
        
        # Configure standard headers for OpenRouter
        self.session.headers.update({
            "Authorization": f"Bearer {self.config.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": f"https://github.com/{self.config.github_repository}" if self.config.github_repository else "https://github.com/unknown/repo",
            "X-Title": "AI-GitHub-PR-Reviewer-Engine"
        })

    async def generate_structured_content(
        self, 
        prompt: str, 
        system_instruction: str | None = None,
        response_schema: dict[str, Any] | None = None
    ) -> str:
        """Sends structured prompts to OpenRouter and returns content, falling back on transient errors."""
        primary_model = self.config.primary_model
        fallback_model = self.config.fallback_model
        
        try:
            # Attempt to request using primary model
            return await self._call_api_with_model(
                model=primary_model,
                prompt=prompt,
                system_instruction=system_instruction,
                response_schema=response_schema
            )
        except (requests.exceptions.Timeout, APIException) as exc:
            # Evaluate if the failure is a transient, retryable error
            is_retryable = False
            error_details = str(exc)
            
            if isinstance(exc, requests.exceptions.Timeout):
                is_retryable = True
            elif isinstance(exc, APIException):
                # 408 (Timeout), 429 (Rate Limit), 503 (Offline), or >=500 (Server errors)
                if exc.status_code in (408, 429, 503) or (exc.status_code and exc.status_code >= 500):
                    is_retryable = True
            
            if not is_retryable:
                # Propagate immediately if error is non-retryable
                logger.error(f"OpenRouter: Non-retryable API error with primary model: {exc}")
                raise exc
                
            logger.warning(
                f"OpenRouter: Primary model '{primary_model}' failed with retryable error: {error_details}. "
                f"Switching to fallback model '{fallback_model}'...",
                extra={"context": {"primary_model": primary_model, "fallback_model": fallback_model}}
            )
            
            # Retry request using the fallback model
            return await self._call_api_with_model(
                model=fallback_model,
                prompt=prompt,
                system_instruction=system_instruction,
                response_schema=response_schema
            )

    async def _call_api_with_model(
        self,
        model: str,
        prompt: str,
        system_instruction: str | None = None,
        response_schema: dict[str, Any] | None = None
    ) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        timeout_seconds = 60.0
        
        # Build messages structure
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        # Build strict JSON schema configuration
        response_format = {"type": "json_object"}
        if response_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "findings_report",
                    "strict": True,
                    "schema": response_schema
                }
            }
            
        payload = {
            "model": model,
            "messages": messages,
            "response_format": response_format,
            "temperature": self.config.gemini_temperature,
            "max_tokens": 800
        }
        
        logger.info(
            f"Sending chat completion request to OpenRouter API.",
            extra={
                "context": {
                    "model": model,
                    "has_schema": response_schema is not None
                }
            }
        )
        
        try:
            response = self.session.post(url, json=payload, timeout=timeout_seconds)
            
            # Raise exception for HTTP error statuses
            if response.status_code != 200:
                raise APIException(
                    message=f"OpenRouter API returned error status: {response.status_code}",
                    status_code=response.status_code,
                    details=response.text
                )
                
            data = response.json()
            
            # Check for error structures inside OK responses
            if "error" in data:
                error_info = data["error"]
                error_msg = error_info.get("message", "Unknown provider error")
                error_code = error_info.get("code", 500)
                raise APIException(
                    message=f"OpenRouter provider returned error: {error_msg}",
                    status_code=error_code,
                    details=str(error_info)
                )
                
            choices = data.get("choices")
            if not choices:
                raise APIException(message="OpenRouter API returned an empty list of choices.")
                
            message_content = choices[0].get("message", {}).get("content")
            if message_content is None:
                raise APIException(message="OpenRouter choice response contains no message content.")
                
            return message_content
            
        except requests.exceptions.Timeout as timeout_err:
            raise APIException(
                message=f"OpenRouter API request timed out after {timeout_seconds}s for model {model}.",
                details=str(timeout_err)
            )
        except requests.exceptions.RequestException as req_err:
            status_code = req_err.response.status_code if req_err.response else None
            raise APIException(
                message="Failed to connect to the OpenRouter API REST endpoint.",
                status_code=status_code,
                details=str(req_err)
            )

    def close(self) -> None:
        """Closes connection session."""
        self.session.close()

# Create new file: src/integrations/llm_router.py

import logging
from src.interfaces.llm_client import ILLMClient
from src.core.config import AppConfig
from src.integrations.gemini.gemini_client import GeminiClient
from src.integrations.openrouter.openrouter_client import OpenRouterClient

logger = logging.getLogger("ReviewEngine.LLMRouter")

class LLMRouter(ILLMClient):
    """Routes between primary (Gemini) and fallback (OpenRouter) providers"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.primary = GeminiClient(config)
        self.fallback = OpenRouterClient(config)
    
    async def generate_structured_content(
        self, 
        prompt: str, 
        system_instruction: str | None = None,
        response_schema: dict | None = None
    ) -> str:
        """Try Gemini first, fall back to OpenRouter if it fails"""
        
        # Try primary (Gemini)
        try:
            logger.info("Attempting with Gemini API (primary)...")
            result = await self.primary.generate_structured_content(
                prompt, system_instruction, response_schema
            )
            logger.info("✓ Gemini API succeeded")
            return result
        
        except Exception as gemini_error:
            logger.warning(f"✗ Gemini API failed: {str(gemini_error)}")
            logger.info("Falling back to OpenRouter API...")
            
            # Try fallback (OpenRouter)
            try:
                result = await self.fallback.generate_structured_content(
                    prompt, system_instruction, response_schema
                )
                logger.info("✓ OpenRouter API succeeded (fallback)")
                return result
            
            except Exception as openrouter_error:
                logger.critical(f"✗ Both APIs failed - Gemini: {gemini_error}, OpenRouter: {openrouter_error}")
                raise
    
    def close(self):
        """Clean up both clients"""
        if hasattr(self.primary, "close"):
            self.primary.close()
        if hasattr(self.fallback, "close"):
            self.fallback.close()
"""Verification script for Gemini integrations and prompt builder services."""
import logging
from src.core.config import AppConfig
from src.core.logging import configure_logging
from src.models.diff import ReviewableChunk
from src.integrations.gemini.gemini_client import GeminiClient
from src.services.prompts.prompt_builder import PromptBuilder
from src.services.prompts.review_prompt_manager import ReviewPromptManager

configure_logging("INFO")
logger = logging.getLogger("VerifyGemini")

def run_verification() -> None:
    logger.info("Initializing configuration parameters.")
    config = AppConfig(
        GEMINI_API_KEY="mock_key_12345",
        GEMINI_MODEL_NAME="gemini-1.5-flash",
        GEMINI_TEMPERATURE=0.2
    )

    logger.info("Instantiating GeminiClient and Prompt Services.")
    client = GeminiClient(config)
    builder = PromptBuilder()
    manager = ReviewPromptManager()

    logger.info("--- Testing PromptBuilder ---")
    mock_chunk = ReviewableChunk(
        file_path="src/Core/Services/Sync.cs",
        chunk_index=0,
        patch_content="+    public async Task RunAsync() {\n+        var x = await FetchAsync();\n     }",
        target_lines=[10, 11]
    )
    user_prompt = builder.build_chunk_prompt(mock_chunk)
    logger.info(f"User Prompt:\n{user_prompt}")

    logger.info("--- Testing ReviewPromptManager ---")
    categories = manager.get_all_categories()
    logger.info(f"Registered categories count: {len(categories)}")
    for cat in categories:
        logger.info(f"Loading system instruction for category: {cat}")
        system_inst = manager.get_system_instruction(cat)
        # Display excerpt of instructions
        logger.info(f" -> Instructions (Excerpt): {system_inst.splitlines()[10]}")

    client.close()
    logger.info("Verification completed successfully.")

if __name__ == "__main__":
    run_verification()

"""Application entry point and bootstrapper for the Pull Request Review System."""
import asyncio
import logging
import os
import sys

# Core Configuration & Logging
from src.core.config import AppConfig
from src.core.container import Container
from src.core.logging import configure_logging
from src.core.exceptions import ReviewEngineException, ConfigurationException, APIException

# Interfaces
from src.interfaces.github_client import IGitHubClient
from src.interfaces.llm_client import ILLMClient
from src.interfaces.reviewer import IReviewer

# Domain Models
from src.models.review import Review

# Integrations
from src.integrations.github.github_client import GitHubClient
from src.integrations.gemini.gemini_client import GeminiClient

# Services
from src.services.diff.csharp_filter import CSharpFileFilter
from src.services.diff.diff_parser import DiffParser
from src.services.diff.diff_extractor import DiffExtractor
from src.services.diff.line_mapper import LineMapper
from src.services.prompts.prompt_builder import PromptBuilder
from src.services.prompts.review_prompt_manager import ReviewPromptManager
from src.services.review.review_validator import ReviewValidator
from src.services.review.severity_engine import SeverityEngine
from src.services.review.finding_filter import FindingFilter
from src.services.publishing.review_formatter import ReviewFormatter
from src.services.publishing.review_summary_generator import ReviewSummaryGenerator
from src.services.publishing.publish_manager import PublishManager

# Agent Orchestration
from src.agent.review_agent import ReviewAgent

# Logger setup
logger = logging.getLogger("ReviewEngine")


async def bootstrap() -> None:
    """Configures the container and executes the production PR review orchestrator workflow."""
    # 1. Load Configurations from environment variables
    config = AppConfig()
    
    # 2. Determine logging outputs (stdout + file if in GitHub Actions)
    log_file = None
    if os.environ.get("GITHUB_ACTIONS") == "true":
        log_file = "/tmp/reviewer-state/run.log"
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
    configure_logging(level=config.log_level, log_file=log_file)
    logger.info("Initializing production review engine configuration and logging pipeline.")

    # 3. Enforce validation check and fail fast if parameters are missing
    config.validate_required_credentials()

    # 4. Setup dependency injection registrations
    container = Container()
    container.reset()
    container.register_singleton(AppConfig, config)
    
    # Register processing, prompt, and validation services
    container.register_singleton(CSharpFileFilter, CSharpFileFilter(config))
    parser = DiffParser()
    container.register_singleton(DiffParser, parser)
    container.register_singleton(DiffExtractor, DiffExtractor(parser))
    container.register_singleton(LineMapper, LineMapper())
    
    container.register_singleton(PromptBuilder, PromptBuilder())
    container.register_singleton(ReviewPromptManager, ReviewPromptManager())
    
    container.register_singleton(ReviewValidator, ReviewValidator())
    container.register_singleton(SeverityEngine, SeverityEngine(config))
    container.register_singleton(FindingFilter, FindingFilter())
    
    # Register publishing formatter/generator
    formatter = ReviewFormatter()
    summary_generator = ReviewSummaryGenerator(formatter)
    container.register_singleton(ReviewFormatter, formatter)
    container.register_singleton(ReviewSummaryGenerator, summary_generator)

    # Register concrete clients for remote executions
    container.register_singleton(IGitHubClient, GitHubClient(config))
    
    from src.integrations.llm_router import LLMRouter
    container.register_singleton(ILLMClient, LLMRouter(config))
    
    # Register remaining orchestrator services
    container.register_factory(
        PublishManager,
        lambda: PublishManager(
            github_client=container.resolve(IGitHubClient),
            formatter=container.resolve(ReviewFormatter),
            summary_generator=container.resolve(ReviewSummaryGenerator),
            config=config
        )
    )
    
    container.register_factory(
        IReviewer,
        lambda: ReviewAgent(
            publish_manager=container.resolve(PublishManager),
            github_client=container.resolve(IGitHubClient),
            llm_client=container.resolve(ILLMClient),
            file_filter=container.resolve(CSharpFileFilter),
            diff_extractor=container.resolve(DiffExtractor),
            line_mapper=container.resolve(LineMapper),
            prompt_builder=container.resolve(PromptBuilder),
            prompt_manager=container.resolve(ReviewPromptManager),
            validator=container.resolve(ReviewValidator),
            severity_engine=container.resolve(SeverityEngine),
            finding_filter=container.resolve(FindingFilter)
        )
    )

    logger.info("Production services configured in Container.")

    # 5. Execute Review Loop
    target_pr = config.github_pr_number
    reviewer = container.resolve(IReviewer)
    
    logger.info(f"Starting production review loop for PR #{target_pr}...")
    review_output = await reviewer.review_pull_request(target_pr)
    
    # Report metrics
    logger.info(
        "Code review execution completed successfully.",
        extra={
            "context": {
                "pr_number": target_pr,
                "findings_count": len(review_output.findings),
                "verdict": review_output.verdict,
                "stats": review_output.stats
            }
        }
    )

    # 6. Shutdown Sequence
    logger.info("Executing shutdown sequence and releasing resources.")
    github_client = container.resolve(IGitHubClient)
    if hasattr(github_client, "close"):
        github_client.close()
        logger.info("Closed GitHubClient session connections.")
        
    llm_client = container.resolve(ILLMClient)
    if hasattr(llm_client, "close"):
        llm_client.close()
        logger.info("Closed LLMClient session connections.")


def main() -> None:
    """Application entry point wrapper handling final process exits."""
    try:
        asyncio.run(bootstrap())
        sys.exit(0)
    except ConfigurationException as config_err:
        print(f"FATAL Configuration Error: {config_err}", file=sys.stderr)
        sys.exit(2)
    except APIException as api_err:
        print(f"FATAL API Error: {api_err}", file=sys.stderr)
        sys.exit(3)
    except ReviewEngineException as engine_err:
        print(f"FATAL Review Engine Error: {engine_err}", file=sys.stderr)
        sys.exit(4)
    except Exception as exc:
        print(f"FATAL Unhandled System Failure: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

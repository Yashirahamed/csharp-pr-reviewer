"""Application entry point and bootstrapper for the Pull Request Review System."""
import asyncio
import logging
import os
import sys
from typing import Any

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
from src.models.pull_request import PullRequest
from src.models.findings import Finding
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


class MockGitHubClient(IGitHubClient):
    """Mock implementation of the GitHub REST API client for local simulation."""

    async def get_pull_request(self, pr_number: int) -> PullRequest:
        logger.info(
            "MockGitHubClient: Fetching Pull Request metadata.",
            extra={"context": {"pr_number": pr_number}}
        )
        return PullRequest(
            pr_number=pr_number,
            title="Refactor Data Sync Service to use Async Streams",
            description="Replaces batch streams with Async Enumerables.",
            state="open",
            is_draft=False,
            head_sha="a1b2c3d4e5f67890a1b2c3d4e5f67890abcdef12",
            base_sha="f6e5d4c3b2a10987f6e5d4c3b2a10987abcdef12",
            html_url=f"https://github.com/AcmeOrg/enterprise-backend/pull/{pr_number}"
        )

    async def get_changed_files(self, pr_number: int) -> list[dict[str, Any]]:
        logger.info(
            "MockGitHubClient: Fetching changed files list.",
            extra={"context": {"pr_number": pr_number}}
        )
        return [
            {
                "filename": "src/Core/Services/Sync.cs",
                "status": "modified",
                "additions": 14,
                "deletions": 2,
                "changes": 16,
                "patch": (
                    "@@ -10,3 +10,4 @@ public class Sync {\n"
                    "+    public async Task RunAsync() {\n"
                    "+        var x = await FetchAsync();\n"
                    "     }\n"
                )
            }
        ]

    async def get_raw_diff(self, pr_number: int) -> str:
        logger.info(
            "MockGitHubClient: Fetching raw unified diff stream.",
            extra={"context": {"pr_number": pr_number}}
        )
        return (
            "@@ -10,3 +10,4 @@ public class Sync {\n"
            "+    public async Task RunAsync() {\n"
            "+        var x = await FetchAsync();\n"
            "     }\n"
        )

    async def submit_review(self, pr_number: int, review: Review) -> None:
        logger.info(
            "MockGitHubClient: Submitting review and comments to PR.",
            extra={
                "context": {
                    "pr_number": pr_number,
                    "verdict": review.verdict,
                    "comments_count": len(review.findings)
                }
            }
        )

    async def get_review_comments(self, pr_number: int) -> list[dict[str, Any]]:
        logger.info(
            "MockGitHubClient: Fetching existing review comments.",
            extra={"context": {"pr_number": pr_number}}
        )
        return []


class MockLLMClient(ILLMClient):
    """Mock implementation of the Gemini API client for local simulation."""

    async def generate_structured_content(
        self, 
        prompt: str, 
        system_instruction: str | None = None,
        response_schema: dict[str, Any] | None = None
    ) -> str:
        logger.info("MockLLMClient: Sending prompts and schema options to Gemini API.")
        return (
            "{\n"
            "  \"findings\": [\n"
            "    {\n"
            "      \"file_path\": \"src/Core/Services/Sync.cs\",\n"
            "      \"line_number\": 11,\n"
            "      \"rule_id\": \"CS-PERF-01\",\n"
            "      \"category\": \"Performance\",\n"
            "      \"severity\": \"High\",\n"
            "      \"title\": \"Avoid blocking async call\",\n"
            "      \"description\": \"Ensure asynchronous calls do not block execution threads.\",\n"
            "      \"suggestion\": \"var x = await FetchAsync();\",\n"
            "      \"confidence_score\": 0.95\n"
            "    }\n"
            "  ]\n"
            "}"
        )


async def bootstrap() -> None:
    """Configures the container and executes the PR review orchestrator workflow."""
    # 1. Load Configurations from environment variables
    config = AppConfig()
    
    # 2. Determine logging outputs (stdout + file if in GitHub Actions)
    log_file = None
    if os.environ.get("GITHUB_ACTIONS") == "true":
        log_file = "/tmp/reviewer-state/run.log"
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
    configure_logging(level=config.log_level, log_file=log_file)
    logger.info("Initializing system configurations and logging pipeline.")

    # 3. Setup dependency injection registrations
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

    # 4. Check if simulation mode is active
    is_simulation = not (config.github_token and config.github_repository and config.gemini_api_key)
    
    if is_simulation:
        logger.warning(
            "Running in LOCAL SIMULATION mode. Required environment parameters not set.",
            extra={
                "context": {
                    "GITHUB_TOKEN": "SET" if config.github_token else "NOT_SET",
                    "GITHUB_REPOSITORY": "SET" if config.github_repository else "NOT_SET",
                    "GEMINI_API_KEY": "SET" if config.gemini_api_key else "NOT_SET"
                }
            }
        )
        container.register_singleton(IGitHubClient, MockGitHubClient())
        container.register_singleton(ILLMClient, MockLLMClient())
        target_pr = config.github_pr_number if config.github_pr_number > 0 else 421
    else:
        # Enforce validation checks for production runs
        config.validate_required_credentials()
        container.register_singleton(IGitHubClient, GitHubClient(config))
        container.register_singleton(ILLMClient, GeminiClient(config))
        target_pr = config.github_pr_number

    # 5. Register remaining orchestrator services
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

    logger.info("Service registrations completed inside Container.")

    # 6. Execute Review Loop
    reviewer = container.resolve(IReviewer)
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

    # 7. Shutdown Sequence
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

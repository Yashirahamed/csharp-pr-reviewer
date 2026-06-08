"""Verification script for GitHub integrations."""
import logging
from src.core.config import AppConfig
from src.core.logging import configure_logging
from src.integrations.github.github_client import GitHubClient

configure_logging("INFO")
logger = logging.getLogger("VerifyGitHub")

def run_verification() -> None:
    logger.info("Initializing configuration parameters.")
    config = AppConfig(
        GITHUB_TOKEN="mock_token_12345",
        GITHUB_REPOSITORY="AcmeOrg/enterprise-backend",
        GITHUB_PR_NUMBER=421
    )
    
    logger.info("Instantiating GitHubClient facade.")
    client = GitHubClient(config)
    
    logger.info("GitHubClient components initialized successfully:")
    logger.info(f" - Owner: {client.reader.owner}")
    logger.info(f" - Repository: {client.reader.repo}")
    logger.info(f" - Token in Headers: {'Masked' if 'Authorization' in client.session.headers else 'Missing'}")
    
    client.close()
    logger.info("Verification completed successfully.")

if __name__ == "__main__":
    run_verification()

from src.core.config import AppConfig
from src.services.review.severity_engine import SeverityEngine

def test_severity_engine_creation():
    config = AppConfig(
        GITHUB_TOKEN="test",
        GITHUB_REPOSITORY="repo",
        GITHUB_PR_NUMBER=1,
        GEMINI_API_KEY="key"
    )

    engine = SeverityEngine(config)
    assert engine is not None
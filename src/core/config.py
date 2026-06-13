"""Configuration module settings loader."""
import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.core.exceptions import ConfigurationException


class AppConfig(BaseSettings):
    """Application configuration container parsed from environment variables."""
    
    # Read environment variables directly or fall back to .env files
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix=""
    )

    # GitHub API Configurations
    github_token: str = Field(default="", validation_alias="GITHUB_TOKEN")
    github_repository: str = Field(default="", validation_alias="GITHUB_REPOSITORY")
    github_pr_number: int = Field(default=0, validation_alias="GITHUB_PR_NUMBER")

    # Gemini API Configurations
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")

    gemini_model_name: str = Field(
        default="gemini-2.5-flash",
        validation_alias="GEMINI_MODEL_NAME"
    )

    gemini_temperature: float = Field(default=0.1, ge=0.0, le=1.0)

    # LLM Provider Configurations
    llm_provider: str = Field(default="gemini", validation_alias="LLM_PROVIDER")
    openrouter_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    primary_model: str = Field(default="google/gemini-2.5-flash", validation_alias="PRIMARY_MODEL")
    fallback_model: str = Field(default="deepseek/deepseek-chat", validation_alias="FALLBACK_MODEL")

    # Review Settings
    exclude_paths: list[str] = Field(default=["**/bin/**", "**/obj/**", "**/*.g.cs",".history/**"])
    max_comments_per_pr: int = Field(default=30, ge=1, le=100)
    log_level: str = Field(default="INFO")
    dry_run: bool = Field(default=False, validation_alias="DRY_RUN")

    @field_validator("github_pr_number")
    @classmethod
    def validate_pr_number(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Pull Request number cannot be negative.")
        return v

    def validate_required_credentials(self) -> None:
        """Validates that all credentials required for remote executions are set."""
        missing = []
        if not self.github_token:
            missing.append("GITHUB_TOKEN")
        if not self.github_repository:
            missing.append("GITHUB_REPOSITORY")
        if self.github_pr_number <= 0:
            missing.append("GITHUB_PR_NUMBER")
        if self.llm_provider.lower() == "gemini":
            if not self.gemini_api_key:
                missing.append("GEMINI_API_KEY")
        elif self.llm_provider.lower() == "openrouter":
            if not self.openrouter_api_key:
                missing.append("OPENROUTER_API_KEY")

        if missing:
            raise ConfigurationException(
                message="Missing required environment variables for execution.",
                details=f"Required fields not set: {', '.join(missing)}"
            )

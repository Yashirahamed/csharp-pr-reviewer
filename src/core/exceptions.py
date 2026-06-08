"""Custom exceptions framework for the Pull Request Review system."""

class ReviewEngineException(Exception):
    """Base exception for all system-related errors."""
    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ConfigurationException(ReviewEngineException):
    """Raised when configuration variables or settings files fail to load."""
    pass


class APIException(ReviewEngineException):
    """Raised when external API integration requests (GitHub, Gemini) fail."""
    def __init__(self, message: str, status_code: int | None = None, details: str | None = None) -> None:
        super().__init__(message, details)
        self.status_code = status_code


class ValidationException(ReviewEngineException):
    """Raised when data contracts, schemas, or line mappings validation fails."""
    pass

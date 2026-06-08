"""Structured JSON logging configuration."""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

class JsonFormatter(logging.Formatter):
    """Formats log records as structured JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        # Build core log structure
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
        }

        # Include traceback details if an exception is logged
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include custom extra context if provided
        if hasattr(record, "context") and isinstance(record.context, dict):
            # Mask sensitive values in context
            masked_context = self._mask_sensitive_data(record.context)
            log_data["context"] = masked_context

        return json.dumps(log_data)

    def _mask_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Masks tokens, secrets, and authorization parameters."""
        sensitive_keys = {"token", "key", "authorization", "secret", "password"}
        masked = {}
        for k, v in data.items():
            if any(s in k.lower() for s in sensitive_keys):
                masked[k] = "********"
            elif isinstance(v, dict):
                masked[k] = self._mask_sensitive_data(v)
            else:
                masked[k] = v
        return masked


def configure_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Configures the root logging handler to output JSON to standard out and optionally a file."""
    root_logger = logging.getLogger()
    
    # Convert string level to logging level code
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Clear existing handlers
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Configure stdout stream handler with JsonFormatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    # Configure file handler if log_file is specified
    if log_file:
        import os
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(file_handler)

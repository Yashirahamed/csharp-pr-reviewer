"""Pydantic data models representing Gemini API requests."""
from typing import Any
from pydantic import BaseModel, Field

class TextPart(BaseModel):
    """A single text part within content structures."""
    text: str = Field(..., description="The textual prompt or code content.")


class ContentItem(BaseModel):
    """An item representing content details sent to the model."""
    role: str = Field(default="user", description="The role context: user or model.")
    parts: list[TextPart] = Field(..., description="Array of text parts.")


class SystemInstruction(BaseModel):
    """System instructions configuring the model's role."""
    parts: list[TextPart] = Field(..., description="System instructions role content.")


class GenerationConfig(BaseModel):
    """Model execution configuration options."""
    responseMimeType: str = Field(default="application/json", description="Target MIME type format.")
    responseSchema: dict[str, Any] | None = Field(default=None, description="Optional strict validation schema dict.")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0, description="Model temperature option.")


class GeminiRequest(BaseModel):
    """Request payload parameters for Gemini content generation API."""
    contents: list[ContentItem] = Field(..., description="Input query prompts and contexts.")
    systemInstruction: SystemInstruction | None = Field(default=None, description="Optional system role guidelines.")
    generationConfig: GenerationConfig = Field(default_factory=GenerationConfig, description="Model generation config parameters.")

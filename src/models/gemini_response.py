"""Pydantic data models representing Gemini API responses."""
from pydantic import BaseModel, Field

class ResponsePart(BaseModel):
    """Text output part in model responses."""
    text: str = Field(..., description="The model's textual response output.")


class ResponseContent(BaseModel):
    """The generated content within a response candidate."""
    parts: list[ResponsePart] = Field(..., description="Generated response parts.")
    role: str = Field(default="model", description="The role structure: model.")


class Candidate(BaseModel):
    """A single candidate response returned by the model."""
    content: ResponseContent = Field(..., description="The content details.")
    finishReason: str = Field(default="STOP", description="The reason for completion (e.g. STOP).")


class UsageMetadata(BaseModel):
    """Token consumption statistics for the request."""
    promptTokenCount: int = Field(default=0, ge=0, description="Tokens used in the input prompt.")
    candidatesTokenCount: int = Field(default=0, ge=0, description="Tokens used in the output response.")
    totalTokenCount: int = Field(default=0, ge=0, description="Total tokens consumed.")


class GeminiResponse(BaseModel):
    """The root response object returned by the Gemini API."""
    candidates: list[Candidate] = Field(..., description="Generated candidate options.")
    usageMetadata: UsageMetadata = Field(default_factory=UsageMetadata, description="Usage statistics.")

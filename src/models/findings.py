"""Review finding domain data model."""
from pydantic import BaseModel, Field, field_validator

class Finding(BaseModel):
    """Data model representing a single code review finding and suggestion."""
    file_path: str = Field(..., description="Target file path.")
    line_number: int = Field(..., ge=1, description="Absolute line number in the new version of the file.")
    rule_id: str = Field(..., description="Unique alphanumeric identifier of the violated rule (e.g. CS-SEC-01).")
    category: str = Field(..., description="Category of the finding (e.g. Security, Performance).")
    severity: str = Field(..., description="Assigned severity level (e.g. Critical, Major, Minor, Info).")
    title: str = Field(..., min_length=1, max_length=128, description="A brief summary title of the issue.")
    description: str = Field(..., description="Detailed explanation of the issue.")
    suggestion: str = Field(default="", description="A suggested C# code block containing the recommended solution.")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="The model's confidence rating between 0.0 and 1.0.")

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        # Normalize casing and map common variations
        v_norm = v.strip().title()
        mapping = {
            "Error": "High",
            "Major": "High",
            "Minor": "Medium",
            "Warning": "Medium",
            "Information": "Info",
            "Informational": "Info"
        }
        v_resolved = mapping.get(v_norm, v_norm)

        valid_severities = {"Critical", "High", "Medium", "Low", "Info"}
        if v_resolved not in valid_severities:
            raise ValueError(f"Severity must be one of: {', '.join(valid_severities)}")
        return v_resolved

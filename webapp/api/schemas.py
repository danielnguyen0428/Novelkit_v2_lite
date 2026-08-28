"""Pydantic request/response models for the NovelKit web API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from provider.llm_client import validate_llm_base_url


class CreateNovelRequest(BaseModel):
    name: str = Field(..., description="Workspace slug: [a-z0-9_-], max 64 chars")
    fields: dict[str, Any] = Field(
        default_factory=dict,
        description="PROJECT_DNA form values keyed by schema field id",
    )


class PlanNextRequest(BaseModel):
    claim: bool = False


class RecordResultRequest(BaseModel):
    task_key: str
    result: str = Field(..., description="done|soft_fail|hard_fail|blocked|skipped")
    score: Optional[float] = Field(None, ge=0, le=100)


class SyncRequest(BaseModel):
    chapter: int = Field(..., ge=1)


class SteerRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Realtime steer / intervention text")


class CompassMigrateRequest(BaseModel):
    current_chapter: int = Field(0, ge=0, description="Chapters already written (become a done arc)")
    target_chapters: int = Field(..., ge=1, description="Target novel length for the compass scale estimate")


class AnalyzeRequest(BaseModel):
    text: str
    genre: Optional[str] = None
    secondary_genre: Optional[str] = None


class ProviderSettingsRequest(BaseModel):
    provider: Optional[str] = Field(
        None, description="Provider preset identifier; Lite uses 'other'"
    )
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = Field(
        None, description="OpenAI-compatible API key; '' clears it, null leaves it"
    )

    @field_validator("base_url")
    @classmethod
    def validate_secure_base_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return value
        return validate_llm_base_url(value)


class ProviderTestRequest(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = Field(
        None, description="Optional probe key; omit to use the saved server key"
    )

    @field_validator("base_url")
    @classmethod
    def validate_secure_base_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return value
        return validate_llm_base_url(value)


class RunRequest(BaseModel):
    max_steps: int = Field(12, ge=1, le=60)
    # When set, run until this many chapters finish (chapter mode); max_steps
    # then acts only as a derived safety ceiling. Left null → legacy step mode.
    chapters: Optional[int] = Field(None, ge=1, le=20)


class DnaGenerateRequest(BaseModel):
    brief: str = Field(..., description="Free-text idea/premise for the novel")
    genre: Optional[str] = Field(None, description="Optional genre slug to anchor")
    title: Optional[str] = Field(None, description="Optional working title")
    output_language: Optional[str] = Field(None, description="Prose output language code")
    output_language_custom: Optional[str] = Field(
        None, description="Custom prose language label when output_language=custom"
    )


class MessageResponse(BaseModel):
    ok: bool = True
    detail: Optional[str] = None
    data: Optional[Any] = None


class WriteArtifactRequest(BaseModel):
    path: str
    text: str


class RegenerateDocRequest(BaseModel):
    path: str

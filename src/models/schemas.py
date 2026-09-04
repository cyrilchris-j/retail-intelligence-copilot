"""API request and response schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class CopilotRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Question cannot be empty.")
        return text


class EvidenceItem(BaseModel):
    evidence_id: str
    type: str
    source: str
    metric: str
    value: Any = None
    product_id: Optional[str] = None
    store_id: Optional[str] = None
    period: Optional[str] = None


class FindingItem(BaseModel):
    issue_type: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    priority: str
    score: Optional[int] = None
    reason: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    recommended_action: str
    needs_human_review: bool = True


class CopilotResponse(BaseModel):
    question: str
    answer: str
    status: str
    intent: str
    priority: Optional[str] = None
    findings: list[Any] = Field(default_factory=list)
    recommendation: Optional[str] = None
    assumptions: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_policies: list[dict[str, Any]] = Field(default_factory=list)
    needs_human_review: bool = True
    ai_available: bool = True
    clarification: Optional[str] = None
    missing: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    business_date: str
    gemini_configured: bool
    database_ready: bool

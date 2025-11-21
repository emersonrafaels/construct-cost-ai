"""API schemas for request and response models."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from construct_cost_ai.domain.models import (
    BudgetItem,
    BudgetMetadata,
    Finding,
    RiskLevel,
    ValidationSummary,
)


class ValidateBudgetRequest(BaseModel):
    """Request model for budget validation endpoint."""

    items: List[BudgetItem] = Field(..., min_length=1, description="Budget line items")
    metadata: BudgetMetadata = Field(..., description="Project metadata")


class ValidateBudgetResponse(BaseModel):
    """Response model for budget validation endpoint."""

    findings_by_item: List[Finding] = Field(..., description="Findings for individual items")
    findings_by_group: Dict[str, List[Finding]] = Field(
        ..., description="Findings aggregated by group"
    )
    summary: ValidationSummary = Field(..., description="Validation summary")
    explanations: List[str] = Field(..., description="AI-generated explanations")


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")

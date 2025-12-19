"""
Core domain models for budget validation.

Define os modelos de dados principais do domínio de validação de orçamentos.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    """Severity levels for validation findings."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RiskLevel(str, Enum):
    """Overall risk assessment levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BudgetItem(BaseModel):
    """Represents a single line item in a construction budget."""

    item_id: str = Field(..., description="Unique identifier for the budget item")
    code: str = Field(..., description="Item code (e.g., SINAPI code)")
    description: str = Field(..., description="Item description")
    group: str = Field(..., description="Service group/category")
    quantity: float = Field(..., gt=0, description="Quantity of the item")
    unit: str = Field(..., description="Unit of measurement")
    unit_price: float = Field(..., ge=0, description="Unit price")
    total_price: float = Field(..., ge=0, description="Total price (quantity * unit_price)")

    @field_validator("total_price")
    @classmethod
    def validate_total_price(cls, v: float, info) -> float:
        """Validate that total_price matches quantity * unit_price."""
        if info.data:
            quantity = info.data.get("quantity", 0)
            unit_price = info.data.get("unit_price", 0)
            expected = round(quantity * unit_price, 2)
            if abs(v - expected) > 0.01:  # Allow small rounding differences
                return expected
        return v


class BudgetMetadata(BaseModel):
    """Metadata about the construction project."""

    archetype: str = Field(..., description="Building archetype (e.g., residential, commercial)")
    square_footage: float = Field(..., gt=0, description="Total area in square meters")
    region: str = Field(..., description="Region/state code (e.g., UF)")
    supplier: Optional[str] = Field(None, description="Supplier name")
    project_id: Optional[str] = Field(None, description="Project identifier")
    submission_date: Optional[datetime] = Field(
        default_factory=datetime.now, description="When the budget was submitted"
    )


class Budget(BaseModel):
    """Complete budget with items and metadata."""

    items: List[BudgetItem] = Field(..., min_length=1, description="List of budget items")
    metadata: BudgetMetadata = Field(..., description="Project metadata")


class Finding(BaseModel):
    """A validation finding for a budget item or aggregation."""

    code: str = Field(..., description="Finding code (e.g., QUANTITY_DEV_001)")
    severity: Severity = Field(..., description="Severity level")
    message: str = Field(..., description="Human-readable message")
    item_id: Optional[str] = Field(None, description="Reference to budget item (if applicable)")
    group: Optional[str] = Field(None, description="Service group (if applicable)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional contextual data")
    validator: str = Field(..., description="Name of the validator that generated this finding")


class ValidationSummary(BaseModel):
    """Summary of validation results."""

    total_items: int = Field(..., description="Total number of budget items")
    items_with_findings: int = Field(..., description="Number of items with findings")
    total_findings: int = Field(..., description="Total number of findings")
    findings_by_severity: Dict[str, int] = Field(
        default_factory=dict, description="Count of findings by severity"
    )
    risk_level: RiskLevel = Field(..., description="Overall risk assessment")
    execution_time_ms: float = Field(..., description="Validation execution time in milliseconds")


class ValidationResult(BaseModel):
    """Complete validation result."""

    findings_by_item: List[Finding] = Field(
        default_factory=list, description="Findings organized by item"
    )
    findings_by_group: Dict[str, List[Finding]] = Field(
        default_factory=dict, description="Findings aggregated by group"
    )
    summary: ValidationSummary = Field(..., description="Overall summary")
    explanations: List[str] = Field(
        default_factory=list,
        description="Natural-language explanations from AI analysis",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the validation was performed"
    )

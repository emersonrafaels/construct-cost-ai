"""Tests for deterministic validators."""

import pytest

from construct_cost_ai.domain.models import Severity
from construct_cost_ai.domain.validators.deterministic import (
    OutOfCatalogValidator,
    QuantityDeviationValidator,
    UnitPriceThresholdValidator,
)


def test_quantity_deviation_validator(sample_budget):
    """Test quantity deviation validator."""
    validator = QuantityDeviationValidator(threshold=0.15)

    findings = validator.validate(sample_budget)

    # Findings depend on mock expected quantities
    assert isinstance(findings, list)
    for finding in findings:
        assert finding.code == "QUANTITY_DEV_001"
        assert finding.severity in [Severity.WARNING, Severity.ERROR]
        assert finding.validator == validator.name


def test_unit_price_threshold_validator(sample_budget):
    """Test unit price threshold validator."""
    validator = UnitPriceThresholdValidator(threshold=0.20)

    findings = validator.validate(sample_budget)

    assert isinstance(findings, list)
    for finding in findings:
        assert finding.code == "PRICE_ANOMALY_001"
        assert finding.severity in [Severity.WARNING, Severity.ERROR, Severity.CRITICAL]
        assert finding.validator == validator.name


def test_out_of_catalog_validator(sample_budget):
    """Test out of catalog validator."""
    validator = OutOfCatalogValidator()

    findings = validator.validate(sample_budget)

    assert isinstance(findings, list)

    # CUSTOM_001 should be flagged as out of catalog
    custom_findings = [f for f in findings if f.item_id == "item_003"]
    assert len(custom_findings) > 0
    assert custom_findings[0].code == "OUT_OF_CATALOG_001"
    assert custom_findings[0].severity == Severity.WARNING


def test_validator_with_different_thresholds():
    """Test that validators respect threshold settings."""
    validator_low = QuantityDeviationValidator(threshold=0.05)
    validator_high = QuantityDeviationValidator(threshold=0.50)

    from construct_cost_ai.domain.models import Budget, BudgetItem, BudgetMetadata

    # Create a simple budget
    budget = Budget(
        items=[
            BudgetItem(
                item_id="test_001",
                code="SINAPI_001",
                description="Concrete pour m³",
                group="Structural",
                quantity=20.0,  # Higher quantity to trigger deviation
                unit="m³",
                unit_price=450.0,
                total_price=9000.0,
            )
        ],
        metadata=BudgetMetadata(
            archetype="Residential", square_footage=100.0, region="SP"
        ),
    )

    findings_low = validator_low.validate(budget)
    findings_high = validator_high.validate(budget)

    # Lower threshold should produce more or equal findings
    assert len(findings_low) >= len(findings_high)

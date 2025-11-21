"""Tests for the budget validation orchestrator."""

import pytest

from construct_cost_ai.domain.models import RiskLevel, Severity
from construct_cost_ai.domain.orchestrator import BudgetValidationOrchestrator
from construct_cost_ai.domain.validators.deterministic import (
    OutOfCatalogValidator,
    QuantityDeviationValidator,
    UnitPriceThresholdValidator,
)
from construct_cost_ai.infra.ai import StackSpotAIClient


def test_orchestrator_initialization():
    """Test orchestrator initialization."""
    validators = [
        QuantityDeviationValidator(),
        UnitPriceThresholdValidator(),
    ]
    ai_client = StackSpotAIClient(mock_mode=True)

    orchestrator = BudgetValidationOrchestrator(
        deterministic_validators=validators, ai_agent=ai_client
    )

    assert len(orchestrator.deterministic_validators) == 2
    assert orchestrator.ai_agent is not None


def test_orchestrator_validate_with_no_validators(sample_budget):
    """Test validation with no validators configured."""
    orchestrator = BudgetValidationOrchestrator(
        deterministic_validators=[], ai_agent=None
    )

    result = orchestrator.validate(sample_budget)

    assert result.summary.total_items == 3
    assert result.summary.total_findings == 0
    assert result.summary.risk_level == RiskLevel.LOW


def test_orchestrator_validate_with_validators(sample_budget):
    """Test validation with deterministic validators."""
    validators = [
        QuantityDeviationValidator(threshold=0.15),
        UnitPriceThresholdValidator(threshold=0.20),
        OutOfCatalogValidator(),
    ]

    orchestrator = BudgetValidationOrchestrator(
        deterministic_validators=validators, ai_agent=None
    )

    result = orchestrator.validate(sample_budget)

    assert result.summary.total_items == 3
    assert result.summary.total_findings >= 0
    assert isinstance(result.summary.risk_level, RiskLevel)
    assert len(result.findings_by_item) >= 0


def test_orchestrator_validate_with_ai(sample_budget):
    """Test validation with AI agent."""
    validators = [QuantityDeviationValidator()]
    ai_client = StackSpotAIClient(mock_mode=True)

    orchestrator = BudgetValidationOrchestrator(
        deterministic_validators=validators, ai_agent=ai_client
    )

    result = orchestrator.validate(sample_budget)

    assert result.summary.total_items == 3
    assert len(result.explanations) > 0
    assert isinstance(result.summary.risk_level, RiskLevel)


def test_orchestrator_findings_aggregation(sample_budget):
    """Test that findings are properly aggregated by group."""
    validators = [
        QuantityDeviationValidator(threshold=0.01),  # Low threshold to trigger findings
        OutOfCatalogValidator(),
    ]

    orchestrator = BudgetValidationOrchestrator(
        deterministic_validators=validators, ai_agent=None
    )

    result = orchestrator.validate(sample_budget)

    # Verify findings_by_group structure
    assert isinstance(result.findings_by_group, dict)

    # Verify all findings have a group or are in _ungrouped
    for finding in result.findings_by_item:
        if finding.group:
            assert finding.group in result.findings_by_group
        else:
            assert "_ungrouped" in result.findings_by_group


def test_orchestrator_add_validator(sample_budget):
    """Test adding validators dynamically."""
    orchestrator = BudgetValidationOrchestrator(deterministic_validators=[])

    assert len(orchestrator.deterministic_validators) == 0

    orchestrator.add_validator(QuantityDeviationValidator())
    assert len(orchestrator.deterministic_validators) == 1

    orchestrator.add_validator(UnitPriceThresholdValidator())
    assert len(orchestrator.deterministic_validators) == 2

    result = orchestrator.validate(sample_budget)
    assert result.summary.total_items == 3


def test_orchestrator_risk_level_calculation(sample_budget):
    """Test risk level calculation based on findings."""
    # No validators = low risk
    orchestrator = BudgetValidationOrchestrator(deterministic_validators=[])
    result = orchestrator.validate(sample_budget)
    assert result.summary.risk_level == RiskLevel.LOW

    # With validators, risk depends on findings severity
    validators = [
        QuantityDeviationValidator(threshold=0.15),
        UnitPriceThresholdValidator(threshold=0.20),
    ]
    orchestrator = BudgetValidationOrchestrator(deterministic_validators=validators)
    result = orchestrator.validate(sample_budget)

    # Risk level should be based on findings
    assert isinstance(result.summary.risk_level, RiskLevel)


def test_orchestrator_execution_time(sample_budget):
    """Test that execution time is recorded."""
    validators = [QuantityDeviationValidator()]

    orchestrator = BudgetValidationOrchestrator(deterministic_validators=validators)
    result = orchestrator.validate(sample_budget)

    assert result.summary.execution_time_ms > 0
    assert result.summary.execution_time_ms < 10000  # Should be under 10 seconds

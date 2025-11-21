"""Test configuration and fixtures."""

import pytest

from construct_cost_ai.domain.models import Budget, BudgetItem, BudgetMetadata


@pytest.fixture
def sample_budget_items():
    """Sample budget items for testing."""
    return [
        BudgetItem(
            item_id="item_001",
            code="SINAPI_001",
            description="Concrete pour m³",
            group="Structural",
            quantity=10.0,
            unit="m³",
            unit_price=450.0,
            total_price=4500.0,
        ),
        BudgetItem(
            item_id="item_002",
            code="SINAPI_002",
            description="Ceramic tile m²",
            group="Finishing",
            quantity=50.0,
            unit="m²",
            unit_price=55.0,
            total_price=2750.0,
        ),
        BudgetItem(
            item_id="item_003",
            code="CUSTOM_001",
            description="Special paint kg",
            group="Finishing",
            quantity=15.0,
            unit="kg",
            unit_price=65.0,
            total_price=975.0,
        ),
    ]


@pytest.fixture
def sample_metadata():
    """Sample budget metadata for testing."""
    return BudgetMetadata(
        archetype="Residential",
        square_footage=100.0,
        region="SP",
        supplier="Test Supplier",
        project_id="PRJ-001",
    )


@pytest.fixture
def sample_budget(sample_budget_items, sample_metadata):
    """Sample complete budget for testing."""
    return Budget(items=sample_budget_items, metadata=sample_metadata)

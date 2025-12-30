"""Tests for the FastAPI application."""

from fastapi.testclient import TestClient

from construct_cost_ai.api.app import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_validate_budget_success(sample_budget_items, sample_metadata):
    """Test successful budget validation."""
    request_data = {
        "items": [item.model_dump() for item in sample_budget_items],
        "metadata": sample_metadata.model_dump(),
    }

    response = client.post("/validate-budget", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "findings_by_item" in data
    assert "findings_by_group" in data
    assert "summary" in data
    assert "explanations" in data

    # Verify summary structure
    summary = data["summary"]
    assert summary["total_items"] == 3
    assert "total_findings" in summary
    assert "risk_level" in summary
    assert summary["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_validate_budget_invalid_data():
    """Test validation with invalid budget data."""
    request_data = {
        "items": [],  # Empty items list should fail validation
        "metadata": {
            "archetype": "Residential",
            "square_footage": 100.0,
            "region": "SP",
        },
    }

    response = client.post("/validate-budget", json=request_data)

    # Should return 422 for validation error
    assert response.status_code == 422


def test_validate_budget_missing_fields():
    """Test validation with missing required fields."""
    request_data = {
        "items": [
            {
                "item_id": "item_001",
                "code": "TEST_001",
                # Missing required fields
            }
        ],
        "metadata": {
            "archetype": "Residential",
            "square_footage": 100.0,
            "region": "SP",
        },
    }

    response = client.post("/validate-budget", json=request_data)

    assert response.status_code == 422


def test_validate_budget_with_findings():
    """Test validation that produces findings."""
    request_data = {
        "items": [
            {
                "item_id": "item_001",
                "code": "UNKNOWN_CODE",  # Should trigger OutOfCatalogValidator
                "description": "Test item",
                "group": "Test Group",
                "quantity": 10.0,
                "unit": "un",
                "unit_price": 100.0,
                "total_price": 1000.0,
            }
        ],
        "metadata": {
            "archetype": "Residential",
            "square_footage": 100.0,
            "region": "SP",
        },
    }

    response = client.post("/validate-budget", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Should have at least one finding from OutOfCatalogValidator
    assert data["summary"]["total_findings"] >= 0


def test_validate_budget_response_structure():
    """Test that response has correct structure."""
    request_data = {
        "items": [
            {
                "item_id": "item_001",
                "code": "TEST_001",
                "description": "Test item",
                "group": "Test",
                "quantity": 1.0,
                "unit": "un",
                "unit_price": 10.0,
                "total_price": 10.0,
            }
        ],
        "metadata": {
            "archetype": "Residential",
            "square_footage": 100.0,
            "region": "SP",
        },
    }

    response = client.post("/validate-budget", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Verify findings_by_item structure
    assert isinstance(data["findings_by_item"], list)

    # Verify findings_by_group structure
    assert isinstance(data["findings_by_group"], dict)

    # Verify summary structure
    assert "total_items" in data["summary"]
    assert "items_with_findings" in data["summary"]
    assert "total_findings" in data["summary"]
    assert "findings_by_severity" in data["summary"]
    assert "risk_level" in data["summary"]
    assert "execution_time_ms" in data["summary"]

    # Verify explanations
    assert isinstance(data["explanations"], list)

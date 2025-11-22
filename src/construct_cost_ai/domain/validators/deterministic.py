"""
Deterministic validators for budget validation.

Implementa validadores baseados em regras para análise de orçamentos.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Production"

from typing import List

from construct_cost_ai.domain.models import Budget, Finding, Severity
from construct_cost_ai.domain.validators.base import BaseDeterministicValidator
from construct_cost_ai.infra.logging import logger


class QuantityDeviationValidator(BaseDeterministicValidator):
    """Validates that quantities are within expected ranges."""

    def __init__(self, threshold: float = 0.15):
        """Initialize the validator.

        Args:
            threshold: Maximum allowed deviation from expected (e.g., 0.15 = 15%)
        """
        super().__init__(name="Quantity Deviation Validator")
        self.threshold = threshold

    def validate(self, budget: Budget) -> List[Finding]:
        """Check for quantity deviations against expected values.

        This is a placeholder implementation. In production, this would
        compare against a reference database (e.g., historical data, LPU tables).

        Args:
            budget: The budget to validate

        Returns:
            List of findings for items with quantity deviations
        """
        findings = []
        logger.debug(
            f"Running {self.name} on {len(budget.items)} items with threshold {self.threshold}"
        )

        for item in budget.items:
            # Placeholder logic: flag items with unusually high quantities
            # In production, compare against expected quantities from a reference database
            expected_quantity = self._get_expected_quantity(item, budget.metadata)

            if expected_quantity is None:
                continue

            deviation = abs(item.quantity - expected_quantity) / expected_quantity

            if deviation > self.threshold:
                severity = Severity.WARNING if deviation < 0.3 else Severity.ERROR
                findings.append(
                    Finding(
                        code="QUANTITY_DEV_001",
                        severity=severity,
                        message=(
                            f"Quantity deviation of {deviation:.1%} for item '{item.description}'. "
                            f"Expected: {expected_quantity:.2f}, Got: {item.quantity:.2f}"
                        ),
                        item_id=item.item_id,
                        group=item.group,
                        details={
                            "expected_quantity": expected_quantity,
                            "actual_quantity": item.quantity,
                            "deviation_percentage": deviation,
                            "threshold": self.threshold,
                        },
                        validator=self.name,
                    )
                )

        logger.info(f"{self.name} found {len(findings)} findings")
        return findings

    def _get_expected_quantity(self, item, metadata) -> float | None:
        """Get expected quantity from reference data.

        This is a placeholder. In production, this would query a database
        based on item code, archetype, and square footage.

        Args:
            item: Budget item
            metadata: Project metadata

        Returns:
            Expected quantity or None if not available
        """
        # Placeholder: simulate expected quantities based on area
        # Real implementation would use LPU tables or historical data
        area = metadata.square_footage

        # Simple heuristic for demonstration
        if "concrete" in item.description.lower():
            return area * 0.15  # Example: 0.15 m³ per m²
        elif "paint" in item.description.lower():
            return area * 0.3  # Example: 0.3 kg per m²
        elif "tile" in item.description.lower():
            return area * 1.1  # Example: 1.1 m² per m² (with waste)

        return None  # No reference data available


class UnitPriceThresholdValidator(BaseDeterministicValidator):
    """Validates that unit prices are within acceptable ranges."""

    def __init__(self, threshold: float = 0.20):
        """Initialize the validator.

        Args:
            threshold: Maximum allowed deviation from reference prices (e.g., 0.20 = 20%)
        """
        super().__init__(name="Unit Price Threshold Validator")
        self.threshold = threshold

    def validate(self, budget: Budget) -> List[Finding]:
        """Check for unit price anomalies.

        This is a placeholder implementation. In production, this would
        compare against reference price tables (e.g., SINAPI, regional tables).

        Args:
            budget: The budget to validate

        Returns:
            List of findings for items with price anomalies
        """
        findings = []
        logger.debug(
            f"Running {self.name} on {len(budget.items)} items with threshold {self.threshold}"
        )

        for item in budget.items:
            reference_price = self._get_reference_price(item, budget.metadata)

            if reference_price is None:
                continue

            deviation = abs(item.unit_price - reference_price) / reference_price

            if deviation > self.threshold:
                severity = self._calculate_severity(deviation)
                findings.append(
                    Finding(
                        code="PRICE_ANOMALY_001",
                        severity=severity,
                        message=(
                            f"Unit price deviation of {deviation:.1%} for item '{item.description}'. "
                            f"Reference: R$ {reference_price:.2f}, Got: R$ {item.unit_price:.2f}"
                        ),
                        item_id=item.item_id,
                        group=item.group,
                        details={
                            "reference_price": reference_price,
                            "actual_price": item.unit_price,
                            "deviation_percentage": deviation,
                            "threshold": self.threshold,
                        },
                        validator=self.name,
                    )
                )

        logger.info(f"{self.name} found {len(findings)} findings")
        return findings

    def _get_reference_price(self, item, metadata) -> float | None:
        """Get reference price from price tables.

        This is a placeholder. In production, this would query SINAPI,
        regional price tables, or similar databases.

        Args:
            item: Budget item
            metadata: Project metadata

        Returns:
            Reference price or None if not available
        """
        # Placeholder: simulate reference prices
        # Real implementation would query price databases by code and region
        if "concrete" in item.description.lower():
            return 450.0  # Example: R$ 450/m³
        elif "paint" in item.description.lower():
            return 35.0  # Example: R$ 35/kg
        elif "tile" in item.description.lower():
            return 55.0  # Example: R$ 55/m²

        return None

    def _calculate_severity(self, deviation: float) -> Severity:
        """Calculate severity based on deviation magnitude."""
        if deviation < 0.3:
            return Severity.WARNING
        elif deviation < 0.5:
            return Severity.ERROR
        else:
            return Severity.CRITICAL


class OutOfCatalogValidator(BaseDeterministicValidator):
    """Validates that items exist in reference catalogs (LPU, SINAPI, etc.)."""

    def __init__(self):
        super().__init__(name="Out of Catalog Validator")

    def validate(self, budget: Budget) -> List[Finding]:
        """Check if items are present in reference catalogs.

        This is a placeholder implementation. In production, this would
        query actual catalog databases.

        Args:
            budget: The budget to validate

        Returns:
            List of findings for items not in catalogs
        """
        findings = []
        logger.debug(f"Running {self.name} on {len(budget.items)} items")

        for item in budget.items:
            if not self._is_in_catalog(item.code, budget.metadata.region):
                findings.append(
                    Finding(
                        code="OUT_OF_CATALOG_001",
                        severity=Severity.WARNING,
                        message=(
                            f"Item code '{item.code}' not found in reference catalogs "
                            f"for region '{budget.metadata.region}'. "
                            f"Description: '{item.description}'"
                        ),
                        item_id=item.item_id,
                        group=item.group,
                        details={
                            "code": item.code,
                            "region": budget.metadata.region,
                            "description": item.description,
                        },
                        validator=self.name,
                    )
                )

        logger.info(f"{self.name} found {len(findings)} findings")
        return findings

    def _is_in_catalog(self, code: str, region: str) -> bool:
        """Check if item code exists in catalogs.

        This is a placeholder. In production, this would query
        SINAPI, LPU, or regional catalog databases.

        Args:
            code: Item code
            region: Region code

        Returns:
            True if item is in catalog, False otherwise
        """
        # Placeholder: simulate catalog lookup
        # Real implementation would query actual databases
        known_codes = {
            "SINAPI_001",
            "SINAPI_002",
            "SINAPI_003",
            "LPU_001",
            "LPU_002",
        }

        # For demonstration, items not starting with known prefixes are "out of catalog"
        return code in known_codes or any(
            code.startswith(prefix) for prefix in ["SINAPI_", "LPU_"]
        )

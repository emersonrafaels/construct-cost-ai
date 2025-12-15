"""
API routes for budget validation.

Define os endpoints da API REST para validação de orçamentos.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Production"

from fastapi import APIRouter, HTTPException, status

from construct_cost_ai import __version__
from construct_cost_ai.api.schemas import (
    HealthCheckResponse,
    ValidateBudgetRequest,
    ValidateBudgetResponse,
)
from construct_cost_ai.domain.models import Budget
from construct_cost_ai.domain.orchestrator import BudgetValidationOrchestrator
from construct_cost_ai.domain.validators.deterministic import (
    OutOfCatalogValidator,
    QuantityDeviationValidator,
    UnitPriceThresholdValidator,
)
from construct_cost_ai.infra.ai import StackSpotAIClient
from construct_cost_ai.infra.config import get_settings
from construct_cost_ai.infra.logging import logger

# Obtendo a instância de configurações
settings = get_settings()

router = APIRouter()


def get_orchestrator() -> BudgetValidationOrchestrator:
    """Create and configure the validation orchestrator.

    Returns:
        Configured BudgetValidationOrchestrator
    """
    # Initialize deterministic validators
    validators = [
        QuantityDeviationValidator(
            threshold=settings.get("validators.quantity_deviation_threshold", 0.15)
        ),
        UnitPriceThresholdValidator(
            threshold=settings.get("validators.unit_price_deviation_threshold", 0.20)
        ),
        OutOfCatalogValidator(),
    ]

    # Initialize AI client
    ai_client = StackSpotAIClient(mock_mode=True)

    # Create orchestrator
    orchestrator = BudgetValidationOrchestrator(
        deterministic_validators=validators, ai_agent=ai_client
    )

    return orchestrator


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint.

    Returns:
        Service health status
    """
    return HealthCheckResponse(status="healthy", version=__version__)


@router.post(
    "/validate-budget",
    response_model=ValidateBudgetResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a construction budget",
    description=(
        "Validates a construction budget using deterministic rules and AI analysis. "
        "Returns findings, aggregations, and natural-language explanations."
    ),
)
async def validate_budget(request: ValidateBudgetRequest):
    """Validate a construction budget.

    Args:
        request: Budget validation request with items and metadata

    Returns:
        Validation results with findings and explanations

    Raises:
        HTTPException: If validation fails
    """
    try:
        logger.info(
            f"Received validation request: {len(request.items)} items, "
            f"archetype={request.metadata.archetype}, "
            f"area={request.metadata.square_footage}m²"
        )

        # Create budget model
        budget = Budget(items=request.items, metadata=request.metadata)

        # Get orchestrator and run validation
        orchestrator = get_orchestrator()
        result = orchestrator.validate(budget)

        logger.info(
            f"Validation complete: {result.summary.total_findings} findings, "
            f"risk_level={result.summary.risk_level.value}"
        )

        return ValidateBudgetResponse(
            findings_by_item=result.findings_by_item,
            findings_by_group=result.findings_by_group,
            summary=result.summary,
            explanations=result.explanations,
        )

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )

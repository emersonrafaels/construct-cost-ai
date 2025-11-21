"""StackSpot AI client for AI-based budget analysis."""

import time
from typing import Dict, Optional

import httpx

from construct_cost_ai.domain.models import Budget
from construct_cost_ai.infra.config import get_settings
from construct_cost_ai.infra.logging import logger

# Get settings instance
settings = get_settings()


class StackSpotAIClient:
    """Client for interacting with StackSpot AI API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        mock_mode: bool = True,
    ):
        """Initialize the StackSpot AI client.

        Args:
            base_url: Base URL for StackSpot AI API (defaults to settings)
            api_key: API key for authentication (defaults to settings)
            timeout: Request timeout in seconds
            mock_mode: If True, returns mock responses instead of making real API calls
        """
        self.base_url = base_url or settings.get("stackspot.ai_base_url")
        self.api_key = api_key or settings.get("stackspot.ai_api_key")
        self.timeout = timeout or settings.get("stackspot.ai_timeout", 30)
        self.mock_mode = mock_mode

        if not self.mock_mode and not self.api_key:
            logger.warning(
                "StackSpot AI API key not configured. Client will operate in mock mode."
            )
            self.mock_mode = True

        logger.info(
            f"StackSpot AI client initialized (base_url={self.base_url}, mock_mode={self.mock_mode})"
        )

    def analyze_budget_context(
        self, budget: Budget, additional_context: Optional[Dict] = None
    ) -> Dict:
        """Analyze budget using AI and return insights.

        Args:
            budget: The budget to analyze
            additional_context: Optional additional context for the AI

        Returns:
            Dictionary containing:
                - explanations: List[str] - Natural language explanations
                - risk_assessment: str - Overall risk level
                - suggestions: List[str] - Improvement suggestions
        """
        start_time = time.time()

        if self.mock_mode:
            logger.debug("Using mock AI response (mock_mode=True)")
            result = self._get_mock_response(budget, additional_context)
        else:
            result = self._make_api_call(budget, additional_context)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"AI analysis completed in {duration_ms:.2f}ms")

        return result

    def _make_api_call(
        self, budget: Budget, additional_context: Optional[Dict] = None
    ) -> Dict:
        """Make actual HTTP request to StackSpot AI API.

        Args:
            budget: The budget to analyze
            additional_context: Optional additional context

        Returns:
            AI analysis results
        """
        endpoint = f"{self.base_url}/analyze/budget"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "budget": budget.model_dump(),
            "context": additional_context or {},
        }

        logger.debug(f"Making API request to {endpoint}")

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()

                logger.info(
                    f"StackSpot AI API call successful (status={response.status_code})"
                )
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"StackSpot AI API error: {e.response.status_code} - {e.response.text}"
            )
            # Fallback to mock response on error
            return self._get_mock_response(budget, additional_context)

        except Exception as e:
            logger.error(f"StackSpot AI API call failed: {str(e)}")
            # Fallback to mock response on error
            return self._get_mock_response(budget, additional_context)

    def _get_mock_response(
        self, budget: Budget, additional_context: Optional[Dict] = None
    ) -> Dict:
        """Generate mock AI response for testing and development.

        Args:
            budget: The budget being analyzed
            additional_context: Optional additional context

        Returns:
            Mock AI analysis results
        """
        total_value = sum(item.total_price for item in budget.items)
        num_items = len(budget.items)
        metadata = budget.metadata

        # Generate realistic mock explanations
        explanations = [
            f"Analysis of {num_items} budget items totaling R$ {total_value:,.2f} for {metadata.archetype} archetype.",
            f"The budget covers {metadata.square_footage:.2f} m² in the {metadata.region} region.",
            "Several items show price deviations from regional reference values, which may indicate market variations or supplier-specific pricing strategies.",
            "Quantity estimates appear generally consistent with the project archetype and square footage.",
        ]

        # Determine risk level based on simple heuristics
        avg_price_per_sqm = total_value / metadata.square_footage if metadata.square_footage > 0 else 0

        if avg_price_per_sqm > 3000:
            risk_assessment = "HIGH"
            explanations.append(
                f"The average cost per m² (R$ {avg_price_per_sqm:,.2f}) is significantly above typical values for this archetype."
            )
        elif avg_price_per_sqm > 2000:
            risk_assessment = "MEDIUM"
            explanations.append(
                f"The average cost per m² (R$ {avg_price_per_sqm:,.2f}) is within acceptable range but warrants review."
            )
        else:
            risk_assessment = "LOW"
            explanations.append(
                f"The average cost per m² (R$ {avg_price_per_sqm:,.2f}) appears reasonable for this archetype."
            )

        suggestions = [
            "Review items with significant price deviations against multiple reference sources.",
            "Verify quantities for structural items against project specifications.",
            "Consider requesting itemized breakdowns for any composite services.",
            "Cross-reference all item codes with current regional catalogs (SINAPI, LPU).",
        ]

        return {
            "explanations": explanations,
            "risk_assessment": risk_assessment,
            "suggestions": suggestions,
        }

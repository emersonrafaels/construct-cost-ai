"""
Base classes and protocols for validators.

Define as classes abstratas e protocolos para validadores determinísticos e agentes de IA.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Production"

from abc import ABC, abstractmethod
from typing import List, Protocol

from construct_cost_ai.domain.models import Budget, Finding


class BaseDeterministicValidator(ABC):
    """Abstract base class for deterministic (rule-based) validators."""

    def __init__(self, name: str):
        """Initialize the validator with a name.

        Args:
            name: Human-readable name for this validator
        """
        self.name = name

    @abstractmethod
    def validate(self, budget: Budget) -> List[Finding]:
        """Validate a budget and return a list of findings.

        Args:
            budget: The budget to validate

        Returns:
            List of findings (empty if no issues found)
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


class BaseAIAgent(Protocol):
    """Protocol for AI-based agents that analyze budgets.

    This defines the interface that AI clients must implement.
    """

    def analyze_budget_context(
        self, budget: Budget, additional_context: dict = None
    ) -> dict:
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
        ...

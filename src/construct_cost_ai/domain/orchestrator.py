"""
Budget validation orchestrator.

Orquestra a validação de orçamentos usando validadores determinísticos e agentes de IA.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import time
from collections import defaultdict
from typing import Dict, List, Optional

from construct_cost_ai.domain.models import (
    Budget,
    Finding,
    RiskLevel,
    Severity,
    ValidationResult,
    ValidationSummary,
)
from construct_cost_ai.domain.validators.base import BaseAIAgent, BaseDeterministicValidator
from construct_cost_ai.infra.logging import logger


class BudgetValidationOrchestrator:
    """Orchestrates budget validation using deterministic validators and AI agents."""

    def __init__(
        self,
        deterministic_validators: Optional[List[BaseDeterministicValidator]] = None,
        ai_agent: Optional[BaseAIAgent] = None,
    ):
        """Initialize the orchestrator.

        Args:
            deterministic_validators: List of rule-based validators to apply
            ai_agent: AI agent for contextual analysis (optional)
        """
        self.deterministic_validators = deterministic_validators or []
        self.ai_agent = ai_agent

        logger.info(
            f"Orchestrator initialized with {len(self.deterministic_validators)} "
            f"deterministic validators and {'AI agent' if ai_agent else 'no AI agent'}"
        )

    def validate(self, budget: Budget) -> ValidationResult:
        """Validate a budget using all configured validators.

        Args:
            budget: The budget to validate

        Returns:
            ValidationResult containing all findings and analysis
        """
        start_time = time.time()
        logger.info(
            f"Starting validation for budget with {len(budget.items)} items "
            f"(archetype={budget.metadata.archetype}, area={budget.metadata.square_footage}m²)"
        )

        # Run deterministic validators
        all_findings = []
        for validator in self.deterministic_validators:
            try:
                findings = validator.validate(budget)
                all_findings.extend(findings)
                logger.debug(f"{validator.name} produced {len(findings)} findings")
            except Exception as e:
                logger.error(f"Error running {validator.name}: {str(e)}", exc_info=True)

        # Run AI analysis if available
        explanations = []
        ai_risk_assessment = None
        if self.ai_agent:
            try:
                logger.debug("Running AI analysis")
                ai_result = self.ai_agent.analyze_budget_context(budget)
                explanations = ai_result.get("explanations", [])
                ai_risk_assessment = ai_result.get("risk_assessment")

                # Add suggestions as explanations
                suggestions = ai_result.get("suggestions", [])
                if suggestions:
                    explanations.append("\nRecommendations:")
                    explanations.extend([f"• {s}" for s in suggestions])

                logger.debug(f"AI analysis complete: {len(explanations)} explanations")
            except Exception as e:
                logger.error(f"Error running AI analysis: {str(e)}", exc_info=True)

        # Aggregate findings
        findings_by_group = self._aggregate_by_group(all_findings)

        # Calculate summary
        summary = self._calculate_summary(budget, all_findings, start_time, ai_risk_assessment)

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"Validation complete: {len(all_findings)} findings in {execution_time:.2f}ms "
            f"(risk_level={summary.risk_level.value})"
        )

        return ValidationResult(
            findings_by_item=all_findings,
            findings_by_group=findings_by_group,
            summary=summary,
            explanations=explanations,
        )

    def _aggregate_by_group(self, findings: List[Finding]) -> Dict[str, List[Finding]]:
        """Aggregate findings by service group.

        Args:
            findings: List of all findings

        Returns:
            Dictionary mapping group names to their findings
        """
        grouped = defaultdict(list)
        for finding in findings:
            if finding.group:
                grouped[finding.group].append(finding)
            else:
                grouped["_ungrouped"].append(finding)
        return dict(grouped)

    def _calculate_summary(
        self,
        budget: Budget,
        findings: List[Finding],
        start_time: float,
        ai_risk_assessment: Optional[str] = None,
    ) -> ValidationSummary:
        """Calculate validation summary.

        Args:
            budget: The budget that was validated
            findings: All findings from validation
            start_time: Validation start timestamp
            ai_risk_assessment: Risk level from AI (if available)

        Returns:
            ValidationSummary
        """
        # Count items with findings
        items_with_findings = len(set(f.item_id for f in findings if f.item_id))

        # Count findings by severity
        findings_by_severity = {}
        for severity in Severity:
            count = sum(1 for f in findings if f.severity == severity)
            if count > 0:
                findings_by_severity[severity.value] = count

        # Determine overall risk level
        risk_level = self._determine_risk_level(findings, ai_risk_assessment)

        execution_time_ms = (time.time() - start_time) * 1000

        return ValidationSummary(
            total_items=len(budget.items),
            items_with_findings=items_with_findings,
            total_findings=len(findings),
            findings_by_severity=findings_by_severity,
            risk_level=risk_level,
            execution_time_ms=execution_time_ms,
        )

    def _determine_risk_level(
        self, findings: List[Finding], ai_risk_assessment: Optional[str] = None
    ) -> RiskLevel:
        """Determine overall risk level based on findings and AI assessment.

        Args:
            findings: All validation findings
            ai_risk_assessment: Risk level suggested by AI (if available)

        Returns:
            Overall RiskLevel
        """
        # Count critical/error findings
        critical_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        error_count = sum(1 for f in findings if f.severity == Severity.ERROR)
        warning_count = sum(1 for f in findings if f.severity == Severity.WARNING)

        # Determine risk based on findings
        if critical_count > 0:
            findings_risk = RiskLevel.CRITICAL
        elif error_count >= 5:
            findings_risk = RiskLevel.HIGH
        elif error_count >= 2 or warning_count >= 10:
            findings_risk = RiskLevel.MEDIUM
        else:
            findings_risk = RiskLevel.LOW

        # Consider AI assessment if available
        if ai_risk_assessment:
            ai_risk_map = {
                "CRITICAL": RiskLevel.CRITICAL,
                "HIGH": RiskLevel.HIGH,
                "MEDIUM": RiskLevel.MEDIUM,
                "LOW": RiskLevel.LOW,
            }
            ai_risk = ai_risk_map.get(ai_risk_assessment.upper(), findings_risk)

            # Take the higher of the two risk levels
            risk_levels_order = [
                RiskLevel.LOW,
                RiskLevel.MEDIUM,
                RiskLevel.HIGH,
                RiskLevel.CRITICAL,
            ]
            if risk_levels_order.index(ai_risk) > risk_levels_order.index(findings_risk):
                return ai_risk

        return findings_risk

    def add_validator(self, validator: BaseDeterministicValidator) -> None:
        """Add a deterministic validator to the orchestrator.

        Args:
            validator: The validator to add
        """
        self.deterministic_validators.append(validator)
        logger.info(f"Added validator: {validator.name}")

    def set_ai_agent(self, ai_agent: BaseAIAgent) -> None:
        """Set or replace the AI agent.

        Args:
            ai_agent: The AI agent to use
        """
        self.ai_agent = ai_agent
        logger.info("AI agent configured")

"""Streamlit frontend for budget validation."""

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from construct_cost_ai.domain.models import Budget, BudgetItem, BudgetMetadata
from construct_cost_ai.domain.orchestrator import BudgetValidationOrchestrator
from construct_cost_ai.domain.validators.deterministic import (
    OutOfCatalogValidator,
    QuantityDeviationValidator,
    UnitPriceThresholdValidator,
)
from construct_cost_ai.infra.ai import StackSpotAIClient
from construct_cost_ai.infra.config import get_settings

# Get settings instance
settings = get_settings()

# Page configuration
st.set_page_config(
    page_title="Construct Cost AI - Budget Validator",
    page_icon="🏗️",
    layout="wide",
)


def get_orchestrator() -> BudgetValidationOrchestrator:
    """Create and configure the validation orchestrator."""
    validators = [
        QuantityDeviationValidator(
            threshold=settings.get("validators.quantity_deviation_threshold", 0.15)
        ),
        UnitPriceThresholdValidator(
            threshold=settings.get("validators.unit_price_deviation_threshold", 0.20)
        ),
        OutOfCatalogValidator(),
    ]

    ai_client = StackSpotAIClient(mock_mode=True)

    return BudgetValidationOrchestrator(
        deterministic_validators=validators, ai_agent=ai_client
    )


def parse_budget_file(uploaded_file) -> list:
    """Parse uploaded budget file (JSON or CSV).

    Args:
        uploaded_file: Uploaded file from Streamlit

    Returns:
        List of budget items as dictionaries
    """
    if uploaded_file.name.endswith(".json"):
        data = json.loads(uploaded_file.read())
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        return data
    elif uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        return df.to_dict("records")
    else:
        raise ValueError("Unsupported file format. Please upload JSON or CSV.")


def main():
    """Main Streamlit application."""
    st.title("🏗️ Construct Cost AI - Budget Validator")
    st.markdown(
        "Upload a construction budget and validate it using AI-powered analysis and rule-based checks."
    )

    # Sidebar for metadata input
    with st.sidebar:
        st.header("📋 Project Metadata")

        archetype = st.selectbox(
            "Archetype",
            ["Residential", "Commercial", "Industrial", "Educational", "Healthcare"],
        )

        square_footage = st.number_input(
            "Square Footage (m²)", min_value=1.0, value=100.0, step=1.0
        )

        region = st.text_input("Region/UF", value="SP")

        supplier = st.text_input("Supplier (optional)", value="")

        project_id = st.text_input("Project ID (optional)", value="")

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📄 Upload Budget")

        uploaded_file = st.file_uploader(
            "Upload budget file (JSON or CSV)",
            type=["json", "csv"],
            help="Upload a JSON or CSV file containing budget line items",
        )

        if uploaded_file:
            try:
                items_data = parse_budget_file(uploaded_file)
                st.success(f"✅ Loaded {len(items_data)} budget items")

                # Display uploaded data
                with st.expander("View uploaded data"):
                    st.json(items_data[:5])  # Show first 5 items

            except Exception as e:
                st.error(f"❌ Error parsing file: {str(e)}")
                items_data = None
        else:
            items_data = None

    with col2:
        st.header("🔍 Validation")

        if st.button("Validate Budget", type="primary", disabled=items_data is None):
            if items_data:
                with st.spinner("Validating budget..."):
                    try:
                        # Create budget model
                        budget_items = [BudgetItem(**item) for item in items_data]

                        metadata = BudgetMetadata(
                            archetype=archetype,
                            square_footage=square_footage,
                            region=region,
                            supplier=supplier if supplier else None,
                            project_id=project_id if project_id else None,
                            submission_date=datetime.now(),
                        )

                        budget = Budget(items=budget_items, metadata=metadata)

                        # Run validation
                        orchestrator = get_orchestrator()
                        result = orchestrator.validate(budget)

                        # Store result in session state
                        st.session_state["validation_result"] = result
                        st.session_state["budget"] = budget

                        st.success("✅ Validation complete!")

                    except Exception as e:
                        st.error(f"❌ Validation error: {str(e)}")

    # Display results
    if "validation_result" in st.session_state:
        result = st.session_state["validation_result"]
        budget = st.session_state["budget"]

        st.divider()
        st.header("📊 Validation Results")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Items", result.summary.total_items)

        with col2:
            st.metric("Items with Findings", result.summary.items_with_findings)

        with col3:
            st.metric("Total Findings", result.summary.total_findings)

        with col4:
            risk_color = {
                "LOW": "🟢",
                "MEDIUM": "🟡",
                "HIGH": "🟠",
                "CRITICAL": "🔴",
            }
            st.metric(
                "Risk Level",
                f"{risk_color.get(result.summary.risk_level.value, '')} {result.summary.risk_level.value}",
            )

        # Findings by severity
        if result.summary.findings_by_severity:
            st.subheader("Findings by Severity")
            severity_df = pd.DataFrame(
                list(result.summary.findings_by_severity.items()),
                columns=["Severity", "Count"],
            )
            st.bar_chart(severity_df.set_index("Severity"))

        # AI Explanations
        if result.explanations:
            st.subheader("🤖 AI Analysis")
            for explanation in result.explanations:
                st.info(explanation)

        # Findings by item
        if result.findings_by_item:
            st.subheader("🔍 Findings by Item")

            findings_data = [
                {
                    "Item ID": f.item_id or "N/A",
                    "Code": f.code,
                    "Severity": f.severity.value,
                    "Message": f.message,
                    "Validator": f.validator,
                }
                for f in result.findings_by_item
            ]

            findings_df = pd.DataFrame(findings_data)
            st.dataframe(findings_df, use_container_width=True)

        # Findings by group
        if result.findings_by_group:
            st.subheader("📦 Findings by Group")

            for group, findings in result.findings_by_group.items():
                with st.expander(f"{group} ({len(findings)} findings)"):
                    group_data = [
                        {
                            "Code": f.code,
                            "Severity": f.severity.value,
                            "Message": f.message,
                        }
                        for f in findings
                    ]
                    st.table(pd.DataFrame(group_data))


if __name__ == "__main__":
    main()

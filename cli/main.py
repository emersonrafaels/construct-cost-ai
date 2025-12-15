"""Rich-based CLI for budget validation."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from construct_cost_ai.domain.models import Budget, BudgetItem, BudgetMetadata
from construct_cost_ai.domain.orchestrator import BudgetValidationOrchestrator
from construct_cost_ai.domain.validators.deterministic import (
    OutOfCatalogValidator,
    QuantityDeviationValidator,
    UnitPriceThresholdValidator,
)
from construct_cost_ai.infra.ai import StackSpotAIClient
from construct_cost_ai.infra.config import get_settings

# Obtendo a instância de configurações
settings = get_settings()

app = typer.Typer(
    name="construct-cost-cli",
    help="CLI tool for construction budget validation using AI and rule-based checks",
)
console = Console()


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

    return BudgetValidationOrchestrator(deterministic_validators=validators, ai_agent=ai_client)


def load_budget_from_file(file_path: Path) -> list:
    """Load budget items from JSON file.

    Args:
        file_path: Path to budget file

    Returns:
        List of budget items

    Raises:
        typer.Exit: If file cannot be loaded
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "items" in data:
            return data["items"]
        return data

    except FileNotFoundError:
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON file: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate(
    budget_file: Path = typer.Argument(
        ..., help="Path to budget JSON file", exists=True, file_okay=True, dir_okay=False
    ),
    archetype: str = typer.Option("Residential", "--archetype", "-a", help="Building archetype"),
    square_footage: float = typer.Option(
        100.0, "--area", "-s", help="Square footage in m²", min=1.0
    ),
    region: str = typer.Option("SP", "--region", "-r", help="Region/state code"),
    supplier: Optional[str] = typer.Option(None, "--supplier", help="Supplier name"),
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Project ID"),
    output_json: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Save results to JSON file"
    ),
):
    """Validate a construction budget from a JSON file.

    Example:
        construct-cost-cli validate budget.json --archetype Residential --area 150 --region SP
    """
    console.print(Panel.fit("🏗️  [bold]Construct Cost AI - Budget Validator[/bold]"))

    # Load budget
    console.print(f"\n[cyan]Loading budget from:[/cyan] {budget_file}")
    items_data = load_budget_from_file(budget_file)
    console.print(f"[green]✓ Loaded {len(items_data)} budget items[/green]")

    # Create budget model
    try:
        budget_items = [BudgetItem(**item) for item in items_data]
        metadata = BudgetMetadata(
            archetype=archetype,
            square_footage=square_footage,
            region=region,
            supplier=supplier,
            project_id=project_id,
        )
        budget = Budget(items=budget_items, metadata=metadata)
    except Exception as e:
        console.print(f"[red]Error creating budget model: {e}[/red]")
        raise typer.Exit(1)

    # Run validation
    console.print("\n[cyan]Running validation...[/cyan]")
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.validate(budget)
        console.print(
            f"[green]✓ Validation complete in {result.summary.execution_time_ms:.2f}ms[/green]"
        )
    except Exception as e:
        console.print(f"[red]Validation error: {e}[/red]")
        raise typer.Exit(1)

    # Display summary
    console.print("\n[bold]📊 Validation Summary[/bold]")

    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")

    summary_table.add_row("Total Items", str(result.summary.total_items))
    summary_table.add_row("Items with Findings", str(result.summary.items_with_findings))
    summary_table.add_row("Total Findings", str(result.summary.total_findings))

    # Risk level with color
    risk_colors = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "orange", "CRITICAL": "red"}
    risk_color = risk_colors.get(result.summary.risk_level.value, "white")
    summary_table.add_row(
        "Risk Level", f"[{risk_color}]{result.summary.risk_level.value}[/{risk_color}]"
    )

    console.print(summary_table)

    # Display findings by severity
    if result.summary.findings_by_severity:
        console.print("\n[bold]Findings by Severity:[/bold]")
        for severity, count in result.summary.findings_by_severity.items():
            console.print(f"  {severity}: {count}")

    # Display AI explanations
    if result.explanations:
        console.print("\n[bold]🤖 AI Analysis:[/bold]")
        for explanation in result.explanations:
            console.print(f"  • {explanation}")

    # Display findings table
    if result.findings_by_item:
        console.print(f"\n[bold]🔍 Findings ({len(result.findings_by_item)} total):[/bold]")

        findings_table = Table(show_header=True, header_style="bold magenta")
        findings_table.add_column("Item ID", style="cyan")
        findings_table.add_column("Severity", style="yellow")
        findings_table.add_column("Code", style="white")
        findings_table.add_column("Message", style="white", no_wrap=False)

        for finding in result.findings_by_item[:20]:  # Show first 20
            severity_style = {
                "INFO": "blue",
                "WARNING": "yellow",
                "ERROR": "orange",
                "CRITICAL": "red",
            }.get(finding.severity.value, "white")

            findings_table.add_row(
                finding.item_id or "N/A",
                f"[{severity_style}]{finding.severity.value}[/{severity_style}]",
                finding.code,
                finding.message[:100] + "..." if len(finding.message) > 100 else finding.message,
            )

        console.print(findings_table)

        if len(result.findings_by_item) > 20:
            console.print(f"\n[dim]... and {len(result.findings_by_item) - 20} more findings[/dim]")

    # Display findings by group
    if result.findings_by_group:
        console.print(f"\n[bold]📦 Findings by Group:[/bold]")
        for group, findings in result.findings_by_group.items():
            console.print(f"  {group}: {len(findings)} findings")

    # Save to file if requested
    if output_json:
        try:
            output_data = {
                "findings_by_item": [f.model_dump() for f in result.findings_by_item],
                "findings_by_group": {
                    k: [f.model_dump() for f in v] for k, v in result.findings_by_group.items()
                },
                "summary": result.summary.model_dump(),
                "explanations": result.explanations,
                "timestamp": result.timestamp.isoformat(),
            }

            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            console.print(f"\n[green]✓ Results saved to: {output_json}[/green]")
        except Exception as e:
            console.print(f"\n[red]Error saving results: {e}[/red]")


@app.command()
def version():
    """Display version information."""
    from construct_cost_ai import __version__

    console.print(f"Construct Cost AI CLI v{__version__}")


if __name__ == "__main__":
    app()

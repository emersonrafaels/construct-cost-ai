"""
LPU Validation Module - Checks discrepancies between budget and price base.

This module performs reconciliation between the budget sent by the construction company
and the official LPU (Unit Price List) database, identifying discrepancies
in values with configurable tolerance.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

from pathlib import Path
from typing import Union
import sys

import pandas as pd

# Add the src directory to the path
base_dir = Path(__file__).parents[5]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from config.config_dynaconf import get_settings
from utils.data.data_functions import read_data

settings = get_settings()


class ValidatorLPUError(Exception):
    """Base exception for LPU validator errors."""

    pass


class FileNotFoundError(ValidatorLPUError):
    """Exception for file not found."""

    pass


class MissingColumnsError(ValidatorLPUError):
    """Exception for missing mandatory columns."""

    pass


def load_budget(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads the budget file.

    Args:
        path: Path to the budget file (Excel or CSV)

    Returns:
        DataFrame with the loaded budget

    Raises:
        FileNotFoundError: If the file is not found
        MissingColumnsError: If mandatory columns are missing
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Budget file not found: {file_path}")

    # Mandatory columns
    required_columns = settings.get("module_validator_lpu.required_columns", [])

    try:
        df = read_data(file_path=file_path, 
                       sheet_name=settings.get("module_validator_lpu.sheet_name_budget_table", 
                                               "Tables"))
    except Exception as e:
        raise ValidatorLPUError(f"Error loading budget: {e}")

    # Validate mandatory columns
    empty_columns = set(required_columns) - set(df.columns)
    if empty_columns:
        raise MissingColumnsError(
            f"Mandatory columns missing in the budget: {', '.join(empty_columns)}"
        )

    # Ensure correct types
    df["cod_item"] = df["cod_item"].astype(str)
    df["unidade"] = df["unidade"].astype(str)
    df["qtde"] = pd.to_numeric(df["qtde"], errors="coerce")
    df["unitario_orcado"] = pd.to_numeric(df["unitario_orcado"], errors="coerce")

    # If total_orcado does not exist, calculate it
    if "total_orcado" not in df.columns:
        df["total_orcado"] = df["qtde"] * df["unitario_orcado"]
    else:
        df["total_orcado"] = pd.to_numeric(df["total_orcado"], errors="coerce")

    return df


def load_lpu(path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads the LPU base file.

    Args:
        path: Path to the LPU file (Excel or CSV)

    Returns:
        DataFrame with the loaded LPU base

    Raises:
        FileNotFoundError: If the file is not found
        MissingColumnsError: If mandatory columns are missing
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"LPU file not found: {path}")

    # Mandatory columns
    mandatory_columns = [
        "cod_item",
        "descricao",
        "unidade",
        "unitario_lpu",
        "fonte",
    ]

    try:
        if path.suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(path)
        elif path.suffix == ".csv":
            df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
        else:
            raise ValidatorLPUError(f"Unsupported format: {path.suffix}")
    except Exception as e:
        raise ValidatorLPUError(f"Error loading LPU: {e}")

    # Validate mandatory columns
    missing_columns = set(mandatory_columns) - set(df.columns)
    if missing_columns:
        raise MissingColumnsError(
            f"Mandatory columns missing in LPU: {', '.join(missing_columns)}"
        )

    # Ensure correct types
    df["cod_item"] = df["cod_item"].astype(str)
    df["unidade"] = df["unidade"].astype(str)
    df["unitario_lpu"] = pd.to_numeric(df["unitario_lpu"], errors="coerce")

    return df


def cross_budget_lpu(budget: pd.DataFrame, lpu: pd.DataFrame) -> pd.DataFrame:
    """
    Merges budget and LPU using cod_item + unidade.

    Args:
        budget: Budget DataFrame
        lpu: LPU base DataFrame

    Returns:
        Combined DataFrame with INNER JOIN

    Raises:
        ValidatorLPUError: If the merge results in an empty DataFrame
    """
    # Merge on cod_item + unidade
    merged_df = pd.merge(
        budget, lpu, on=["cod_item", "unidade"], how="inner", suffixes=("_orc", "_lpu")
    )

    if merged_df.empty:
        raise ValidatorLPUError(
            "No match found between budget and LPU. "
            "Check if cod_item and unidade are consistent."
        )

    # Calculate items not found in LPU
    items_not_in_lpu = len(budget) - len(merged_df)
    if items_not_in_lpu > 0:
        logger.warning(f"⚠️  Attention: {items_not_in_lpu} budget items not found in LPU")

    return merged_df


def calculate_discrepancies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates discrepancies between budget and LPU.

    Adds the columns:
    - valor_total_orcado: qtde * unitario_orcado
    - dif_unitario: unitario_orcado - unitario_lpu
    - dif_total: dif_unitario * qtde
    - perc_dif: (dif_unitario / unitario_lpu) * 100
    - status_conciliacao: discrepancy classification

    Classification rules (tolerance configurable in settings.toml):
    - "OK": -tolerance <= discrepancy <= +tolerance
    - "For reimbursement": discrepancy > +tolerance
    - "Below LPU": discrepancy < -tolerance

    Args:
        df: DataFrame with crossed data

    Returns:
        DataFrame with calculated discrepancy columns
    """
    df = df.copy()

    # Get tolerance from settings
    tolerance = settings.validador_lpu.tolerancia_percentual
    logger.debug(f"Calculating discrepancies with tolerance of {tolerance}%")

    # Calculate total budgeted value (revalidate)
    df["valor_total_orcado"] = df["qtde"] * df["unitario_orcado"]

    # Check consistency of total_orcado if it exists
    if "total_orcado" in df.columns:
        inconsistencies = (abs(df["total_orcado"] - df["valor_total_orcado"]) > 0.01).sum()
        if inconsistencies > 0:
            logger.warning(
                f"⚠️  Attention: {inconsistencies} inconsistencies in total_orcado detected"
            )

    # Calculate differences
    df["dif_unitario"] = df["unitario_orcado"] - df["unitario_lpu"]
    df["dif_total"] = df["dif_unitario"] * df["qtde"]

    # Calculate percentage (handling division by zero)
    df["perc_dif"] = 0.0
    valid_mask = df["unitario_lpu"] != 0
    df.loc[valid_mask, "perc_dif"] = (
        df.loc[valid_mask, "dif_unitario"] / df.loc[valid_mask, "unitario_lpu"]
    ) * 100

    # Classification WITH TOLERANCE (configurable)
    def classify_discrepancy(row):
        perc = row["perc_dif"]
        if -tolerance <= perc <= tolerance:
            return "OK"
        elif perc > tolerance:
            return "For reimbursement"
        else:
            return "Below LPU"

    df["status_conciliacao"] = df.apply(classify_discrepancy, axis=1)

    logger.debug(f"Discrepancies calculated for {len(df)} items")

    # Round values to 2 decimal places
    columns_to_round = [
        "unitario_orcado",
        "unitario_lpu",
        "valor_total_orcado",
        "dif_unitario",
        "dif_total",
        "perc_dif",
    ]
    for col in columns_to_round:
        if col in df.columns:
            df[col] = df[col].round(2)

    return df


def save_results(df: pd.DataFrame, output_dir: Union[str, Path], base_name: str = None) -> None:
    """
    Saves the results in Excel and CSV formats.

    Args:
        df: DataFrame with validation results
        output_dir: Output directory
        base_name: Base name for the files (default configured in settings)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use base name from settings if not provided
    if base_name is None:
        base_name = settings.validador_lpu.arquivo_excel_basico.replace(".xlsx", "")

    logger.debug(f"Saving results to {output_dir}")

    # Define column order
    ordered_columns = [
        "cod_upe",
        "cod_item",
        "nome",
        "categoria",
        "unidade",
        "qtde",
        "unitario_orcado",
        "unitario_lpu",
        "dif_unitario",
        "perc_dif",
        "valor_total_orcado",
        "dif_total",
        "status_conciliacao",
        "fonte",
        "descricao",
        "data_referencia",
        "composicao",
        "fornecedor",
        "observacoes_orc",
        "observacoes_lpu",
    ]

    # Select only existing columns
    existing_columns = [col for col in ordered_columns if col in df.columns]
    output_df = df[existing_columns].copy()

    # Save as Excel with formatting
    excel_filename = settings.validador_lpu.arquivo_excel_basico
    excel_path = output_dir / excel_filename

    logger.debug(f"Generating Excel file: {excel_filename}")

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        # Main sheet with complete validation
        output_df.to_excel(writer, sheet_name="Complete Validation", index=False)

        # Summary sheet by status
        status_summary = (
            df.groupby("status_conciliacao")
            .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
            .reset_index()
        )
        status_summary.columns = ["Status", "Item Count", "Total Difference (R$)", "Total Budgeted Value (R$)"]
        status_summary.to_excel(writer, sheet_name="Status Summary", index=False)

        # Summary sheet by category
        if "categoria" in df.columns:
            category_summary = (
                df.groupby(["categoria", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
            )
            category_summary.columns = ["Category", "Status", "Item Count", "Total Difference (R$)"]
            category_summary.to_excel(writer, sheet_name="Category Summary", index=False)

        # Summary sheet by UPE
        if "cod_upe" in df.columns:
            upe_summary = (
                df.groupby(["cod_upe", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
            )
            upe_summary.columns = ["UPE Code", "Status", "Item Count", "Total Difference (R$)"]
            upe_summary.to_excel(writer, sheet_name="UPE Summary", index=False)

    logger.success(f"✅ Excel saved at: {excel_path}")

    # Save as CSV
    csv_filename = settings.validador_lpu.arquivo_csv
    csv_path = output_dir / csv_filename
    output_df.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
    logger.success(f"✅ CSV saved at: {csv_path}")


def generate_html_report(
    df: pd.DataFrame, output_dir: Union[str, Path], base_name: str = None
) -> None:
    """
    Generates an HTML report for LPU validation.

    Args:
        df (pd.DataFrame): DataFrame containing the validation results.
        output_dir (Union[str, Path]): Directory to save the HTML report.
        base_name (str): Base name for the HTML file. Defaults to None.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use base name from settings if not provided
    if base_name is None:
        base_name = settings.validador_lpu.arquivo_html.replace(".html", "")

    html_path = output_dir / f"{base_name}.html"

    logger.debug(f"Generating HTML report: {base_name}.html")

    # General statistics
    total_items = len(df)
    items_ok = (df["status_conciliacao"] == "OK").sum()
    items_refund = (df["status_conciliacao"] == "Para ressarcimento").sum()
    items_below = (df["status_conciliacao"] == "Abaixo LPU").sum()

    total_value = df["valor_total_orcado"].sum()
    total_divergence = df["dif_total"].sum()
    refund_divergence = df[df["status_conciliacao"] == "Para ressarcimento"]["dif_total"].sum()

    # Top 10 divergences
    df["perc_dif_abs"] = abs(df["perc_dif"])
    top_10_abs = df.nlargest(10, "dif_total")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "dif_total",
            "status_conciliacao",
        ]
    ]
    top_10_perc = df.nlargest(10, "perc_dif_abs")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "perc_dif",
            "dif_total",
            "status_conciliacao",
        ]
    ]

    # Status summary
    status_summary = (
        df.groupby("status_conciliacao")
        .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
        .reset_index()
    )
    status_summary.columns = ["Status", "Item Count", "Total Difference (R$)", "Total Budgeted Value (R$)"]

    # Category summary
    category_summary = None
    if "categoria" in df.columns:
        category_summary = (
            df.groupby(["categoria", "status_conciliacao"])
            .agg({"cod_item": "count", "dif_total": "sum"})
            .reset_index()
        )
        category_summary.columns = ["Category", "Status", "Item Count", "Total Difference (R$)"]

    # UPE summary
    upe_summary = None
    if "cod_upe" in df.columns:
        upe_summary = (
            df.groupby(["cod_upe", "status_conciliacao"])
            .agg({"cod_item": "count", "dif_total": "sum"})
            .reset_index()
        )
        upe_summary.columns = ["UPE Code", "Status", "Item Count", "Total Difference (R$)"]

    # Create HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LPU Validation Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
            display: flex;
            align-items: center;
        }}
        
        .section h2::before {{
            content: '📊';
            margin-right: 10px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-ok {{ color: #28a745; }}
        .stat-warning {{ color: #ffc107; }}
        .stat-danger {{ color: #dc3545; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .status-ok {{
            background: #d4edda;
            color: #155724;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .status-refund {{
            background: #fff3cd;
            color: #856404;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .status-below {{
            background: #f8d7da;
            color: #721c24;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .value-positive {{
            color: #dc3545;
            font-weight: bold;
        }}
        
        .value-negative {{
            color: #28a745;
            font-weight: bold;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #dee2e6;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            .stat-card:hover {{
                transform: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 LPU Validation Report</h1>
            <p>Budget vs Reference Price Base Reconciliation</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Generated on: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <div class="content">
            <!-- GENERAL STATISTICS -->
            <div class="section">
                <h2>General Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">Total Items</div>
                        <div class="stat-value">{total_items}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Items OK</div>
                        <div class="stat-value stat-ok">{items_ok} ({items_ok/total_items*100:.1f}%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">For Refund</div>
                        <div class="stat-value stat-warning">{items_refund} ({items_refund/total_items*100:.1f}%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Below LPU</div>
                        <div class="stat-value stat-danger">{items_below} ({items_below/total_items*100:.1f}%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Budgeted Value</div>
                        <div class="stat-value">R$ {total_value:,.2f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Divergence</div>
                        <div class="stat-value stat-warning">R$ {total_divergence:,.2f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Potential Refund</div>
                        <div class="stat-value stat-danger">R$ {refund_divergence:,.2f}</div>
                    </div>
                </div>
            </div>
            
            <!-- STATUS SUMMARY -->
            <div class="section">
                <h2>Status Summary</h2>
                {status_summary.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>
            
            <!-- TOP 10 ABSOLUTE DIVERGENCES -->
            <div class="section">
                <h2>🔴 Top 10 Largest Absolute Divergences</h2>
                {top_10_abs.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>
            
            <!-- TOP 10 PERCENTUAL DIVERGENCES -->
            <div class="section">
                <h2>📈 Top 10 Largest Percentual Divergences</h2>
                {top_10_perc.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'{x:.2f}%' if 'perc' in str(x) else (f'R$ {x:,.2f}' if pd.notna(x) else ''))}
            </div>
            {"<!-- CATEGORY SUMMARY -->" if category_summary is not None else ""}
            {f'''<div class="section">
                <h2>Category Summary</h2>
                {category_summary.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: 'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>''' if category_summary is not None else ""}
            {"<!-- UPE SUMMARY -->" if upe_summary is not None else ""}
            {f'''<div class="section">
                <h2>UPE Summary</h2>
                {upe_summary.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: 'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>''' if upe_summary is not None else ""}
        </div>
        
        <div class="footer">
            <p>Report automatically generated by the LPU Validator system</p>
            <p style="margin-top: 5px; font-size: 0.9em;">Construct Cost AI - Intelligent Construction Budget Verifier</p>
        </div>
    </div>
</body>
</html>
"""

    # Save HTML
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.success(f"✅ HTML report saved at: {html_path}")


def generate_complete_excel_report(
    df: pd.DataFrame, output_dir: Union[str, Path], base_name: str = None
) -> None:
    """
    Generates a complete Excel report with all analyses in separate sheets.

    Args:
        df: DataFrame with validation results
        output_dir: Output directory
        base_name: Base name for the Excel file (default configured in settings)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use base name from settings if not provided
    if base_name is None:
        base_name = settings.validador_lpu.arquivo_excel_completo.replace(".xlsx", "")

    excel_path = output_dir / f"{base_name}.xlsx"

    logger.debug(f"Generating complete Excel report: {base_name}.xlsx")

    # Prepare data
    df["perc_dif_abs"] = abs(df["perc_dif"])

    # Get top_n configuration from settings
    top_n = settings.validador_lpu.top_n_divergencias
    top_n_extended = settings.validador_lpu.top_n_divergencias_extended

    # Top divergences
    top_10_abs = df.nlargest(top_n, "dif_total")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "dif_total",
            "status_conciliacao",
        ]
    ]
    top_20_abs = df.nlargest(top_n_extended, "dif_total")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "dif_total",
            "status_conciliacao",
        ]
    ]

    top_10_perc = df.nlargest(top_n, "perc_dif_abs")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "perc_dif",
            "dif_total",
            "status_conciliacao",
        ]
    ]
    top_20_perc = df.nlargest(top_n_extended, "perc_dif_abs")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "perc_dif",
            "dif_total",
            "status_conciliacao",
        ]
    ]

    # Statistics
    total_items = len(df)
    items_ok = (df["status_conciliacao"] == "OK").sum()
    items_refund = (df["status_conciliacao"] == "Para ressarcimento").sum()
    items_below = (df["status_conciliacao"] == "Abaixo LPU").sum()

    total_value = df["valor_total_orcado"].sum()
    total_divergence = df["dif_total"].sum()
    refund_divergence = df[df["status_conciliacao"] == "Para ressarcimento"]["dif_total"].sum()

    stats_data = {
        "Metric": [
            "Total Items",
            "Items OK",
            "Items For Refund",
            "Items Below LPU",
            "% OK",
            "% For Refund",
            "% Below LPU",
            "Total Budgeted Value (R$)",
            "Total Divergence (R$)",
            "Potential Refund (R$)",
        ],
        "Value": [
            total_items,
            items_ok,
            items_refund,
            items_below,
            f"{items_ok/total_items*100:.2f}%",
            f"{items_refund/total_items*100:.2f}%",
            f"{items_below/total_items*100:.2f}%",
            f"R$ {total_value:,.2f}",
            f"R$ {total_divergence:,.2f}",
            f"R$ {refund_divergence:,.2f}",
        ],
    }
    df_stats = pd.DataFrame(stats_data)

    # Status summary
    status_summary = (
        df.groupby("status_conciliacao")
        .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
        .reset_index()
    )
    status_summary.columns = ["Status", "Item Count", "Total Difference (R$)", "Total Budgeted Value (R$)"]

    # Items for reimbursement
    items_for_refund = df[df["status_conciliacao"] == "Para ressarcimento"][
        [
            "cod_item",
            "nome",
            "categoria",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "perc_dif",
            "qtde",
            "dif_total",
            "fonte",
        ]
    ].sort_values("dif_total", ascending=False)

    # Items below LPU
    items_below_lpu = df[df["status_conciliacao"] == "Abaixo LPU"][
        [
            "cod_item",
            "nome",
            "categoria",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "perc_dif",
            "qtde",
            "dif_total",
            "fonte",
        ]
    ].sort_values("dif_total")

    # Save as Excel
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        # Sheet 1: General Statistics
        df_stats.to_excel(writer, sheet_name="Statistics", index=False)

        # Sheet 2: Status Summary
        status_summary.to_excel(writer, sheet_name="Status Summary", index=False)

        # Sheet 3: Top 10 Divergences (Value)
        top_10_abs.to_excel(writer, sheet_name="Top 10 Absolute Divergence", index=False)

        # Sheet 4: Top 20 Divergences (Value)
        top_20_abs.to_excel(writer, sheet_name="Top 20 Absolute Divergence", index=False)

        # Sheet 5: Top 10 Divergences (%)
        top_10_perc.to_excel(writer, sheet_name="Top 10 Percentual Divergence", index=False)

        # Sheet 6: Top 20 Divergences (%)
        top_20_perc.to_excel(writer, sheet_name="Top 20 Percentual Divergence", index=False)

        # Sheet 7: Items for Refund
        items_for_refund.to_excel(
            writer, sheet_name="Items For Refund", index=False
        )

        # Sheet 8: Items Below LPU
        items_below_lpu.to_excel(writer, sheet_name="Items Below LPU", index=False)

        # Sheet 9: Category Summary (if exists)
        if "categoria" in df.columns:
            category_summary = (
                df.groupby(["categoria", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
            )
            category_summary.columns = ["Category", "Status", "Item Count", "Total Difference (R$)"]
            category_summary.to_excel(writer, sheet_name="Category Summary", index=False)

            # Total divergence by category
            divergence_by_category = (
                df.groupby("categoria")
                .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
                .reset_index()
                .sort_values("dif_total", ascending=False)
            )
            divergence_by_category.columns = ["Category", "Item Count", "Total Difference (R$)", "Total Value (R$)"]
            divergence_by_category.to_excel(writer, sheet_name="Divergence by Category", index=False)

        # Sheet 10: UPE Summary (if exists)
        if "cod_upe" in df.columns:
            upe_summary = (
                df.groupby(["cod_upe", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
                .sort_values("cod_upe")
            )
            upe_summary.columns = ["UPE Code", "Status", "Item Count", "Total Difference (R$)"]
            upe_summary.to_excel(writer, sheet_name="UPE Summary", index=False)

            # Total divergence by UPE
            divergence_by_upe = (
                df.groupby("cod_upe")
                .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
                .reset_index()
                .sort_values("dif_total", ascending=False)
            )
            divergence_by_upe.columns = ["UPE Code", "Item Count", "Total Difference (R$)", "Total Value (R$)"]
            divergence_by_upe.to_excel(writer, sheet_name="Divergence by UPE", index=False)

        # Sheet 11: Complete Data
        df.to_excel(writer, sheet_name="Complete Data", index=False)

    logger.success(f"✅ Complete Excel report saved at: {excel_path}")


def get_default_settings(key):
    """
    Returns the default values of the LPU validator settings.

    Returns:
        Dictionary with default settings
    """
    return {
        "default_budget_path": settings.validador_lpu.caminho_padrao_orcamento,
        "default_lpu_path": settings.validador_lpu.caminho_padrao_lpu,
        "output_dir": settings.validador_lpu.output_dir,
        "tolerance_percentual": settings.validador_lpu.tolerancia_percentual,
        "basic_excel_file": settings.validador_lpu.arquivo_excel_basico,
        "complete_excel_file": settings.validador_lpu.arquivo_excel_completo,
        "csv_file": settings.validador_lpu.arquivo_csv,
        "html_file": settings.validador_lpu.arquivo_html,
        "top_n_divergences": settings.validador_lpu.top_n_divergencias,
        "top_n_divergences_extended": settings.validador_lpu.top_n_divergencias_extended,
    }


def validate_lpu(
    file_path_budget: Union[str, Path] = None,
    file_path_lpu: Union[str, Path] = None,
    output_dir: Union[str, Path] = None,
    output_file: str = "02_BASE_RESULTADO_VALIDADOR_LPU.xlsx",
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Orchestrator function for LPU validation.

    Performs the entire validation flow:
    1. Loads budget and LPU
    2. Crosses the data (INNER JOIN on cod_item + unidade)
    3. Calculates discrepancies with configurable tolerance
    4. Classifies items (OK, For reimbursement, Below LPU)
    5. Saves results in Excel, CSV, and HTML formats

    Args:
        file_path_budget: Path to the budget file (default in settings)
        file_path_lpu: Path to the LPU file (default in settings)
        output_dir: Directory to save results (default in settings)
        output_file_name: Base name for the output files (without extension)
        verbose: If True, displays statistics on the console

    Returns:
        DataFrame with complete validation results

    Raises:
        ValidatorLPUError: In case of validation error
    """

    if verbose:
        print("-" * 50)
        logger.info("LPU VALIDATOR - Budget vs Price Base Reconciliation")
        logger.info(f"Configured tolerance: {settings.get('module_validator_lpu.tol_percentile')}%")
        print("-" * 50)

    # 1. Load data
    if verbose:
        logger.info("📂 Loading files...")

    try:
        logger.info(f"Loading budget from: {file_path_budget}")
        df_budget = load_budget(file_path_budget)
        if verbose:
            logger.info(f"   ✅ Budget loaded: {len(df_budget)} items")
    except Exception as e:
        logger.error(f"Error loading budget: {e}")
        raise ValidatorLPUError(f"Error loading budget: {e}")

    try:
        logger.debug(f"Loading LPU from: {file_path_lpu}")
        df_lpu = load_lpu(file_path_lpu)
        if verbose:
            logger.info(f"   ✅ LPU loaded: {len(df_lpu)} items")
    except Exception as e:
        logger.error(f"Error loading LPU: {e}")
        raise ValidatorLPUError(f"Error loading LPU: {e}")

    # 2. Cross data
    if verbose:
        logger.info("🔗 Crossing budget with LPU...")

    try:
        df_crossed = cross_budget_lpu(df_budget, df_lpu)
        if verbose:
            logger.info(f"   ✅ Crossed items: {len(df_crossed)}")
    except Exception as e:
        logger.error(f"Error crossing data: {e}")
        raise ValidatorLPUError(f"Error crossing data: {e}")

    if verbose:
        logger.info("")

    # 3. Calculate discrepancies
    if verbose:
        logger.info(
            f"🧮 Calculating discrepancies (tolerance {settings.validador_lpu.tolerancia_percentual}%)..."
        )

    try:
        df_result = calculate_discrepancies(df_crossed)
    except Exception as e:
        logger.error(f"Error calculating discrepancies: {e}")
        raise ValidatorLPUError(f"Error calculating discrepancies: {e}")

    # Statistics
    if verbose:
        logger.info("")
        logger.info("📊 VALIDATION STATISTICS")
        logger.info("-" * 80)

        total_items = len(df_result)
        items_ok = (df_result["status_conciliacao"] == "OK").sum()
        items_refund = (df_result["status_conciliacao"] == "Para ressarcimento").sum()
        items_below = (df_result["status_conciliacao"] == "Abaixo LPU").sum()

        logger.info(f"   Total items validated: {total_items}")
        logger.info(f"   ✅ OK: {items_ok} ({items_ok/total_items*100:.1f}%)")
        logger.info(
            f"   ⚠️  For reimbursement: {items_refund} ({items_refund/total_items*100:.1f}%)"
        )
        logger.info(f"   📉 Below LPU: {items_below} ({items_below/total_items*100:.1f}%)")
        logger.info("")

        total_budgeted_value = df_result["valor_total_orcado"].sum()
        total_divergence = df_result["dif_total"].sum()
        refund_divergence = df_result[
            df_result["status_conciliacao"] == "Para ressarcimento"
        ]["dif_total"].sum()

        logger.info(f"   💰 Total budgeted value: R$ {total_budgeted_value:,.2f}")
        logger.info(f"   💵 Total divergence: R$ {total_divergence:,.2f}")
        logger.info(f"   💸 Potential refund: R$ {refund_divergence:,.2f}")
        logger.info("")

    # Register statistics in logger
    logger.debug("📊 VALIDATION STATISTICS")
    total_items = len(df_result)
    items_ok = (df_result["status_conciliacao"] == "OK").sum()
    items_refund = (df_result["status_conciliacao"] == "Para ressarcimento").sum()
    items_below = (df_result["status_conciliacao"] == "Abaixo LPU").sum()

    logger.debug(f"Total items validated: {total_items}")
    logger.debug(f"✅ OK: {items_ok} ({items_ok/total_items*100:.1f}%)")
    logger.debug(
        f"⚠️  For reimbursement: {items_refund} ({items_refund/total_items*100:.1f}%)"
    )
    logger.debug(f"📉 Below LPU: {items_below} ({items_below/total_items*100:.1f}%)")

    total_budgeted_value = df_result["valor_total_orcado"].sum()
    total_divergence = df_result["dif_total"].sum()
    refund_divergence = df_result[df_result["status_conciliacao"] == "Para ressarcimento"][
        "dif_total"
    ].sum()

    logger.debug(f"💰 Total budgeted value: R$ {total_budgeted_value:,.2f}")
    logger.debug(f"💵 Total divergence: R$ {total_divergence:,.2f}")
    logger.debug(f"💸 Potential refund: R$ {refund_divergence:,.2f}")

    # 4. Save results
    if verbose:
        logger.info("")
        logger.info("💾 Saving results...")

    try:
        # Save basic format (4 sheets)
        save_results(df_result, output_dir)

        # Save complete report in Excel (11+ sheets)
        generate_complete_excel_report(df_result, output_dir)

        # Save HTML report
        generate_html_report(df_result, output_dir)

    except Exception as e:
        logger.error(f"Error saving results: {e}")
        raise ValidatorLPUError(f"Error saving results: {e}")

    if verbose:
        logger.info("")
        logger.info("=" * 80)
        logger.success("✅ VALIDATION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)

    logger.debug("=" * 80)
    logger.success("✅ VALIDATION COMPLETED SUCCESSFULLY!")
    logger.debug("=" * 80)

    return df_result


def orchestrate_validate_lpu(
    file_path_budget: Union[str, Path] = None,
    file_path_lpu: Union[str, Path] = None,
    output_dir: Union[str, Path] = None,
    output_file: str = None,
    verbose: bool = True,
) -> int:
    """
    Main function for direct module execution or external calling.

    Args:
        file_path_budget: Path to the budget file (default in settings if None).
        file_path_lpu: Path to the LPU file (default in settings if None).
        output_dir: Directory to save results (default in settings if None).
        output_file: Base name for the output files (default in settings if None).
        verbose: If True, displays statistics on the console.

    Returns:
        int: Status code (0 for success, 1 for error).
    """
    # Configure default paths if not provided
    base_dir = Path(__file__).parents[5]
    path_file_budget = Path(base_dir, file_path_budget or settings.get("module_validator_lpu.file_path_budget"))
    path_file_lpu = Path(base_dir, file_path_lpu or settings.get("module_validator_lpu.file_path_lpu"))
    output_dir = Path(base_dir, output_dir or settings.get("module_validator_lpu.output_dir"))
    output_file = output_file or settings.get("module_validator_lpu.file_path_output")

    logger.debug(f"Budget: {path_file_budget}")
    logger.debug(f"LPU: {path_file_lpu}")
    logger.debug(f"Output: {output_dir}")

    try:
        df_result = validate_lpu(
            file_path_budget=path_file_budget,
            file_path_lpu=path_file_lpu,
            output_dir=output_dir,
            output_file=output_file,
            verbose=verbose,
        )

        # Display first rows
        if verbose:
            logger.info("\n📋 RESULTS PREVIEW:")
            logger.info("-" * 80)
            preview_columns = [
                "cod_item",
                "nome",
                "unidade",
                "qtde",
                "unitario_orcado",
                "unitario_lpu",
                "dif_unitario",
                "perc_dif",
                "status_conciliacao",
            ]
            preview_columns = [col for col in preview_columns if col in df_result.columns]
            logger.info(f"\n{df_result[preview_columns].head(10).to_string(index=False)}")

        logger.success("Main execution completed successfully!")
        return 0

    except ValidatorLPUError as e:
        logger.error(f"ERROR: {e}")
        return 1
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(orchestrate_validate_lpu())

"""Deterministic, descriptive price-versus-cost diagnostic for the review demo.

This calculates observed comparisons only; it does not infer why pricing decisions
occurred or establish external causality.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = (
    "month",
    "product",
    "purchase_cost_per_kg",
    "selling_price_per_kg",
    "quantity_sold_kg",
)


def diagnose_price_cost(frame: pd.DataFrame) -> dict[str, Any]:
    """Compare quantity-weighted price/cost rates per product over reported periods."""
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("Expected a parsed pandas DataFrame.")
    if not frame.columns.is_unique:
        raise ValueError("Column names must be unique.")
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        return {
            "status": "needs_data",
            "summary": "A price-versus-cost diagnostic cannot be calculated from this dataset yet.",
            "missing_columns": missing,
            "records": [],
            "product_findings": [],
            "limitations": ["No cause has been inferred."],
        }

    work = frame.loc[:, list(REQUIRED_COLUMNS)].copy()
    input_rows = int(len(work))
    for column in ("purchase_cost_per_kg", "selling_price_per_kg", "quantity_sold_kg"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    numeric = work[["purchase_cost_per_kg", "selling_price_per_kg", "quantity_sold_kg"]].to_numpy(dtype=float)
    valid_numeric = np.isfinite(numeric).all(axis=1)
    valid = (
        work["month"].notna()
        & work["product"].notna()
        & valid_numeric
        & work["purchase_cost_per_kg"].ge(0)
        & work["selling_price_per_kg"].ge(0)
        & work["quantity_sold_kg"].gt(0)
    )
    work = work.loc[valid].copy()
    usable_rows = int(len(work))
    if work.empty:
        return {
            "status": "needs_data",
            "summary": "No rows had valid periods, products, non-negative prices/costs and positive quantities.",
            "missing_columns": [],
            "input_rows": input_rows,
            "usable_rows": 0,
            "excluded_rows": input_rows,
            "records": [],
            "product_findings": [],
            "limitations": ["No price trend or cause can be determined from the remaining rows."],
        }

    work["_selling_weighted"] = work["selling_price_per_kg"] * work["quantity_sold_kg"]
    work["_purchase_weighted"] = work["purchase_cost_per_kg"] * work["quantity_sold_kg"]
    grouped = (
        work.groupby(["product", "month"], dropna=False, sort=False)
        .agg(
            quantity_sold_kg=("quantity_sold_kg", "sum"),
            selling_total=("_selling_weighted", "sum"),
            purchase_total=("_purchase_weighted", "sum"),
            source_rows=("product", "size"),
        )
        .reset_index()
    )
    grouped["selling_price_per_kg"] = grouped["selling_total"] / grouped["quantity_sold_kg"]
    grouped["purchase_cost_per_kg"] = grouped["purchase_total"] / grouped["quantity_sold_kg"]
    grouped["spread_per_kg"] = grouped["selling_price_per_kg"] - grouped["purchase_cost_per_kg"]
    grouped["gross_margin_percent"] = np.where(
        grouped["selling_price_per_kg"] > 0,
        grouped["spread_per_kg"] / grouped["selling_price_per_kg"] * 100.0,
        np.nan,
    )
    grouped["_parsed_month"] = pd.to_datetime(grouped["month"], errors="coerce", utc=True)
    grouped["_month_label"] = grouped["month"].astype(str)
    grouped = grouped.sort_values(
        ["product", "_parsed_month", "_month_label"],
        kind="mergesort",
        na_position="last",
    )

    records: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for _, row in grouped.iterrows():
        values = {
            "month": row["_month_label"],
            "product": str(row["product"]),
            "quantity_sold_kg": float(row["quantity_sold_kg"]),
            "purchase_cost_per_kg": float(row["purchase_cost_per_kg"]),
            "selling_price_per_kg": float(row["selling_price_per_kg"]),
            "spread_per_kg": float(row["spread_per_kg"]),
            "gross_margin_percent": None if not np.isfinite(row["gross_margin_percent"]) else float(row["gross_margin_percent"]),
            "source_rows": int(row["source_rows"]),
        }
        records.append({
            key: (round(value, 4) if isinstance(value, float) and np.isfinite(value) else value)
            for key, value in values.items()
        })

    for product, subset in grouped.groupby("product", sort=False, dropna=False):
        if len(subset) < 2:
            findings.append({
                "product": str(product),
                "status": "insufficient_periods",
                "finding": "At least two reported periods are needed to compare a change.",
            })
            continue
        first = subset.iloc[0]
        last = subset.iloc[-1]
        sell_change = float(last["selling_price_per_kg"] - first["selling_price_per_kg"])
        cost_change = float(last["purchase_cost_per_kg"] - first["purchase_cost_per_kg"])
        spread_change = float(last["spread_per_kg"] - first["spread_per_kg"])
        if sell_change > 0 and cost_change < 0 and spread_change > 0:
            finding = (
                f"For {product}, the quantity-weighted selling-price rate increased by "
                f"{sell_change:.2f} per kg while the purchase-cost proxy decreased by "
                f"{abs(cost_change):.2f} per kg; the observed price-cost spread widened by "
                f"{spread_change:.2f} per kg between {first['_month_label']} and {last['_month_label']}."
            )
            status = "price_up_cost_down_spread_up"
        elif sell_change > 0 and cost_change <= 0:
            finding = (
                f"For {product}, the selling-price rate increased by {sell_change:.2f} per kg "
                f"while the purchase-cost proxy was flat or lower over the selected endpoints. "
                f"The observed spread changed by {spread_change:.2f} per kg."
            )
            status = "price_up_cost_flat_or_down"
        else:
            finding = (
                f"For {product}, selling price changed by {sell_change:.2f} per kg, "
                f"purchase-cost proxy changed by {cost_change:.2f} per kg, and the spread "
                f"changed by {spread_change:.2f} per kg between the selected endpoints."
            )
            status = "mixed_or_other_change"
        findings.append({
            "product": str(product),
            "status": status,
            "first_period": str(first["_month_label"]),
            "last_period": str(last["_month_label"]),
            "selling_price_change_per_kg": round(sell_change, 4),
            "purchase_cost_change_per_kg": round(cost_change, 4),
            "spread_change_per_kg": round(spread_change, 4),
            "finding": finding,
        })

    diverging = sum(item["status"] == "price_up_cost_down_spread_up" for item in findings)
    summary = (
        f"Observed {diverging} product(s) with rising selling-price rates, declining purchase-cost proxies, "
        "and a widening price-cost spread across the available endpoints. This describes the supplied data; "
        "it does not establish the business reason or an external cause."
        if diverging
        else "The available records do not show a price-up/cost-down/spread-up pattern for every product. Review the product-level changes and data coverage before interpreting the trend."
    )
    return {
        "status": "ok",
        "summary": summary,
        "input_rows": input_rows,
        "usable_rows": usable_rows,
        "excluded_rows": input_rows - usable_rows,
        "weighting": "Per product and period, price and cost rates are weighted by reported quantity_sold_kg.",
        "records": records,
        "product_findings": findings,
        "limitations": [
            "The output describes observed changes; it does not prove why selling prices changed.",
            "Purchase cost weighted by quantity sold is only a proxy unless the source rows reliably link cost to the inventory actually sold.",
            "Freight, taxes, discounts, returns, inventory-lot costing, supplier terms and external market prices are not accounted for unless represented in the source data.",
            "Product comparisons are separated to avoid treating changes in product mix as a single-product price trend.",
        ],
    }

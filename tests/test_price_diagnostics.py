import pandas as pd

from app.diagnostics import diagnose_price_cost


def sample():
    return pd.DataFrame({
        "month": ["2026-01", "2026-02", "2026-01", "2026-02"],
        "product": ["Rice A", "Rice A", "Rice B", "Rice B"],
        "purchase_cost_per_kg": [42, 39, 58, 55],
        "selling_price_per_kg": [48, 58, 68, 78],
        "quantity_sold_kg": [100, 120, 50, 60],
    })


def test_diagnostic_detects_observed_price_up_cost_down_pattern():
    result = diagnose_price_cost(sample())
    assert result["status"] == "ok"
    assert result["usable_rows"] == 4
    assert len(result["product_findings"]) == 2
    for item in result["product_findings"]:
        assert item["status"] == "price_up_cost_down_spread_up"
        assert item["selling_price_change_per_kg"] > 0
        assert item["purchase_cost_change_per_kg"] < 0
        assert item["spread_change_per_kg"] > 0
    assert "does not establish" in result["summary"]


def test_missing_columns_are_reported_without_guessing():
    result = diagnose_price_cost(pd.DataFrame({"sales": [100]}))
    assert result["status"] == "needs_data"
    assert "purchase_cost_per_kg" in result["missing_columns"]
    assert not result["records"]


def test_invalid_prices_and_quantities_are_excluded():
    frame = sample()
    frame.loc[0, "selling_price_per_kg"] = "invalid"
    frame.loc[1, "quantity_sold_kg"] = 0
    result = diagnose_price_cost(frame)
    assert result["status"] == "ok"
    assert result["excluded_rows"] == 2
    assert result["usable_rows"] == 2


def test_single_period_does_not_claim_a_change():
    frame = sample().iloc[[0, 2]]
    result = diagnose_price_cost(frame)
    assert result["status"] == "ok"
    assert all(item["status"] == "insufficient_periods" for item in result["product_findings"])

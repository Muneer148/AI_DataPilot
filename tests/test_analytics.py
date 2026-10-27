from dataclasses import dataclass

import numpy as np
import pandas as pd
import pytest

from src.analytics import AnalyticsError, aggregate_dataset, correlate_dataset, describe_dataset, detect_outliers, trend_dataset


def sales_frame():
    return pd.DataFrame({
        "region": ["East", "West", "East", "West", "North"],
        "sales": [10.0, 20.0, 30.0, np.nan, 40.0],
        "units": [1, 2, 3, 4, 5],
        "when": ["2025-01-01", "2025-01-02", "2025-02-01", "bad-date", "2025-02-15"],
    })


@dataclass
class Provenance:
    source_name: str = "sales.csv"
    def to_dict(self):
        return {"source_name": self.source_name}


@dataclass
class PreparedDataset:
    dataframe: pd.DataFrame
    provenance: Provenance
    validation: object | None = None
    source_validation: object | None = None


def test_describe_known_values_missingness_and_no_mutation():
    df = sales_frame()
    before = df.copy(deep=True)
    result = describe_dataset(df, columns=["sales"])
    rec = result.records[0]
    assert result.row_count == 5
    assert rec["non_null_count"] == 4
    assert rec["missing_count"] == 1
    assert rec["missing_ratio"] == pytest.approx(0.2)
    assert rec["numeric_count"] == 4
    assert rec["sum"] == pytest.approx(100)
    assert rec["mean"] == pytest.approx(25)
    assert rec["median"] == pytest.approx(25)
    assert rec["quantiles"]["0.5"] == pytest.approx(25)
    pd.testing.assert_frame_equal(df, before)


def test_describe_excludes_infinity_and_does_not_convert_strings():
    result = describe_dataset(pd.DataFrame({"n": [1.0, np.inf, -np.inf, np.nan], "text": ["1", "2", None, "4"]}))
    assert result.records[0]["numeric_count"] == 1
    assert result.records[0]["non_finite_count"] == 2
    assert result.records[0]["sum"] == 1
    assert result.records[1]["numeric_count"] is None
    assert result.records[1]["sum"] is None
    assert any("infinite" in warning for warning in result.warnings)


def test_describe_empty_invalid_quantile_columns_and_duplicate_labels():
    assert describe_dataset(pd.DataFrame({"v": pd.Series(dtype=float)})).records[0]["mean"] is None
    with pytest.raises(AnalyticsError, match="Unknown column"):
        describe_dataset(sales_frame(), columns=["missing"])
    with pytest.raises(AnalyticsError, match="quantiles"):
        describe_dataset(sales_frame(), quantiles=[-0.1])
    with pytest.raises(AnalyticsError) as error:
        describe_dataset(pd.DataFrame([[1, 2]], columns=["x", "x"]))
    assert error.value.code == "DUPLICATE_COLUMNS"


def test_prepared_contract_and_provenance_are_supported():
    result = describe_dataset(PreparedDataset(pd.DataFrame({"x": [1, 2]}), Provenance()))
    assert result.provenance == {"source_name": "sales.csv"}
    assert result.records[0]["sum"] == 3


def test_aggregation_group_sort_top_n_and_missing_group():
    df = pd.DataFrame({"region": ["East", "West", "East", None], "sales": [10, 20, 30, 40]})
    result = aggregate_dataset(df, group_by=["region"], aggregations={"sales": ["sum", "mean", "count"]}, sort_by="sales__sum", ascending=False, limit=2)
    assert result.row_count == 4
    assert result.metrics["group_count"] == 3
    assert len(result.records) == 2
    assert result.records[0]["region"] == "East"
    assert result.records[0]["sales__sum"] == 40
    assert result.records[0]["row_count"] == 2
    assert result.records[1]["region"] is None
    assert any("limited" in warning for warning in result.warnings)


def test_aggregation_filters_and_empty_global_result():
    result = aggregate_dataset(sales_frame(), group_by=["region"], aggregations={"sales": "sum"}, filters=[{"column": "sales", "operator": "gte", "value": 20}], sort_by="sales__sum", ascending=False)
    assert result.row_count == 3
    assert result.records[0]["region"] == "North"
    assert result.records[0]["sales__sum"] == 40
    empty = aggregate_dataset(pd.DataFrame({"v": [1, 2]}), aggregations={"v": ["sum", "mean", "count"]}, filters=[{"column": "v", "operator": "gt", "value": 99}])
    assert empty.row_count == 0
    assert empty.records == [{"row_count": 0, "v__sum": None, "v__mean": None, "v__count": 0}]


def test_aggregation_rejects_bad_requests_and_excludes_infinity_from_numeric_ops():
    df = pd.DataFrame({"label": ["a", "b"], "v": [1.0, np.inf]})
    with pytest.raises(AnalyticsError, match="Unknown column"):
        aggregate_dataset(df, group_by=["nope"])
    with pytest.raises(AnalyticsError, match="requires a real numeric"):
        aggregate_dataset(df, aggregations={"label": "mean"})
    with pytest.raises(AnalyticsError, match="Unsupported aggregation"):
        aggregate_dataset(df, aggregations={"v": "variance"})
    with pytest.raises(AnalyticsError, match="sort_by"):
        aggregate_dataset(df, aggregations={"v": "sum"}, sort_by="missing")
    result = aggregate_dataset(pd.DataFrame({"g": ["a", "a"], "v": [1.0, np.inf]}), group_by=["g"], aggregations={"v": ["sum", "count"]})
    assert result.records[0]["v__sum"] == 1
    assert result.records[0]["v__count"] == 2


def test_correlation_pairwise_counts_constant_column_and_non_numeric_rejection():
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [2, 4, 6, 8], "constant": [1, 1, 1, 1], "label": ["a", "b", "c", "d"]})
    result = correlate_dataset(df)
    xy = next(r for r in result.records if {r["column_a"], r["column_b"]} == {"x", "y"})
    assert xy["correlation"] == pytest.approx(1)
    assert xy["sample_size"] == 4
    assert any(r["correlation"] is None for r in result.records)
    assert any("constant" in warning for warning in result.warnings)
    with pytest.raises(AnalyticsError, match="real numeric"):
        correlate_dataset(df, columns=["label"])


def test_correlation_insufficient_sample_and_methods():
    result = correlate_dataset(pd.DataFrame({"x": [1, None], "y": [2, 4]}))
    assert result.records[0]["sample_size"] == 1
    assert result.records[0]["correlation"] is None
    with pytest.raises(AnalyticsError, match="method"):
        correlate_dataset(pd.DataFrame({"x": [1, 2], "y": [2, 3]}), method="invalid")


def test_trend_buckets_timezone_and_invalid_timestamp_warning():
    df = pd.DataFrame({"date": ["2025-01-01", "2025-01-15", "2025-02-01", "bad-date"], "sales": [10, 20, 30, 100]})
    result = trend_dataset(df, time_column="date", value_column="sales", interval="month", aggregation="sum")
    assert result.row_count == 3
    assert len(result.records) == 2
    assert result.records[0]["value"] == 30
    assert result.records[1]["value"] == 30
    assert any("invalid" in warning for warning in result.warnings)


def test_trend_rejects_bad_interval_and_non_numeric_measure():
    df = pd.DataFrame({"date": ["2025-01-01"], "measure": ["one"]})
    with pytest.raises(AnalyticsError, match="real numeric"):
        trend_dataset(df, time_column="date", value_column="measure")
    with pytest.raises(AnalyticsError, match="interval"):
        trend_dataset(pd.DataFrame({"date": ["2025-01-01"], "v": [1]}), time_column="date", value_column="v", interval="decade")


def test_outliers_iqr_zscore_zero_variance_and_bounding():
    df = pd.DataFrame({"value": [10.0, 11.0, 12.0, 13.0, 1000.0]})
    result = detect_outliers(df, column="value", method="iqr")
    assert result.records[0]["row_position"] == 4
    assert result.records[0]["side"] == "high"
    zscore = detect_outliers(df, column="value", method="zscore", threshold=1.0, max_results=1)
    assert zscore.metrics["candidate_count"] >= 1
    assert len(zscore.records) == 1
    zero = detect_outliers(pd.DataFrame({"value": [5, 5, 5]}), column="value", method="zscore")
    assert zero.records == []
    assert any("zero variance" in warning for warning in zero.warnings)


def test_outliers_reject_non_numeric_and_results_are_strict_json():
    with pytest.raises(AnalyticsError, match="real numeric"):
        detect_outliers(pd.DataFrame({"value": ["x", "y"]}), column="value")
    result = describe_dataset(pd.DataFrame({"value": [1.0, np.inf, np.nan]}))
    assert "Infinity" not in result.to_json()
    assert "NaN" not in result.to_json()


def test_contains_filter_rejects_all_null_non_string_column_cleanly():
    from src.analytics import aggregate_dataset
    with pytest.raises(AnalyticsError, match="contains filters"):
        aggregate_dataset(
            pd.DataFrame({"label": pd.Series([None, None], dtype=object), "value": [1, 2]}),
            group_by=["label"],
            filters=[{"column": "label", "operator": "contains", "value": "a"}],
        )


def test_correlation_pair_output_is_bounded():
    frame = pd.DataFrame({f"c{i}": [1.0, 2.0, 4.0] for i in range(50)})
    result = correlate_dataset(frame, max_pairs=10)
    assert result.metrics["pair_count"] == 50 * 49 // 2
    assert result.metrics["returned_pair_count"] == 10
    assert len(result.records) == 10
    assert any("only the first 10 pairs" in warning for warning in result.warnings)


def test_trend_rejects_numeric_timestamp_input():
    frame = pd.DataFrame({"timestamp": [1, 2], "value": [10, 20]})
    with pytest.raises(AnalyticsError, match="numeric values"):
        trend_dataset(frame, time_column="timestamp", value_column="value")


def test_malformed_aggregation_operations_and_filter_values_are_rejected_cleanly():
    frame = pd.DataFrame({"region": ["East", "West"], "sales": [10, 20]})
    with pytest.raises(AnalyticsError, match="must be strings"):
        aggregate_dataset(frame, aggregations={"sales": [["sum"]]})
    with pytest.raises(AnalyticsError, match="Unsupported filter operator"):
        aggregate_dataset(frame, filters=[{"column": "region", "operator": ["eq"], "value": "East"}])
    with pytest.raises(AnalyticsError, match="filters must be"):
        aggregate_dataset(frame, filters=42)
    with pytest.raises(AnalyticsError, match="Comparison filter values must be scalar"):
        aggregate_dataset(frame, filters=[{"column": "sales", "operator": "gt", "value": [2, 3]}])
    with pytest.raises(AnalyticsError, match="sort_by"):
        aggregate_dataset(frame, aggregations={"sales": "sum"}, sort_by=["sales__sum"])


def test_all_filter_operators_have_defined_null_semantics():
    frame = pd.DataFrame({
        "label": ["alpha", "beta", None, "alphaX"],
        "amount": [1, 2, 3, 4],
    })
    cases = [
        ({"column": "label", "operator": "eq", "value": "alpha"}, 1),
        ({"column": "label", "operator": "ne", "value": "alpha"}, 6),
        ({"column": "amount", "operator": "gt", "value": 2}, 7),
        ({"column": "amount", "operator": "gte", "value": 2}, 9),
        ({"column": "amount", "operator": "lt", "value": 3}, 3),
        ({"column": "amount", "operator": "lte", "value": 3}, 6),
        ({"column": "label", "operator": "in", "value": ["alpha", "beta"]}, 3),
        ({"column": "label", "operator": "not_in", "value": ["alpha", "beta"]}, 4),
        ({"column": "label", "operator": "is_null"}, 3),
        ({"column": "label", "operator": "not_null"}, 7),
        ({"column": "label", "operator": "contains", "value": "alpha"}, 5),
    ]
    for filter_spec, expected_sum in cases:
        result = aggregate_dataset(frame, aggregations={"amount": "sum"}, filters=[filter_spec])
        assert result.records[0]["amount__sum"] == expected_sum, filter_spec


@pytest.mark.parametrize("method", ["spearman", "kendall"])
def test_rank_correlations_return_expected_monotonic_relationship(method):
    frame = pd.DataFrame({"x": [1, 2, 3, 4], "y": [1, 4, 9, 16]})
    result = correlate_dataset(frame, method=method)
    assert result.records[0]["correlation"] == pytest.approx(1.0)
    with pytest.raises(AnalyticsError, match="method"):
        correlate_dataset(frame, method=["pearson"])


def test_trend_reports_missing_measures_separately_and_rejects_bad_timezone():
    frame = pd.DataFrame({
        "date": ["2025-01-01", "2025-01-02", "2025-02-01"],
        "sales": [10.0, np.nan, 30.0],
    })
    result = trend_dataset(frame, time_column="date", value_column="sales", interval="month")
    assert result.row_count == 2
    assert any("1 row(s) had missing measures" in warning for warning in result.warnings)
    with pytest.raises(AnalyticsError, match="timezone"):
        trend_dataset(frame, time_column="date", value_column="sales", timezone="Not/AZone")
    with pytest.raises(AnalyticsError, match="interval"):
        trend_dataset(frame, time_column="date", value_column="sales", interval=["month"])


def test_single_value_iqr_analysis_warns_about_small_sample():
    result = detect_outliers(pd.DataFrame({"value": [7.0]}), column="value", method="iqr")
    assert result.records == []
    assert result.metrics["sample_size"] == 1
    assert any("At least two finite observations" in warning for warning in result.warnings)


def test_correlation_column_and_pair_limits_are_bounded():
    frame = pd.DataFrame({f"c{i}": [1.0, 2.0, 4.0] for i in range(20)})
    result = correlate_dataset(frame, max_columns=10, max_pairs=5)
    assert len(result.columns) == 10
    assert result.metrics["pair_count"] == 45
    assert result.metrics["returned_pair_count"] == 5
    assert result.parameters["max_columns"] == 10
    assert any("Only the first 10" in warning for warning in result.warnings)
    assert any("only the first 5 pairs" in warning for warning in result.warnings)


def test_missing_scalar_filters_require_explicit_null_operators():
    frame = pd.DataFrame({"value": [1.0, np.nan, 2.0]})
    for missing in (None, np.nan, pd.NA, pd.NaT):
        with pytest.raises(AnalyticsError, match="Use is_null"):
            aggregate_dataset(
                frame,
                aggregations={"value": "count"},
                filters=[{"column": "value", "operator": "eq", "value": missing}],
            )

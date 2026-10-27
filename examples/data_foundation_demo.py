"""Preview-first CLI demonstration for AI_DataPilot's data foundation.

Run from the repository root:
    python -m examples.data_foundation_demo
    python -m examples.data_foundation_demo --prepare
    python -m examples.data_foundation_demo path/to/data.csv --required-column sales
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Sequence

import pandas as pd

from src.data import CleaningConfig, prepare_file, preview_file


def _write_sample_csv(path: Path) -> None:
    """Create a deterministic synthetic dataset for a safe, repeatable demo."""
    sample = pd.DataFrame(
        {
            " region ": ["East", "West", "East", None],
            "sales": [120.0, 80.0, 200.0, None],
            " note ": ["priority", "   ", "repeat", None],
        }
    )
    sample.to_csv(path, index=False)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect a dataset, review proposed cleaning and optionally prepare "
            "an AnalysisReadyDataset. A synthetic CSV is used when no path is supplied."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="CSV, XLSX, XLS or JSON file to inspect; defaults to a synthetic sample.",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Prepare the dataset only if the preview passes output validation.",
    )
    parser.add_argument(
        "--required-column",
        action="append",
        default=[],
        metavar="NAME",
        help="Column required after cleaning; may be supplied more than once.",
    )
    parser.add_argument(
        "--max-missing-ratio",
        type=float,
        default=0.5,
        help="Maximum allowed missing-value ratio per output column (default: 0.5).",
    )
    parser.add_argument(
        "--max-model-columns",
        type=int,
        default=100,
        help="Maximum columns included in bounded model context (default: 100).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the preview-first demonstration and return a shell exit code."""
    args = _build_parser().parse_args(argv)
    config = CleaningConfig()

    with tempfile.TemporaryDirectory(prefix="aidatapilot-demo-") as temp_dir:
        if args.path:
            source_path = Path(args.path).expanduser()
            required_columns = args.required_column
        else:
            source_path = Path(temp_dir) / "sample_sales.csv"
            _write_sample_csv(source_path)
            required_columns = args.required_column or ["sales", "region"]

        try:
            preview = preview_file(
                source_path,
                config=config,
                required_columns=required_columns or None,
                max_missing_ratio=args.max_missing_ratio,
            )
            payload: dict[str, object] = {
                "stage": "preview",
                "source_file": source_path.name,
                "ready": preview.ready,
                "preview": preview.to_dict(include_value_examples=False),
                "prepared": False,
            }

            if args.prepare:
                if not preview.ready:
                    payload["message"] = (
                        "Preparation blocked: review the output validation findings, "
                        "adjust the input or configuration, then preview again."
                    )
                    print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))
                    return 2

                dataset = prepare_file(
                    source_path,
                    config=config,
                    required_columns=required_columns or None,
                    max_missing_ratio=args.max_missing_ratio,
                )
                payload["stage"] = "prepared"
                payload["prepared"] = True
                payload["dataset"] = {
                    "rows": dataset.rows,
                    "columns": dataset.columns,
                    "validation": dataset.validation.to_dict(),
                    "cleaning": dataset.cleaning.to_dict(),
                    "provenance": (
                        dataset.provenance.to_dict() if dataset.provenance is not None else None
                    ),
                    "model_context": dataset.to_model_context(
                        max_columns=args.max_model_columns
                    ),
                }
            else:
                payload["next_step"] = (
                    "Review the preview first. Re-run with --prepare only after accepting "
                    "the proposed transformations."
                )

            print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))
            return 0
        except (OSError, TypeError, ValueError) as exc:
            error_payload = {
                "error": str(exc),
                "source_file": source_path.name,
            }
            print(
                json.dumps(error_payload, indent=2, ensure_ascii=False),
                file=sys.stderr,
            )
            return 2


if __name__ == "__main__":
    raise SystemExit(main())

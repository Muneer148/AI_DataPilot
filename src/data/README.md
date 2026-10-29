# Member 1 — Data foundation

This package owns file ingestion, schema inference, data quality validation, conservative cleaning, profiling, provenance, and the `AnalysisReadyDataset` contract consumed by the agent and analytics modules.

## Public API

- `DataLoader.load(path)`: load a supported local file.
- `DataLoader.load_bytes(filename, content)`: parse a bounded upload from bytes without writing it to disk.
- `preview_dataframe(df, ...)`: report source quality and a proposed cleaned copy without mutating the input.
- `preview_file(path, ...)`: load and preview a local file.
- `prepare_dataset(df, ...)`: produce the stable analysis-ready contract.
- `prepare_file(path, ...)`: load and prepare a local file.
- `validate_dataframe`, `clean_dataframe`, `infer_schema`, and `profile_dataframe`: deterministic building blocks.

Supported formats: CSV, XLSX, XLS, and JSON. Excel parsing requires the declared `openpyxl` and `xlrd` engines. Upload callers must apply a smaller application-specific byte limit where appropriate; the loader's default local-file limit is 100 MiB.

## Contract and safety

- Cleaning works on a copy and emits an audit report. Duplicate records are retained by default because repeated events may be legitimate.
- A preview is non-destructive. The caller must explicitly approve cleaning before using the prepared dataset for analysis.
- Profile examples/top values are omitted from serialized data and model context by default because they can contain sensitive values.
- `to_model_context()` is bounded and excludes raw rows and value examples unless explicitly enabled.
- Duplicate counts are represented as unknown when the dataframe library cannot safely compute them; skipped checks are exposed as status fields or validation warnings rather than reported as zero.
- Column rename details include column positions to disambiguate repeated original labels.
- Provenance records the basename, format, byte size where available, input/output shape, and cleaning configuration. It does not store the source rows.
- This module does not itself provide authentication, multi-user isolation, persistent storage, or authorization.

## Test

From the repository root:

```bash
python -m pytest -q
```

The tests use synthetic data and temporary fixtures. They should not require real customer datasets or live model credentials.

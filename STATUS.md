# AIQuantLab Status

Last updated: 2026-08-06

## Current Milestone

Phase 0-1: architecture contracts and data foundation.

## Completed

- Established the `src/aiquantlab` package layout and requested research directories.
- Defined supported timeframes and dataset provenance metadata.
- Added strict YAML source configuration and CSV column mapping.
- Added UTC timestamp normalization without silent sorting or deduplication.
- Added canonical OHLCV validation and structured quality reports.
- Added missing-candle detection with continuous, weekday, and disabled-inference policies.
- Added anchored OHLCV timeframe conversion with incomplete boundary removal.
- Added processed Parquet manifests with checksums and provenance.
- Added focused unit tests using small synthetic datasets.

## Verification

- `python -m pytest`: 13 passed.
- `python -m pytest --cov=aiquantlab --cov-report=term-missing`: 88% total coverage.
- `python -m compileall -q src tests`: passed.
- Strict project type checking reports no internal issues when unavailable third-party stubs are
  excluded; `pandas-stubs` and `types-PyYAML` are declared in the development dependencies.
- Ruff is declared as a development dependency but was not installed in the current interpreter.

## Important Decisions

- Canonical timestamps are timezone-aware UTC values.
- Candle timestamps default to bar-open time and must be labeled explicitly in metadata.
- Missing-candle results are warnings until vendor-specific trading sessions are modeled.
- Invalid data is not silently repaired and is rejected by processed-data persistence by default.
- Raw data and generated artifacts are excluded from Git; directory placeholders remain tracked.
- A reference event-driven backtester will be authoritative; vectorized tools will be optional.

## Pending

- Lock dependencies for the selected execution environment.
- Add vendor-specific session calendars and holiday support.
- Add causal feature interfaces, registry, warm-up metadata, and feature tests.
- Add multi-timeframe alignment using only closed higher-timeframe bars.
- Add experiment manifests, event studies, and statistical reporting.
- Add reference execution, accounting, costs, and risk metrics.
- Add walk-forward, sensitivity, bootstrap, and cross-asset validation.
- Pilot the framework on a small, inspected XAUUSD sample.

## Known Issues and Limitations

- Generic weekday calendars do not know XAUUSD daily maintenance breaks or broker holidays.
- OHLC bars cannot resolve the order of intrabar stop-loss and take-profit touches.
- Tick volume is not centralized traded volume and must not be interpreted as such.
- Bid/ask absence limits the fidelity of spread and execution-cost simulations.
- `vectorbt` is intentionally not a core dependency until compatibility and semantics are assessed.

## Experiment Results

No market hypotheses or strategies have been tested. This is intentional for the current milestone.

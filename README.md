# AIQuantLab

AIQuantLab is a correctness-first framework for researching systematic market behavior. Its
purpose is to turn hypotheses into reproducible experiments, test them out of sample, and reject
fragile results before any strategy is considered for MT5 implementation.

The project does not claim that any indicator, timeframe, or strategy is profitable. Backtest
return is evidence to investigate, not proof.

## Current Scope

The current milestone implements the data foundation:

- Strict OHLCV and provenance contracts
- CSV column mapping and UTC timestamp normalization
- Duplicate, ordering, missing-value, OHLC, volume, alignment, and gap checks
- Configurable candle-grid policies
- Explicitly anchored timeframe conversion
- Parquet persistence with a JSON manifest and SHA-256 integrity check

Feature research, strategy simulation, optimization, and full-history data processing are not yet
implemented.

## Architecture

```text
raw data (immutable)
    -> ingestion and normalization
    -> validation and quality report
    -> canonical Parquet plus manifest
    -> causal features
    -> event studies and hypotheses
    -> reference backtester
    -> walk-forward and cross-asset validation
    -> reproducible reports
```

Reusable code lives in `src/aiquantlab`. Top-level `features`, `research`, `strategies`,
`backtest`, and `validation` directories are reserved for research specifications and artifacts;
notebooks must call package APIs rather than contain the only copy of core logic.

## Data Contract

Canonical bars contain exactly these required fields:

| Column | Meaning |
| --- | --- |
| `timestamp` | Timezone-aware UTC candle timestamp |
| `open` | Opening price |
| `high` | Highest price |
| `low` | Lowest price |
| `close` | Closing price |
| `volume` | Vendor-provided real, tick, or unknown volume |

Timestamps default to candle-open time. Raw files are never rewritten. Loading does not silently
sort or deduplicate rows, so those defects remain visible to validation.

The built-in `weekdays` calendar suppresses Saturday and Sunday expectations, but it cannot infer
a broker's XAUUSD maintenance break, holidays, or unusual sessions. Missing-candle findings are
therefore warnings until the vendor calendar is defined and verified. Dataset metadata must record
the vendor, timezone, price basis, volume type, and timestamp convention.

## Installation

Python 3.11 or newer is required. Create an isolated environment, then install the package and test
dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Research dependencies can be installed later with `python -m pip install -e ".[research,dev]"`.
Dependency versions should be locked before reproducible experiments begin.

## Basic Usage

Create a source configuration from `config/data.example.yaml`, keeping the raw CSV under
`data/raw`. Then use the composable ingestion API:

```python
from aiquantlab.data import ingest_csv, load_data_source_config

config = load_data_source_config("config/data.example.yaml")
result = ingest_csv("data/raw/xauusd-15m.csv", config)

print(result.quality_report.model_dump_json(indent=2))
```

Persist only a validated result:

```python
from aiquantlab.data import write_processed_dataset

write_processed_dataset(
    result.frame,
    "data/processed/xauusd-15m.parquet",
    metadata=result.metadata,
    quality_report=result.quality_report,
)
```

Run the test suite with `python -m pytest`.

## Research Guardrails

- Higher-timeframe features may use only fully closed bars.
- Train, validation, and final-test periods must remain separate.
- The final test must not influence feature, rule, or parameter selection.
- Costs, slippage, ambiguous intrabar execution, and sample dependence must be explicit.
- Failed and inconclusive hypotheses must be retained in the experiment registry.
- Cross-asset results supplement economic reasoning; they do not replace it.

See `STATUS.md` for progress, decisions, known limitations, and the next milestone.


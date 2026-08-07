# AIQuantLab

AIQuantLab 是一个以 correctness-first（优先保证正确性）为原则的系统化市场行为研究框架。它的目标是将研究假设转化为可复现的实验，在 out-of-sample（样本外）数据上进行检验，并在任何策略进入 MT5 实现阶段之前，识别并排除脆弱的研究结果。

本项目不声称任何指标、时间周期或策略一定具有盈利能力。Backtest return（回测收益）只是需要进一步调查的证据，不是有效性的证明。

## Current Scope（当前范围）

当前里程碑已经实现数据基础设施和 research experiment framework（研究实验框架）：

- 严格的 OHLCV 和 Data provenance（数据来源与处理溯源）契约
- CSV 列映射和 UTC 时间戳标准化
- 重复、排序、缺失值、OHLC、成交量、对齐和数据缺口检查
- 可配置的 K 线时间网格策略
- 明确锚定方式的 timeframe conversion（时间周期转换）
- 使用 JSON manifest 和 SHA-256 integrity check（完整性校验）的 Parquet 持久化
- 可证伪的 hypothesis definition（假设定义）和只允许当前或历史 lag 的结构化事件条件
- 持久化 experiment registry，记录实验 revision、运行状态和人工研究结论
- Event study（事件研究），测量 forward return、最大上行/下行幅度和首次正/负收益所需 bar 数
- 使用 deterministic bootstrap、confidence interval 和 Benjamini-Hochberg 多重检验调整的统计报告
- 固定 dataset checksum、配置 fingerprint、随机种子和代码版本的不可变实验产物

Feature engineering（特征工程）、trading strategy（交易策略）、Backtesting（回测）、optimization（优化）和全历史数据处理目前尚未实现。

## Architecture（架构）

```text
raw data (immutable，原始数据不可变)
    -> ingestion and normalization（摄取与标准化）
    -> validation and quality report（校验与质量报告）
    -> canonical Parquet plus manifest（规范 Parquet 数据与 manifest）
    -> causal features（因果特征）
    -> event studies and hypotheses（事件研究与研究假设）
    -> reference backtester（参考回测器）
    -> walk-forward and cross-asset validation（Walk-forward validation 与跨资产验证）
    -> reproducible reports（可复现报告）
```

可复用代码位于 `src/aiquantlab`。顶层的 `features`、`research`、`strategies`、`backtest` 和 `validation` 目录用于保存研究规范和产物；notebook 必须调用 package API，不能成为核心逻辑的唯一实现位置。

## Data Contract（数据契约）

规范 K 线包含以下必需字段：

| Column | 含义 |
| --- | --- |
| `timestamp` | 带时区的 UTC K 线时间戳 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `close` | 收盘价 |
| `volume` | 数据供应商提供的 real、tick 或 unknown 成交量 |

时间戳默认表示 K 线开盘时刻。原始文件不会被重写。加载过程不会静默地排序或去重，因此这些问题会保留到 validation（校验）阶段并明确报告。

内置的 `weekdays` calendar（交易日历）会忽略周六和周日的预期 K 线，但无法推断某个经纪商的 XAUUSD 维护时段、节假日或其他特殊交易时段。因此，在供应商交易日历被定义并验证之前，missing-candle（缺失 K 线）结果只作为 warning（警告）。Dataset metadata（数据集元数据）必须记录供应商、时区、price basis（价格基准）、volume type（成交量类型）和 timestamp convention（时间戳含义）。

## Installation（安装）

需要 Python 3.11 或更高版本。请创建隔离环境，然后安装 package 和测试依赖：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Research dependencies（研究依赖）可以稍后通过 `python -m pip install -e ".[research,dev]"` 安装。在开始可复现实验之前，应锁定依赖版本。

## Basic Usage（基本用法）

从 `config/data.example.yaml` 创建数据源配置，并将原始 CSV 放在 `data/raw` 下。然后使用可组合的 ingestion API：

```python
from aiquantlab.data import ingest_csv, load_data_source_config

config = load_data_source_config("config/data.example.yaml")
result = ingest_csv("data/raw/xauusd-15m.csv", config)

print(result.quality_report.model_dump_json(indent=2))
```

只持久化通过校验的数据：

```python
from aiquantlab.data import write_processed_dataset

write_processed_dataset(
    result.frame,
    "data/processed/xauusd-15m.parquet",
    metadata=result.metadata,
    quality_report=result.quality_report,
)
```

运行测试套件：`python -m pytest`。

## Research Experiments（研究实验）

`config/experiments/event_study.example.yaml` 展示了完整的可复现实验配置。运行前必须将示例 `sha256` 替换为目标 Parquet 文件的实际 SHA-256。完整实验始终从配置引用的数据文件加载，不接受未登记的内存 DataFrame。

```python
from aiquantlab.research import (
    ExperimentRegistry,
    load_experiment_config,
    run_experiment,
)

config = load_experiment_config("config/experiments/event_study.example.yaml")
registry = ExperimentRegistry("experiments/registry.json")

result = run_experiment(
    config,
    registry=registry,
    artifact_root="experiments/runs",
    code_version="replace-with-git-commit",
)

print(result.statistical_report.model_dump_json(indent=2))
```

每次运行会生成 resolved config、hypothesis、event observations、unconditional baseline、statistical report 和 run manifest。报告不会自动宣布假设成立；`supported`、`not_supported` 或 `inconclusive` 结论必须在审阅结果后写入 registry，并附研究说明。

Event horizon 的单位是 bar，不是自然时间。默认 unconditional baseline 包含 event observations；bootstrap confidence interval 目前将 baseline mean 视为固定值。上述限制会写入统计报告 warning，不能在解释结果时忽略。

固定小样本的首个端到端验证记录见 [Phase 3 XAUUSD pilot](reports/phase3_xauusd_pilot.md)。该报告仅验证研究 workflow，不包含策略、信号或参数优化。

## Research Guardrails（研究护栏）

- Higher-timeframe features（高时间周期特征）只能使用已经完全收盘的 K 线。
- Train、validation 和 final-test 时间段必须保持分离。
- Final test（最终测试集）不得影响特征、规则或参数选择。
- Costs、slippage、ambiguous intrabar execution（盘中执行顺序不确定性）和 sample dependence（样本依赖性）必须显式建模或说明。
- Failed and inconclusive hypotheses（失败或结论不确定的假设）必须保留在 experiment registry（实验登记表）中。
- Cross-asset validation（跨资产验证）用于补充经济解释，不能取代经济解释本身。
- Statistical significance（统计显著性）不能单独证明经济显著性、可交易性或策略有效性。
- Event study 只测量市场行为，不得加入仓位、止损、止盈或订单执行规则。

进度、决策、已知限制和下一里程碑请参见 `STATUS.md`。

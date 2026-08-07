# AIQuantLab

AIQuantLab 是一个以 correctness-first（优先保证正确性）为原则的系统化市场行为研究框架。它的目标是将研究假设转化为可复现的实验，在 out-of-sample（样本外）数据上进行检验，并在任何策略进入 MT5 实现阶段之前，识别并排除脆弱的研究结果。

本项目不声称任何指标、时间周期或策略一定具有盈利能力。Backtest return（回测收益）只是需要进一步调查的证据，不是有效性的证明。

## Long-term Vision（长期愿景）

AIQuantLab 不只是一个 Backtesting framework，也不是让 AI 直接预测价格或生成 buy/sell signal 的系统。长期目标是建立一个 AI-assisted quantitative research laboratory（AI 辅助量化研究实验室），让 AI 协助整理研究问题、执行受约束的实验、比较证据和积累知识，但不能绕过数据质量、统计检验和人工研究判断。

系统长期应持续完成以下工作：

1. 收集和处理高质量 Market Data。
2. 发现并分析可解释的市场行为模式。
3. 永久保存 research experiments、失败结果和研究结论。
4. 从经过验证的 Research Findings 生成 strategy hypotheses。
5. 使用严格的 Backtesting 和 validation 评估策略候选。
6. 仅在策略通过验证后，考虑部署到 MT5 EA 等自动化执行系统。

核心原则：

```text
Research first.
Evidence first.
Validation before deployment.
```

## Current Scope（当前范围）

当前里程碑已经实现从 Tick 数据到研究结论、策略探针和时间样本外验证报告的首个完整纵向切片：

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
- 严格校验排序、UTC 与 bid/ask 关系的 Tick Parquet 到 M15 聚合，并保留执行价格列
- 两个最小 causal price-structure features、feature bundle fingerprint 和物化 manifest
- 人工审阅门槛、不可变 Research Finding 与跨 finding JSON index
- 完整策略候选契约、next-bar-open bid/ask 参考执行模型和交易成本指标
- 固定 research / validation / final-test 时段的时间顺序验证与压力滑点报告
- 只读 Web 研究界面：数据集、质量报告、实验证据、研究发现与策略候选的浏览器视图

当前实现是验证架构边界的最小纵向切片，不是通用策略平台。Multi-timeframe alignment、参数敏感性、滚动 walk-forward、bootstrap robustness、cross-asset validation、完整 Tick ingestion/tick replay、optimization 和 paper trading 仍未实现。

## Architecture（架构）

```text
Market Data
    -> Data Validation and Normalization
    -> Research Experiments
    -> Research Findings Knowledge Base
    -> Strategy Hypothesis Generation
    -> Strategy Development
    -> Backtesting
    -> Walk-forward Validation
    -> Paper Trading / Simulation Account
    -> Live Trading System (MT5 EA)
```

各阶段责任不同：

| Stage | 责任 |
| --- | --- |
| Market Data | 保存可追溯、不可变的原始市场数据 |
| Data Validation and Normalization | 统一 schema、时区和时间周期，暴露数据缺陷 |
| Research Experiments | 用可证伪 hypothesis 和 Event Study 测量市场行为 |
| Research Findings Knowledge Base | 保存配置、数据身份、结果、限制和人工结论 |
| Strategy Hypothesis Generation | 从已验证 finding 提出多个可比较的策略方向 |
| Strategy Development | 将候选方向转换为完整、明确、可执行的规则 |
| Backtesting | 在成本和执行假设明确的条件下模拟策略行为 |
| Walk-forward Validation | 检查 out-of-sample 稳定性和参数敏感性 |
| Paper Trading | 在 simulation account 中验证实时数据和执行流程 |
| Live Trading System | 由 MT5 EA 等执行层运行最终通过验证的策略 |

AIQuantLab 本身是 research and validation platform。MT5 EA 是最终 execution layer，不承担发现研究规律或选择策略的职责。

可复用代码位于 `src/aiquantlab`。顶层的 `features`、`research`、`strategies`、`backtest` 和 `validation` 目录用于保存研究规范和产物；notebook 必须调用 package API，不能成为核心逻辑的唯一实现位置。

## Research Findings 与 Strategies

Research Finding 回答的是：

> 哪一种市场行为具有统计证据？

Strategy 回答的是：

> 系统在什么条件下进入、退出并管理风险？

例如，研究层可能得到以下 finding：

> XAUUSD 在特定 trend、volatility 和 price structure 条件之后表现出正的 conditional expectancy。

这仍然不是交易策略。一个 finding 可以产生多个策略候选：

- Strategy A：条件保守、交易较少、目标是较低 drawdown。
- Strategy B：条件更积极、频率更高，同时承担更高风险。
- Strategy C：使用不同的 entry timing 和 exit timing。

Research layer 必须独立于 Strategy layer。研究实验不得包含 position sizing、stop loss、take profit 或订单执行规则；策略层也不得把单次显著结果直接当成有效规则。

## Research Findings Knowledge Base

AIQuantLab 应将每项研究结果保存为可复用、可审计的长期资产，而不是只保留一张图或一次终端输出。目标是积累市场知识，避免重复执行相同实验，也避免只保留成功结果。

目标结构示例：

```text
experiments/
└── EXP001/
    ├── hypothesis.md
    ├── config.yaml
    ├── dataset_info.json
    ├── result.json
    ├── analysis_report.md
    └── conclusion.md
```

每项实验至少应记录：

- Research question
- Hypothesis
- Dataset information 与 Data Provenance
- Market、timeframe 和 data range
- Parameters 与 methodology
- Statistical results
- Limitations
- Human conclusion

当前 experiment registry、resolved config、dataset checksum、statistical report 和 immutable run artifacts 是该 Knowledge Base 的基础。跨实验索引、检索、finding 归并和长期知识查询仍属于后续建设范围。

## Tick-first Data Architecture

长期数据架构以 Tick Data 作为最高保真的 Raw Data 和 single source of truth。用户不应手工维护每一种 timeframe 数据集。

```text
Raw Tick Data (immutable)
    -> Bar Aggregation Engine
    -> M1 / M5 / M15 / H1 / H4 / D1
    -> Research Pipeline
```

由 Tick Data 生成的 timeframe 数据属于 processed artifacts，可以按明确的 aggregation config 重建；Raw Tick Data 必须保持不可变，并记录 provider、timezone、bid/ask schema、授权信息和 checksum。

Tick Data 的主要价值：

- 生成统一或自定义 timeframe，减少供应商 bar 边界差异。
- 为高保真 Backtesting 和 realistic execution simulation 提供基础。
- 支持未来的 tick replay。
- 更好地分析 intrabar price movement。
- 在 bar 数据无法确定事件顺序时提供更细粒度证据。

例如，同一根 OHLC K 线可能同时覆盖 stop loss 和 take profit，但无法判断哪一个先触发。Tick replay 可以提供更可靠的事件顺序；它仍不能消除 latency、liquidity 和真实成交回报等执行不确定性。

当前 package 已实现 bar-level ingestion、validation 和 timeframe conversion，但完整的 Tick Data ingestion、Bar Aggregation Engine 和 tick replay 尚未实现。因此 Tick-first 是长期架构原则，不是对当前功能完整度的声明。

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

## Web Research Interface（Web 研究界面）

Web 层是 artifact 的只读研究界面，不是交易终端，也不生成或执行任何订单。它直接读取 `data/processed`、`experiments` 和 `reports` 下的既有 artifact，不引入数据库，也不复制研究数据。架构边界见 [docs/WEB_ARCHITECTURE.md](docs/WEB_ARCHITECTURE.md)。

启动后端（默认监听 `http://127.0.0.1:8000`，OpenAPI 文档在 `/docs`）：

```powershell
python -m pip install -e ".[web,dev]"
python -m uvicorn aiquantlab_web.app:app --reload --app-dir web/backend
```

后端通过向上查找 `pyproject.toml` 定位仓库根目录；如需指向其他仓库，设置 `AIQUANTLAB_ROOT` 环境变量。

启动前端（默认监听 `http://localhost:5173`，开发期由 Vite 代理 `/api` 到后端）：

```powershell
cd web/frontend
npm install
npm run dev
```

界面按研究流程分页：研究总览、数据集浏览与质量报告、实验浏览与统计证据、研究发现、策略候选与验证报告、研究报告查看器。被拒绝的实验、发现和候选一律保留可见，界面不会把它们呈现为可交易结论。

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

## First Complete XAUUSD Pipeline

固定配置 `config/pipelines/xauusd_m15_first.yaml` 使用 2015–2017 HistData bid/ask Tick 数据运行首个完整纵向切片：2015 research、2016 validation、2017 final test。运行方式：

```powershell
python scripts/run_xauusd_research_pipeline.py
```

脚本会校验并聚合 Tick、物化因果特征、运行 Event Study、应用人工 review、发布 finding、冻结策略定义，并生成含 primary/stress 成本场景的 validation report。生成数据与不可变 artifacts 默认留在 Git 之外；固定配置、人工 review 和结果摘要进入版本控制。

本次预声明的 strong-bullish continuation 假设没有通过 research gate。系统保留 rejected finding，并将预声明 long rule 仅作为 `pipeline_probe` 执行，以验证回测与报告链路；它不能被解释为通过验证的策略。结果见 [first complete XAUUSD pipeline report](reports/xauusd_m15_first_pipeline.md)。

## Strategy Research Layer

Strategy Research Layer 只接收经过审阅的 Research Findings，其职责是：

- 将 finding 转换为明确、可验证的交易规则。
- 从同一个 finding 生成多个 strategy candidates，而不是只保留历史表现最好的版本。
- 比较不同候选的风险、收益、交易频率、持有时间和执行要求。
- 保持策略定义与研究证据之间的可追溯关系。

完整 strategy definition 最终应包含：

- Market
- Timeframe
- Entry conditions
- Exit conditions
- Stop loss
- Take profit
- Position sizing
- Risk management rules

每个策略候选必须独立评估。Research Finding 本身不能直接下单。当前仅实现一条受限纵向切片：接受的 finding 可以生成 qualification candidate；rejected finding 只能生成明确标记、永远不能获得 qualifying assessment 的 pipeline probe。通用候选生成、比较和选择仍未实现。

## Validation Philosophy（验证哲学）

历史 Backtesting 表现良好不是策略被接受的充分条件。完整验证流程应包括：

- Historical Backtesting
- Walk-forward Validation
- Sensitivity Analysis
- Bootstrap Analysis
- Cross-market / Cross-asset Validation
- Paper Trading

当前已实现固定的 research / validation / final-test chronological split、observed bid/ask spread、显式 slippage stress 和基础收益/回撤指标。它不等同于完整 rolling walk-forward、参数敏感性或跨资产验证。

系统需要主动检测和限制：

- Future data leakage
- Overfitting
- Curve fitting
- 在同一数据上 optimization 与 evaluation
- 只选择有利时期、资产或参数
- Unrealistic execution assumptions

Final unseen test 在规则和参数冻结前不得访问。即使统计结果显著，也必须检查 effect size、样本量、成本敏感性、regime dependence 和经济解释。

## Future Execution and MT5 EA Integration

最终部署路径：

```text
Validated Research Finding
    -> Strategy Definition
    -> Backtesting
    -> Walk-forward Validation
    -> Paper Trading
    -> MT5 EA Implementation
    -> Live Deployment
```

AIQuantLab 不是 EA。AIQuantLab 负责生成、保存和验证研究证据与策略候选；MT5 EA 只负责实现最终批准的 execution contract。任何策略未完成 validation 和 Paper Trading 前，不应进入 live deployment。

## Roadmap

| Phase | 目标 |
| --- | --- |
| Phase 0 | Architecture and Data Foundation |
| Phase 1 | Data Validation and Processing |
| Phase 2 | Research Experiment Framework |
| Phase 3 | Research Knowledge Base |
| Phase 4 | Strategy Research Framework |
| Phase 5 | Backtesting and Validation |
| Phase 6 | Paper Trading |
| Phase 7 | MT5 EA Integration |

Phase 编号表示长期能力建设顺序，不表示某个实验已经获得交易资格。当前实现状态和剩余工作以 `STATUS.md` 为准。

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

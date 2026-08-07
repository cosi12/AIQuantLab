# AIQuantLab

AIQuantLab 是一个 **AI-assisted quantitative research laboratory**（AI 辅助量化研究实验室），采用 correctness-first（正确性优先）的工程原则，把研究假设转化为可复现的实验，并在任何策略进入执行系统之前识别并排除脆弱的研究结果。

本项目不声称任何指标、时间周期或策略具有盈利能力。Backtest return（回测收益）只是需要进一步调查的证据，不是有效性的证明。

## 目录

1. [项目概览](#1-项目概览)
2. [为什么需要 AIQuantLab](#2-为什么需要-aiquantlab)
3. [核心哲学](#3-核心哲学)
4. [架构总览](#4-架构总览)
5. [研究工作流](#5-研究工作流)
6. [当前已实现能力](#6-当前已实现能力)
7. [Research Findings 概念](#7-research-findings-概念)
8. [数据架构](#8-数据架构)
9. [验证原则](#9-验证原则)
10. [Roadmap](#10-roadmap)
11. [当前限制](#11-当前限制)
12. [开发原则](#12-开发原则)

---

## 1. 项目概览

AIQuantLab 是一个 research and validation platform（研究与验证平台），用于系统化地研究市场行为、保存研究证据，并为后续策略开发提供可审计的知识基础。

### 1.1 它是什么

| 定位 | 说明 |
| --- | --- |
| Research laboratory | 提出可证伪假设，用受约束的实验测量市场行为 |
| Evidence archive | 永久保存实验配置、数据身份、统计结果、限制和人工结论 |
| Validation platform | 在结论进入执行系统之前施加严格的验证与护栏 |

### 1.2 它不是什么

AIQuantLab **不是**：

- Trading signal generator（交易信号生成器）
- AI price prediction system（AI 价格预测系统）
- 自动盈利系统
- Strategy optimizer（以历史收益为目标的参数优化器）
- MT5 EA 或任何形式的执行程序

### 1.3 "AI-assisted" 的确切含义

AI 在本项目中的角色是**协助研究流程**，而不是替代研究判断：

- AI 可以协助整理研究问题、编写实验配置、执行受约束的实验、比较证据、归纳文档。
- AI **不能** 绕过 data quality check、统计检验或人工研究结论。
- 框架不会因为统计显著就自动认定假设成立。

需要明确：当前 package 中**没有实现任何自动化 AI agent 组件**。"AI-assisted" 描述的是研究协作方式与长期设计意图，人类研究者与 AI 助手使用同一套可复现契约。

---

## 2. 为什么需要 AIQuantLab

量化研究中最常见的失败不是"没有找到规律"，而是"找到了不存在的规律"：

| 常见失败模式 | AIQuantLab 的应对 |
| --- | --- |
| 数据缺陷被静默修复，污染结论 | 不静默排序、去重或填充；缺陷进入 quality report 并显式暴露 |
| 特征引用了未来数据 | Event condition 只允许当前值和非负历史 lag |
| 实验无法复现 | 固定 dataset checksum、config fingerprint、random seed、code version |
| 只保留成功结果 | 失败与 inconclusive 结论必须保留在 registry 中 |
| 在同一数据上优化并评估 | 训练/验证/最终测试时段分离，final test 冻结前不可访问 |
| 把统计显著等同于可交易性 | 统计层与策略层分离；显著性不构成经济结论 |
| 研究结果只存在于一次终端输出中 | 每次运行生成不可变 artifact 目录 |

这些问题无法靠"更聪明的模型"解决，只能靠**流程约束**解决。AIQuantLab 的价值在于把这些约束写进代码契约，而不是写进注意事项清单。

---

## 3. 核心哲学

```text
Research first.
Evidence first.
Validation before deployment.
```

具体展开为三条工作准则：

**Research first（研究优先）**  
先理解市场行为，再考虑如何交易。策略是研究结论的下游产物，不是起点。

**Evidence first（证据优先）**  
每个结论必须绑定可核对的数据身份、统计结果和已知限制。没有证据链的结论不构成 finding。

**Validation before deployment（先验证后部署）**  
历史表现良好不是接受策略的充分条件。任何规则在完成完整验证与 paper trading 之前，不进入 live deployment。

### 3.1 研究层与策略层必须分离

| 层 | 回答的问题 | 允许包含 | 禁止包含 |
| --- | --- | --- | --- |
| Research Finding | 哪一种市场行为具有统计证据？ | 事件定义、forward return、统计报告、限制 | position sizing、stop loss、take profit、订单执行 |
| Strategy | 系统在什么条件下进入、退出并管理风险？ | 完整可执行规则 | 把单次显著结果直接当作有效规则 |

例如研究层可能得到这样的 finding：

> XAUUSD 在特定 trend、volatility 和 price structure 条件之后表现出正的 conditional expectancy。

**这仍然不是交易策略。** 同一个 finding 可以派生出多个独立的策略候选：

- Strategy A：条件保守、交易较少、目标较低 drawdown
- Strategy B：条件更积极、频率更高、承担更高风险
- Strategy C：使用不同的 entry timing 与 exit timing

每个候选必须独立评估。这就是为什么 finding 与 strategy 必须分层保存。

---

## 4. 架构总览

### 4.1 长期流水线

```text
Market Data
    ↓
Data Validation and Normalization
    ↓
Research Experiments
    ↓
Research Findings Knowledge Base
    ↓
Strategy Hypothesis Generation        (future)
    ↓
Strategy Development                  (future)
    ↓
Backtesting and Validation            (future)
    ↓
Paper Trading / Simulation Account    (future)
    ↓
Execution Systems such as MT5 EA      (future)
```

标注 `(future)` 的阶段仍属于长期完整能力。当前已有一条受限的 strategy/backtest/chronological-validation 纵向切片，用于验证端到端契约；它不表示通用阶段能力已经完成。

### 4.2 各阶段责任

| Stage | 责任 | 状态 |
| --- | --- | --- |
| Market Data | 保存可追溯、不可变的原始市场数据 | 基础实现 |
| Data Validation and Normalization | 统一 schema、时区和时间周期，暴露数据缺陷 | 基础实现 |
| Research Experiments | 用可证伪 hypothesis 和 Event Study 测量市场行为 | 基础实现 |
| Research Findings Knowledge Base | 把已审阅的实验证据归并为可检索的长期 finding | 最小 promotion gate、immutable finding 与 JSON index 已实现；完整检索/归并待建设 |
| Strategy Hypothesis Generation | 从已验证 finding 提出多个可比较的策略方向 | 仅有固定单候选纵向切片；通用生成/比较未实现 |
| Strategy Development | 将候选方向转换为完整、明确、可执行的规则 | 最小 immutable candidate contract 已实现 |
| Backtesting and Validation | 在成本与执行假设明确的条件下模拟策略行为，并检查 out-of-sample 稳定性与参数敏感性 | next-open bid/ask 参考引擎与固定 chronological splits 已实现；完整 walk-forward/敏感性未实现 |
| Paper Trading / Simulation Account | 在 simulation account 中验证实时数据和执行流程 | 未开始 |
| Execution Systems such as MT5 EA | 实现最终批准的 execution contract | 未开始 |

### 4.3 平台边界

**AIQuantLab 本身是 research and validation platform。**

MT5 EA 是**未来的** execution layer，它不承担发现研究规律或选择策略的职责。AIQuantLab 负责生成、保存和验证研究证据与策略候选；执行层只负责实现最终批准的 execution contract。

### 4.4 代码组织

可复用逻辑位于 `src/aiquantlab`：

```text
src/aiquantlab/
├── data/         # ingestion、validation、tick aggregation、resampling、storage
├── features/     # causal feature contracts、registry、materialization
├── research/     # hypothesis、event condition、event study、statistics、registry、runner
├── findings/     # human-reviewed promotion gate 与 immutable index
├── strategies/   # immutable candidate contracts
├── backtest/     # next-bar-open bid/ask reference engine
└── validation/   # frozen chronological split plans and reports
```

顶层的 `features/`、`research/`、`strategies/`、`backtest/`、`validation/` 目录用于保存研究规范与产物；可执行逻辑只位于 package。Notebook 必须调用 package API，不能成为核心逻辑的唯一实现位置。

---

## 5. 研究工作流

当前框架支持的完整研究闭环：

```text
1. 配置数据源          config/data.example.yaml
2. Ingest + Validate   ingest_csv -> QualityReport
3. 持久化              write_processed_dataset -> Parquet + manifest + SHA-256
4. 定义假设            可证伪的 HypothesisDefinition
5. 定义实验            ExperimentConfig（数据 checksum、event、horizon、统计参数）
6. 执行实验            run_experiment -> 不可变 artifact 目录
7. 人工审阅            阅读 statistical report
8. 写入结论            registry.set_conclusion(supported / not_supported / inconclusive / invalid)
```

关键约束：

- 步骤 6 会强制校验数据文件 SHA-256 与配置声明一致，不匹配则直接失败。
- 步骤 7 **不能自动化**。框架不会宣布假设成立。
- 步骤 8 必须附研究说明；无说明的结论会被拒绝。

---

## 6. 当前已实现能力

本节**只描述今天已经存在的功能**。

### 6.1 数据基础设施

- 严格的 OHLCV 与 data provenance（数据来源与处理溯源）契约
- CSV 列映射与 UTC 时间戳标准化
- 重复、排序、缺失值、OHLC 关系、成交量、对齐与数据缺口检查
- 可配置的 K 线时间网格策略（continuous / weekdays / disabled）
- 明确锚定方式的 timeframe conversion，并移除不完整的边界 K 线
- 使用 JSON manifest 与 SHA-256 integrity check 的 Parquet 持久化

### 6.2 研究实验框架

- 可证伪的 hypothesis definition（statement、rationale、null / alternative、falsification criteria）
- 结构化 event condition，只允许当前值或非负历史 lag
- Event study：forward return、最大上行/下行幅度、首次正/负收益所需 bar 数
- Unconditional baseline 与 deterministic IID / moving-block bootstrap
- Confidence interval、standardized effect、bootstrap p-value、Benjamini-Hochberg q-value
- 持久化 experiment registry：config fingerprint、dataset checksum、运行状态、人工结论
- 不可变实验产物：resolved config、hypothesis、observations、baseline、statistical report、run manifest

### 6.3 首个完整纵向切片

- HistData bid/ask Tick Parquet 严格校验与 M15 midpoint/execution-bar 聚合
- Causal price-structure feature bundle 与 feature-conditioned experiment integrity chain
- Human-reviewed finding promotion gate 和 immutable finding index
- Immutable strategy candidate、next-bar-open bid/ask execution、固定持有期
- 2015 research / 2016 validation / 2017 final-test chronological report

首个 finding 被正确标记为 `rejected`；对应 long rule 仅以 `pipeline_probe` 验证链路，最终 assessment 为 `not_supported`。这证明流程会保留失败证据，不证明策略能力。

### 6.4 尚未实现

以下能力**当前不存在**，不要根据本 README 假设它们可用：

Multi-timeframe alignment、通用 strategy generation、滚动 walk-forward、参数敏感性、bootstrap robustness、cross-asset validation、optimization、完整 tick ingestion、通用多周期 bar aggregation、tick replay 和 paper trading。

### 6.5 安装

需要 Python 3.11 或更高版本：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Research 依赖（matplotlib、scipy、statsmodels 等）可稍后安装：

```powershell
python -m pip install -e ".[research,dev]"
```

在开始可复现实验之前，应为目标执行环境锁定依赖版本。

### 6.5 数据 ingestion

从 `config/data.example.yaml` 创建数据源配置，并将原始 CSV 放在 `data/raw` 下：

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

默认情况下，含有 error-level 质量问题的数据会被拒绝写入。

### 6.6 运行实验

`config/experiments/event_study.example.yaml` 展示了完整的可复现实验配置。运行前必须将示例 `sha256` 替换为目标 Parquet 文件的实际 SHA-256。完整实验始终从配置引用的数据文件加载，**不接受未登记的内存 DataFrame**。

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

报告不会自动宣布假设成立。`supported`、`not_supported` 或 `inconclusive` 结论必须在审阅结果后写入 registry，并附研究说明。

Event horizon 的单位是 **bar，不是自然时间**。

### 6.7 测试

```powershell
python -m pytest
```

当前测试结果与覆盖率见 `STATUS.md`。

### 6.8 首个端到端验证

固定小样本的首个端到端验证记录见 [Phase 3 XAUUSD pilot](reports/phase3_xauusd_pilot.md)。

该 pilot **只验证研究 workflow**，两项描述性 event study 的结论均为 `inconclusive`。它不包含策略、信号或参数优化，也不构成稳健市场证据。完整数据、统计结果与限制见报告本身。

---

## 7. Research Findings 概念

研究知识分为两层，本文档始终区分使用，不混称为"知识库"：

| 层 | 名称 | 内容 | 状态 |
| --- | --- | --- | --- |
| 实验层 | **Experiment Registry and Artifacts** | 单次实验的身份、配置 fingerprint、数据 checksum、运行状态、不可变产物与人工结论 | 已实现 |
| 知识层 | **Research Findings Knowledge Base** | 经人工提升的跨实验长期结论，绑定证据链接与限制 | 未实现，设计见 Phase 4a |

实验层回答"这次实验做了什么、得到什么"；知识层回答"我们据此知道了什么、还不知道什么"。

一条 finding 可以引用多次实验运行；**一次实验运行不会自动成为 finding**。提升必须经过人工审阅，不得仅凭 p/q-value 阈值触发。

### 7.1 实验不应在执行后消失

一次实验的价值不在于那一次终端输出，而在于它成为可复用、可审计的长期资产。目标是积累市场知识，避免重复执行相同实验，也避免只保留成功结果。

每条 finding 记录至少应保存：

- Research question
- Hypothesis
- Dataset information 与 data provenance
- Market、timeframe 与 data range
- Parameters 与 methodology
- Statistical results
- **Limitations**
- **Human conclusion**

### 7.2 负面结果同样是知识

| 结论 | 是否保留 | 价值 |
| --- | --- | --- |
| `supported` | 是 | 候选研究方向，仍需 replication |
| `not_supported` | 是 | 排除了一条假设，避免重复投入 |
| `inconclusive` | 是 | 记录样本量、效应量或数据质量的边界 |
| `invalid` | 是 | 记录方法学缺陷，防止重蹈覆辙 |

**Inconclusive research is still knowledge.** 失败与结论不确定的假设必须保留在 registry 中，不允许删除或改写。

### 7.3 可复现性

一个研究结果如果不能复现，它就不是证据。当前框架通过以下机制保证可复现：

| 机制 | 作用 |
| --- | --- |
| Dataset checksum (SHA-256) | 固定数据身份；文件变化导致实验直接失败，而不是静默产出不同结果 |
| Configuration fingerprint | 配置的规范化 SHA-256；同一 experiment_id + revision 下配置变化会被拒绝 |
| Code version | 记录执行时的代码版本，绑定结果与实现 |
| Random seed | 固定 bootstrap 抽样，保证统计结果确定性 |
| Frame fingerprint | 记录实际参与计算的研究帧身份 |
| Immutable artifacts | 每次 run 写入独立目录：resolved config、hypothesis、observations、baseline、statistical report、run manifest |
| Provenance metadata | 记录 provider、timezone、price basis、volume type、timestamp convention |

### 7.4 两层的落盘结构

```text
experiments/
├── registry.json          # 实验层，已实现：实验登记、运行状态、人工结论
├── runs/                  # 实验层，已实现：不可变 run artifacts
│   └── <EXP_ID>/revision-<n>/<run_id>/
│       ├── config.resolved.json
│       ├── hypothesis.json
│       ├── observations.parquet
│       ├── baseline.parquet
│       ├── statistical_report.json
│       └── run_manifest.json
└── findings/              # 知识层，未实现：finding 记录与跨实验索引
```

实验层是知识层的**前提**而不是知识层本身：跨实验索引、检索、finding 归并和长期结论管理尚未实现，设计见 [Phase 4 设计文档](docs/phase4_design.md)。

---

## 8. 数据架构

### 8.1 Data Contract（数据契约）

规范 K 线包含以下必需字段：

| Column | 含义 |
| --- | --- |
| `timestamp` | 带时区的 UTC K 线时间戳 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `close` | 收盘价 |
| `volume` | 数据供应商提供的 real、tick 或 unknown 成交量 |

时间戳默认表示 **bar-open time（K 线开盘时刻）**。原始文件不会被重写。加载过程不会静默地排序或去重，因此这些问题会保留到 validation 阶段并明确报告。

Dataset metadata 必须记录供应商、时区、price basis（价格基准）、volume type（成交量类型）与 timestamp convention（时间戳含义）。

### 8.2 交易日历限制

内置的 `weekdays` calendar 会忽略周六和周日的预期 K 线，但**无法推断**某个经纪商的 XAUUSD 维护时段、节假日或其他特殊交易时段。因此，在供应商交易日历被定义并验证之前，missing-candle 结果只作为 **warning**，不作为 error。

### 8.3 Tick-first Data Architecture（长期架构原则）

> **实现状态**：当前 package 已实现 bar-level ingestion、validation 与 timeframe conversion。**完整的 Tick Data ingestion、Bar Aggregation Engine 和 tick replay 尚未实现。** Tick-first 是长期架构原则，不是对当前功能完整度的声明。

长期数据架构以 Tick Data 作为最高保真度的 raw data 和 single source of truth。研究者不应手工维护每一种 timeframe 数据集。

```text
Raw Tick Data (immutable)
    ↓
Bar Aggregation Engine
    ↓
M1 / M5 / M15 / H1 / H4 / D1
    ↓
Research Pipeline
```

由 Tick Data 生成的 timeframe 数据属于 **processed artifacts**，可以按明确的 aggregation config 重建；Raw Tick Data 必须保持不可变，并记录 provider、timezone、bid/ask schema、授权信息与 checksum。

这样做可以消除供应商 bar 边界差异，并为高保真 backtesting、intrabar 分析和未来的 tick replay 提供基础。

其中最关键的一点：同一根 OHLC K 线可能同时覆盖 stop loss 与 take profit，但无法判断哪一个先触发。Tick replay 可以提供更可靠的事件顺序；它仍**不能**消除 latency、liquidity 和真实成交回报等执行不确定性。

---

## 9. 验证原则

### 9.1 历史表现不是接受条件

完整验证流程应包括：

- Historical Backtesting
- Walk-forward Validation
- Sensitivity Analysis
- Bootstrap Analysis
- Cross-market / Cross-asset Validation
- Paper Trading

上述验证阶段**当前均未实现**，属于 Phase 5 及以后的范围。

### 9.2 必须主动检测与限制的问题

- Future data leakage（未来数据泄漏）
- Overfitting（过拟合）
- Curve fitting（曲线拟合）
- 在同一数据上 optimization 与 evaluation
- 只选择有利时期、资产或参数
- Unrealistic execution assumptions（不现实的执行假设）

### 9.3 Research Guardrails（研究护栏）

以下护栏对所有阶段有效：

- Higher-timeframe features 只能使用已经完全收盘的 K 线。
- Train、validation 和 final-test 时间段必须保持分离。
- Final test 不得影响特征、规则或参数选择；规则与参数冻结前不得访问。
- Costs、slippage、ambiguous intrabar execution 和 sample dependence 必须显式建模或说明。
- Failed and inconclusive hypotheses 必须保留在 experiment registry 中。
- Cross-asset validation 用于补充经济解释，不能取代经济解释本身。
- Statistical significance 不能单独证明经济显著性、可交易性或策略有效性。
- Event study 只测量市场行为，不得加入仓位、止损、止盈或订单执行规则。

即使统计结果显著，仍必须检查 **effect size、样本量、成本敏感性、regime dependence 和经济解释**。

### 9.4 未来的执行路径

部署顺序即第 4.1 节流水线的下半段：validated finding → strategy definition → backtesting → walk-forward validation → paper trading → MT5 EA implementation → live deployment。

AIQuantLab 不是 EA。任何策略在完成 validation 与 paper trading 之前，不进入 live deployment。

---

## 10. Roadmap

| Phase | 能力 | 状态 |
| --- | --- | --- |
| Phase 0 | Architecture and Data Foundation | 已完成基础实现 |
| Phase 1 | Data Validation and Processing | 已完成基础实现，provider calendar 等仍待完善 |
| Phase 2 | Research Experiment Framework | 已完成基础实现 |
| Phase 3 | Research Knowledge Base — 实验层（registry 与不可变产物） | 已完成基础实现 |
| Phase 4a | Causal Feature and Research Findings Layer | 设计完成，未实现 |
| Phase 4b | Strategy Research Framework | 未开始，由 4a 产出的 finding 证据门控 |
| Phase 5 | Backtesting and Validation | 未开始 |
| Phase 6 | Paper Trading | 未开始 |
| Phase 7 | MT5 EA Integration | 未开始 |

Phase 编号表示**长期能力建设顺序**，不表示某个实验已经获得交易资格。

Phase 4 拆分为 4a 与 4b 是实现顺序的如实反映：4a 交付因果特征契约、多时间框架对齐与 Research Findings Knowledge Base，**不生成任何策略**；4b 才进入 Strategy Hypothesis Generation，且必须等 4a 积累到足够的 finding 证据后才启动。范围与非目标见 [Phase 4 设计文档](docs/phase4_design.md)。

当前实现状态、已知限制与下一里程碑以 [`STATUS.md`](STATUS.md) 为准。

---

## 11. 当前限制

以下限制是已知且公开记录的，解释研究结果时不得忽略。完整清单见 [`STATUS.md`](STATUS.md)。

### 11.1 数据限制

- Tick volume 不是集中式实际成交量，不得按实际成交量解释。
- 缺少 bid/ask 数据会限制 spread 与 execution-cost simulation 的精度。
- 交易日历与 intrabar 顺序的限制见第 8.2、8.3 节。

### 11.2 统计限制

- 默认 baseline 包含 event observations，统计报告必须披露这一点。
- Bootstrap confidence interval 当前不重采样 baseline uncertainty，baseline mean 被视为固定值。
- Moving-block bootstrap 只能**部分**缓解重叠 event window 与时间序列依赖。
- 多 horizon 样本可能因数据尾部没有完整 forward window 而具有不同样本量。

### 11.3 工程限制

- JSON experiment registry 采用 atomic replacement，但当前只支持 single-process workflow，没有跨进程文件锁。
- 依赖版本尚未为目标执行环境锁定。

### 11.4 研究范围限制

- 现有实验结果来自单一固定小样本，仅用于验证 workflow。
- 尚未使用独立时期或独立报价源复核数据语义。
- 尚无任何结论达到可以支撑策略开发的证据强度。

---

## 12. 开发原则

### 12.1 工程约定

- 可复用逻辑必须位于 `src/aiquantlab`；notebook 只能调用 package API。
- 数据契约与研究契约使用 pydantic 严格模型（`extra="forbid"`、`frozen=True`）。
- 不静默修复无效数据；默认情况下 processed-data persistence 会拒绝含有质量错误的数据。
- Raw data 与生成产物默认排除在 Git 之外；目录占位文件会被跟踪。
- 参考 event-driven backtester 将作为权威执行模型；vectorized tools 只作为可选工具。

### 12.2 研究约定

- 假设必须可证伪，且在运行前固定。
- 实验参数（样本窗口、event、horizon、bootstrap、seed）在运行前固定，不得事后调整以改善结果。
- 结论必须由人工写入，并附研究说明。
- 已发布的 run artifact 视为不可变；修正通过新 revision 表达，而不是覆盖历史。
- 阶段能力状态在**实现之后**才更新到 README 与 STATUS，不提前宣称完成。

### 12.3 文档职责

| 文档 | 职责 |
| --- | --- |
| `README.md` | 项目身份、哲学、架构、当前能力与长期 roadmap |
| [`STATUS.md`](STATUS.md) | 权威的实现进度、验证结果、决策记录与已知限制 |
| [`docs/phase4_design.md`](docs/phase4_design.md) | Phase 4 研究层设计（范围与非目标） |
| [`reports/`](reports/) | 具体研究报告与 pilot 记录 |

当 README 与 `STATUS.md` 出现分歧时，**以 `STATUS.md` 为准**。

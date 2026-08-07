# Phase 4 设计：Causal Feature & Research Findings Layer

日期：2026-08-07  
状态：核心因果特征与最小 finding promotion 已实现；MTF alignment 仍未实现
依据：`README.md`、`STATUS.md`、现有 `src/aiquantlab` 研究契约

> 2026-08-07 实现说明：`aiquantlab.features`、feature-conditioned experiment integrity chain 和最小 `FindingRegistry` 已按本设计落地。后续 milestone 另行加入了受限 strategy/backtest/chronological-validation 纵向切片；rejected finding 仅允许产生不可获得 qualifying assessment 的 `pipeline_probe`，不改变本设计中 Research Finding 与 Strategy 的责任边界。

## 1. 定位

Phase 4 建设的是 **Research Findings 成熟化层**：在已完成的 Event Study / Experiment Registry 之上，补齐因果特征、多时间框架对齐、finding 提升与跨实验知识索引，使研究层能够产出可比较、可检索、可审计的 Research Finding。

它回答的问题是：

> 在什么可解释、无未来泄漏的市场状态条件下，事件后的条件行为是否有可复现的统计证据？

它 **不** 回答：

> 系统应如何入场、出场、止损、止盈或管理仓位？

### 1.1 与 Roadmap 标签的关系

长期 Roadmap 将 Phase 4 标注为 `Strategy Research Framework`。该标签描述的是架构流水线中 **Research Findings → Strategy Hypothesis Generation** 的下一阶段能力。

当前权威状态与原则要求：

- Phase 3 Knowledge Base 仅有 registry / artifacts 基础，跨实验索引与 finding 归并未完成。
- Causal feature、warm-up metadata、已收盘高时间周期对齐尚未实现。
- `STATUS.md` 明确：在研究证据充分后才建设 Strategy Research Framework；当前不得提前生成策略。
- 项目原则：Research first. Evidence first. Validation before deployment.

因此，**Phase 4 的实现范围是 Strategy Research 的前置研究层**，不是策略框架本身。  
Strategy Hypothesis Generation 仍属于后续阶段；本阶段只定义向其交付的 Finding 契约与准入门槛。

### 1.2 在权威架构中的位置

```text
Market Data
    -> Data Validation and Normalization          # Phase 0–1（已有基础）
    -> Research Experiments                       # Phase 2（已有基础）
    -> Research Findings Knowledge Base           # Phase 3 基础 + Phase 4 完成
         |  + Causal Features / MTF Alignment     # Phase 4 新增研究能力
         v
    -> Strategy Hypothesis Generation             # 后续阶段（本设计不实现）
    -> Strategy Development
    -> Backtesting
    -> ...
```

## 2. 设计目标

1. **因果特征契约**：所有用于事件条件的特征必须可声明、可复现、无未来泄漏，并记录 warm-up。
2. **多时间框架因果对齐**：高时间周期特征只能引用已完全收盘的 K 线。
3. **扩展而非替换实验框架**：继续使用现有 `ExperimentConfig`、`run_experiment`、`ExperimentRegistry` 与 Event Study 统计报告；允许受控扩展，禁止另起一套实验系统。
4. **Finding 提升协议**：将已人工审阅的实验运行提升为长期 Research Finding，而不是停留在单次 run 产物。
5. **跨实验知识索引**：支持按市场、时间周期、特征族、结论状态检索，保留失败与 inconclusive 结果。
6. **为后续策略层预留只读接口**：Finding 可被后续 Strategy Research 引用，但 Phase 4 不生成策略候选。

## 3. 明确非目标

Phase 4 **不得** 包含：

| 排除项 | 原因 |
| --- | --- |
| Trading strategy / EA | 研究层与策略层必须分离 |
| Entry / exit / stop / take-profit / sizing | Event study 不得混入订单规则 |
| Backtesting / walk-forward / paper trading | 属于 Phase 5+ |
| 以盈利能力为目标的参数搜索或优化 | 违反 evidence-first |
| 自动将统计显著升级为 finding 或策略 | 结论必须人工审阅 |
| 替换现有 experiment runner / registry | Phase 2–3 决策权威 |
| 完整 Tick ingestion / tick replay | 长期架构原则，非本阶段范围 |
| 供应商特定交易日历完整建模 | 可并行，但不阻塞 Phase 4 核心契约 |
| 将 Phase 3 pilot 的 inconclusive 结果升级为市场规律 | Pilot 仅验证 workflow |

## 4. 承继的权威决策（不可推翻）

1. Research Finding 回答市场行为证据；Strategy 回答可执行交易规则。两者分层保存。
2. Event condition 只允许当前值与非负历史 lag；未来数据仅用于 outcome。
3. Event study 以 bar 数定义 horizon，不解释为持仓或 PnL。
4. 完整实验必须固定 dataset checksum、config fingerprint、随机种子与 code version。
5. Registry 将 run status 与人工 conclusion 分离；框架不自动判定 hypothesis supported。
6. 失败与 inconclusive 假设必须保留。
7. 高时间周期特征只能使用已完全收盘的 K 线。
8. Train / validation / final-test 时段必须分离；final test 不得影响特征或规则选择。
9. Statistical significance 不能单独证明经济显著性或可交易性。
10. Notebook 只能调用 package API，不能成为核心逻辑唯一实现位置。

## 5. Phase 4 能力分解

Phase 4 由三个可独立验收、但共享契约的子层组成。

```text
┌─────────────────────────────────────────────────────────────┐
│                 Research Findings Knowledge                 │
│   FindingRecord / Index / Promotion / Query / Limitations   │
└─────────────────────────────▲───────────────────────────────┘
                              │ promote reviewed evidence
┌─────────────────────────────┴───────────────────────────────┐
│              Feature-conditioned Experiments                │
│   existing Event Study + FeatureBundle references           │
└─────────────────────────────▲───────────────────────────────┘
                              │ consume causal columns
┌─────────────────────────────┴───────────────────────────────┐
│           Causal Feature & MTF Alignment Layer              │
│   FeatureSpec / Registry / Transform / Warm-up / Provenance │
└─────────────────────────────────────────────────────────────┘
```

### 5.1 Causal Feature Layer

职责：从已校验 OHLCV（及可选已对齐的高时间周期数据）生成可解释、可序列化、可复现的研究特征列。

#### 5.1.1 核心概念

| 概念 | 定义 |
| --- | --- |
| `FeatureSpec` | 单个特征的声明式定义：名称、输入列、参数、lookback、输出 dtype、经济含义 |
| `FeatureFamily` | 特征族标签，如 `price_structure`、`volatility`、`trend`、`session` |
| `FeatureBundle` | 一组 FeatureSpec 的不可变组合，有独立 fingerprint |
| `FeatureManifest` | 一次特征物化运行的 provenance：输入 dataset checksum、bundle fingerprint、code version、warm-up bars、输出 checksum |
| `Warm-up` | 特征首次有效所需的历史 bar 数；warm-up 区间不得作为事件触发样本 |

#### 5.1.2 因果性硬约束

1. 特征变换只能读取 `t` 及更早的数据；禁止任何正向 shift 作为输入。
2. 使用滚动窗口时，窗口右端最多到当前 bar；默认语义必须在 Spec 中写死。
3. 高时间周期输入必须先经 MTF alignment，且只能携带“已收盘”状态。
4. 特征不得内嵌交易决策（不得输出 position、order、PnL）。
5. 特征输出允许 NaN（warm-up / 对齐不足），但事件评估必须显式排除无效行。
6. 每个 FeatureSpec 必须声明：
   - `lookback_bars`
   - `uses_current_bar: bool`（当前 bar 的 OHLC 是否参与计算）
   - `leakage_notes`（已知边界，例如当前 bar 未收盘时不可用于实盘决策的提示；研究层仍按 bar-close 研究语义解释）

#### 5.1.3 建议首批特征族（研究用，非策略信号）

仅作为可解释研究原语，不预设盈利假设：

1. **Price structure**：`close > open`、实体占比、上下影线比、相对前收涨跌。
2. **Return / momentum**：滞后 N bar 简单收益或对数收益（N 固定于 Spec）。
3. **Volatility**：已实现波动、ATR 类真实波幅、高低区间归一化。
4. **Trend context**：仅基于已收盘数据的均线位置 / 斜率状态（离散化优先，便于事件条件）。
5. **Session / calendar proxies**：UTC hour、weekday 等可验证时间特征（在供应商日历完善前标记为 proxy）。

首批实现应少而严，优先可测试的因果性，而不是指标覆盖面。

#### 5.1.4 包布局（建议）

```text
src/aiquantlab/features/
    __init__.py
    models.py          # FeatureSpec, FeatureBundle, FeatureManifest
    registry.py        # 已注册特征定义（代码内 registry，非实验 registry）
    transforms.py      # 纯函数变换
    materialize.py     # 将 bundle 应用到 DataFrame 并写 manifest
    mtf.py             # 多时间框架因果对齐
    exceptions.py
```

顶层 `features/` 目录继续存放研究规范与物化产物元数据，不放核心算法。

### 5.2 Multi-Timeframe Causal Alignment

职责：把高时间周期信息安全地对齐到研究主时间周期。

#### 5.2.1 规则

1. 主研究 timeframe 由实验 `dataset.timeframe` 决定。
2. 高时间周期 bar 只有在其 **收盘时刻之后**，才可被更低时间周期 bar 引用。
3. 对齐键使用规范 UTC bar-open timestamp；收盘时刻 = open + timeframe duration。
4. 不完整边界 K 线继续沿用现有 resampling 决策：移除，不猜测。
5. 对齐结果必须可复现，并写入 FeatureManifest 或独立 `mtf_alignment.json`。

#### 5.2.2 语义示例

对 M15 研究帧引用 H1 特征：

```text
H1 bar [10:00, 11:00) 在 11:00 收盘
M15 bar 10:00 / 10:15 / 10:30 / 10:45 不得使用该 H1 的收盘特征
M15 bar 11:00 起才可使用该已收盘 H1 特征
```

### 5.3 Feature-conditioned Experiment Extension

职责：让现有 Event Study 能消费特征列，而不改变其统计与产物哲学。

#### 5.3.1 扩展原则

- **保留** `HypothesisDefinition`、`EventDefinition`、`EventStudySpecification`、`StatisticalSpecification`。
- **保留** `run_experiment` 的 checksum 校验、artifact 原子发布、registry 生命周期。
- **新增** 可选的特征引用块；无特征引用时行为与 Phase 2–3 完全一致。
- Event condition 仍是列比较；特征只是提前物化到研究帧中的列。

#### 5.3.2 建议配置扩展（示意）

```yaml
schema_version: 2   # 仅当启用特征引用时需要；v1 配置继续有效
experiment_id: XAUUSD-M15-STRUCTURE-VOL-001
# ...现有 hypothesis / dataset / event_study / statistics...

feature_bundle:
  bundle_id: "price_structure_v1"
  bundle_sha256: "<fingerprint>"
  materialized_dataset:
    path: "data/processed/xauusd_m15_features_v1.parquet"
    sha256: "<file sha256>"
  warm_up_bars: 50
```

规则：

1. 若声明 `feature_bundle`，实验加载的必须是带特征的物化数据集，或其等价经 manifest 验证的组合加载路径。
2. 物化数据集必须能追溯到原始 processed OHLCV checksum。
3. Event / eligibility 条件引用的列必须存在于物化帧；缺失则失败，不静默跳过。
4. Warm-up 行不得进入 event 触发集；应在 eligibility 或 runner 预处理中剔除。
5. 不因为引入特征而改变 outcome 定义：仍是 forward return / path extrema / time-to-first-move。

#### 5.3.3 Runner 变更边界

允许：

- 校验 feature manifest 与 dataset checksum 链
- 在 event study 前应用 warm-up mask
- 把 feature manifest 摘要写入 run artifacts

禁止：

- 在 runner 内即时临时发明未登记特征
- 在统计阶段加入成本、滑点、仓位或交易次数优化
- 自动搜索特征阈值或 horizon

### 5.4 Research Findings Knowledge Layer

职责：把 Phase 3 的“单实验登记 + 运行产物”提升为可长期复用的 Findings Knowledge Base。

#### 5.4.1 对象模型

| 对象 | 含义 |
| --- | --- |
| `ExperimentRun` | 已有：一次不可变执行 |
| `ExperimentConclusion` | 已有：人工对某 revision 的结论 |
| `ResearchFinding` | 新增：通过提升门槛的长期知识条目 |
| `FindingIndex` | 新增：跨 finding 的检索视图 |
| `ReplicationLink` | 新增：同一假设族在不同样本 / 市场 / 时段的关联 |

`ResearchFinding` 不是自动从 `supported` 复制而来。它是人工提升后的知识资产，必须绑定证据与限制。

#### 5.4.2 Finding 必备字段

```text
finding_id
title
status                  # candidate | accepted_for_research | rejected | superseded
source_experiments[]    # experiment_id + revision + run_id
market / symbol
timeframe
feature_bundle_ref      # optional
hypothesis_summary
evidence_summary        # 效应方向、horizon、样本量、效应量、q-value 等摘要
limitations[]
economic_rationale      # 允许“尚不充分”
human_reviewer_notes
created_at / reviewed_at
schema_version
```

#### 5.4.3 提升门槛（Promotion Gate）

满足以下条件才允许将实验结论提升为 `ResearchFinding`：

1. 至少一次 `COMPLETED` run，artifact checksum 可复核。
2. Registry conclusion 已人工写入，且不为 `not_reviewed`。
3. 结论为 `supported` 时，notes 必须同时记录：
   - effect size 与样本量判断
   - 已知统计限制（baseline 包含 event、bootstrap 不重采样 baseline 等）
   - 为何 **尚不足以** 形成策略
4. 结论为 `not_supported` / `inconclusive` / `invalid` 同样可以入知识库；失败知识也是资产。
5. 不得仅因 p/q-value 阈值自动提升。
6. Phase 3 pilot 结果默认保持 workflow 验证地位，除非用独立样本完成 replication 后再审阅。

#### 5.4.4 建议目录结构

扩展 README 中的目标结构，而不是替换：

```text
experiments/
├── registry.json                 # 现有实验登记
├── runs/                         # 现有不可变 run artifacts
└── findings/
    ├── index.json                # FindingIndex
    └── FND-0001/
        ├── finding.json
        ├── evidence_links.json   # 指向 run artifacts / registry entries
        ├── limitations.md
        └── conclusion.md
```

`research/` 顶层目录可保存 finding 规范模板与审阅清单；可执行逻辑仍在 `src/aiquantlab`。

#### 5.4.5 查询能力（最小集）

第一版只需结构化过滤，不需要全文搜索引擎：

- by symbol / timeframe
- by conclusion / finding status
- by feature family / bundle_id
- by tag
- by date range of dataset or review

查询结果必须能导航回原始 config、statistical report 与 human notes。

## 6. 研究工作流（Phase 4）

```text
1. 选择已校验 processed OHLCV dataset
2. 声明 FeatureBundle（及可选 MTF 输入）
3. Materialize features -> 带 manifest 的特征数据集
4. 编写/扩展 ExperimentConfig（可引用特征列）
5. run_experiment（现有框架）
6. 人工审阅 statistical report -> registry conclusion
7. （可选）replication：独立时段 / 报价源 / 相关市场
8. 通过 Promotion Gate 写入 ResearchFinding
9. 更新 FindingIndex
```

停止条件：到步骤 8/9 为止。不进入策略假设生成。

## 7. 与后续 Strategy Research 的接口（只定义，不实现）

Phase 4 结束时，Strategy Research 只能消费满足以下契约的 Finding：

```text
AcceptedResearchFinding
    finding_id
    status == accepted_for_research
    source_experiments (immutable refs)
    market_behavior_claim
    applicable_conditions (feature/event summary)
    explicit_non_claims[]   # 例如：不是入场规则；未计入成本；未验证执行
    suggested_research_questions_for_strategy[]  # 可选问题清单，不是策略
```

Strategy Research 后续可以做的事（**非 Phase 4**）：

- 从同一 finding 生成多个 strategy candidates
- 定义 entry/exit/risk 规则
- 比较频率、持有时间、风险特征

Phase 4 最多允许在 finding notes 中记录“可探索的策略研究问题”，禁止输出策略定义文件或候选排行榜。

## 8. 数据与产物契约

### 8.1 特征物化产物

```text
data/processed/<symbol>_<tf>_features_<bundle>.parquet
data/processed/<symbol>_<tf>_features_<bundle>.manifest.json
```

Manifest 至少包含：

- source_ohlcv_sha256
- feature_bundle_sha256
- code_version
- warm_up_bars
- mtf_sources[]（如有）
- output_sha256
- created_at

### 8.2 实验产物增量

在现有 run artifacts 基础上可选新增：

- `feature_manifest.json`（或摘要）
- `promotion_checklist.json`（审阅辅助，不自动结论）

不得删除或改写既有 artifact 语义。

### 8.3 Finding 产物

Finding 目录一经 `accepted_for_research` 或 `rejected` 发布后视为不可变；修正必须 `superseded` 并创建新 finding_id 或新版本字段。

## 9. API 边界（建议）

```python
# 特征层
from aiquantlab.features import (
    FeatureSpec,
    FeatureBundle,
    materialize_features,
    align_higher_timeframe,
)

# 知识层（新建模块，不塞进现有 registry 的实验生命周期）
from aiquantlab.findings import (
    FindingRegistry,
    promote_finding,
    list_findings,
)
```

现有：

```python
from aiquantlab.research import (
    load_experiment_config,
    ExperimentRegistry,
    run_experiment,
)
```

保持稳定。Findings 模块可以读取 ExperimentRegistry，但 ExperimentRegistry 不负责策略，也不自动创建 Finding。

## 10. 验证与测试计划

### 10.1 单元测试重点

1. 特征因果性：构造含未来突变的序列，断言特征在泄漏点之前不变。
2. Warm-up：前 N 行为无效，第 N+1 行起有效。
3. MTF 对齐：收盘前不可见、收盘后可见。
4. Bundle fingerprint：参数或 lookback 变化必改哈希。
5. 实验兼容：无 `feature_bundle` 的 v1 配置结果与现网一致。
6. Promotion gate：缺少 conclusion notes / 无 completed run 时拒绝提升。
7. Finding index：失败与 inconclusive 可检索。

### 10.2 Pilot 建议（设计级，非本文件执行）

Phase 4 pilot 应验证：

- 在固定小样本上物化少量因果特征
- 运行 1–2 个 feature-conditioned event study
- 完成人工 conclusion
- 将至少一条 `inconclusive` 或 `not_supported` 结果写入 finding 知识库

Pilot **不得**：

- 搜索最优特征组合
- 声称发现可交易优势
- 生成策略

## 11. 验收标准

Phase 4 视为设计落地完成，当且仅当：

1. `aiquantlab.features` 可声明、物化、校验因果特征，并持久化 manifest。
2. MTF alignment 通过专门泄漏测试。
3. 现有 experiment framework 在无特征配置下行为不变；有特征配置时可复现运行。
4. Finding registry / index 可从已审阅实验提升知识条目，并保留负面结果。
5. 文档与 STATUS 明确：本阶段无策略、无回测、无优化。
6. 测试覆盖特征因果性、对齐、promotion gate 与回归兼容。

## 12. 实施顺序建议

1. **Feature contracts + registry + materialize**（最小价格结构特征）
2. **MTF alignment**
3. **Experiment config v2 可选扩展 + runner 校验链**
4. **Finding model + promotion API + index**
5. **Phase 4 research pilot（workflow only）**
6. **更新 README / STATUS 的能力状态**（实现后，不在本设计阶段提前改口宣称完成）

## 13. 风险与开放问题

| 风险 / 问题 | 处理态度 |
| --- | --- |
| 特征阈值搜索滑向隐式优化 | 禁止自动搜索；阈值变更必须新 revision，并说明不是优化循环 |
| Finding 过早 `accepted_for_research` | Promotion gate 强制 limitations 与 non-claims |
| 与 Roadmap“Strategy Research Framework”命名混淆 | 本文件将 Phase 4 实现范围定义为研究前置层；策略框架后置 |
| Baseline / bootstrap 已知统计限制 | 继续披露；Finding 必须继承这些 warning |
| 无供应商日历导致 session 特征粗糙 | session 特征标记 proxy；不作为强经济解释 |
| 单进程 registry 限制 | Findings 索引沿用单进程假设，不在本阶段做分布式锁 |

开放问题（本阶段不裁决实现细节）：

1. Finding 版本是新 ID 还是同 ID 递增 version——倾向同 `finding_id` + `version`，与 experiment revision 类比。
2. 特征物化数据集是否必须进入 Git-ignored `data/processed`——是，与现有 raw/processed 政策一致。
3. 是否在 Phase 4 引入简单 regime label——仅当能写成因果 FeatureSpec；否则推迟。

## 14. 决策摘要

1. Phase 4 设计并建设 **Causal Feature & Research Findings Layer**。
2. **不** 创建策略、不优化盈利、不替换现有实验框架。
3. 完成 Research Knowledge Base 中跨实验 finding 管理，使 Research Finding 成为可审计长期资产。
4. 向后续 Strategy Research 只提供 Finding 只读契约与准入门槛。
5. 在 Finding 证据充分且人工确认之前，不得启动策略假设生成实现。

---

本文是 Phase 4 的权威设计输入。实现时应遵循本文件的范围与非目标；若需引入策略层能力，必须单独立项并更新 Roadmap / STATUS，而不是在本阶段悄然扩张。

# AIQuantLab 状态

最后更新：2026-08-07

## 当前里程碑

首个完整 XAUUSD research-to-validation 纵向切片。

固定使用 2015–2017 HistData bid/ask Tick：2015 research、2016 validation、2017 final test。里程碑目标是验证 evidence → finding → candidate → backtest → validation 的契约，而不是产生盈利策略。首个假设和 probe 均被正确拒绝。

## 已完成

- 建立 `src/aiquantlab` package 布局和指定的研究目录。
- 定义支持的时间周期以及 dataset provenance metadata（数据集溯源元数据）。
- 添加严格的 YAML 数据源配置和 CSV 列映射。
- 添加 UTC 时间戳标准化，且不会静默排序或去重。
- 添加规范 OHLCV 校验和结构化 quality report（质量报告）。
- 添加缺失 K 线检测，并支持 continuous、weekday 和 disabled-inference 三种策略。
- 添加带明确锚定方式的 OHLCV timeframe conversion，并移除不完整的边界 K 线。
- 添加带 checksum（校验和）和 provenance（溯源信息）的 processed Parquet manifest。
- 使用小型合成数据集添加针对性的单元测试。
- 添加严格、可证伪的 hypothesis definition 和可复现 ExperimentConfig。
- 添加结构化 event condition；只允许当前值和非负历史 lag，防止事件识别引用未来值。
- 添加 Event study framework，输出 forward return、最大上行/下行幅度及首次正/负收益所需 bar 数。
- 添加 unconditional baseline 和 deterministic IID/moving-block bootstrap 统计报告。
- 添加 confidence interval、standardized effect、bootstrap p-value 和 Benjamini-Hochberg q-value。
- 添加持久化 experiment registry，记录配置 fingerprint、dataset checksum、运行状态和人工结论。
- 添加不可变运行目录，保存 resolved config、hypothesis、observations、baseline、statistical report 和 manifest。
- 强制完整实验从 checksum 匹配的 Parquet 文件加载，并记录 frame fingerprint 和 code version。
- 添加完整实验 runner，并保持 Event Study 与交易执行逻辑分层。
- 检查本地 `XAUUSD_M5.csv` 的 schema、时间范围、重复、排序、价格、volume 和 spread。
- 固定使用 2026-07-13 至 2026-07-24 的两周样本，没有搜索或选择有利区间。
- 通过 ingestion pipeline 处理 2,760 根 M5，并 resample 为 920 根 M15。
- 保留 9 次每日 session gap，不填充、不插值；M15 quality report 记录 36 个 warning。
- 运行 bullish candle 和 bearish candle 两项描述性 Event study，horizon 固定为 1/4/16 bars。
- 使用 non-overlapping event sampling；没有优化 horizon、condition 或统计参数。
- 两项 registry run 均完成，全部 artifact checksum 已复核。
- 生成 `reports/phase3_xauusd_pilot.md`，没有生成 buy/sell signal 或策略。
- 明确 AIQuantLab 的长期定位为 AI-assisted quantitative research laboratory，而不是价格预测器或 EA。
- 在 README 中记录 Research Findings、Strategy Research、Tick-first Data Architecture、validation 和 MT5 execution 的职责边界。
- 添加严格 Tick Parquet 校验与 midpoint M15 聚合，保留 bid/ask OHLC 和 spread 执行列。
- 聚合 76,443,318 条 Tick 为 70,879 根 M15；原始 36 个文件以 source-tree SHA-256 固定。
- 添加 causal feature contract、registry、warm-up、物化 manifest 与 experiment integrity chain。
- 添加人工 finding promotion gate、不可变 finding artifact 和 JSON index；失败 finding 同样保留。
- 添加 immutable strategy candidate contract 和 `pipeline_probe` / qualification 研究门槛。
- 添加 next-bar-open bid/ask 参考执行模型、fixed-fraction accounting、spread/slippage cost 和回撤指标。
- 添加冻结 candidate 的 research / validation / final-test chronological validation 与逐笔交易账本。
- 生成 `reports/xauusd_m15_first_pipeline.md` 以及 checksum-verified validation artifacts。

## 验证结果

- `python -m pytest`：45 项测试通过。
- `python -m pytest --cov=aiquantlab --cov-report=term-missing`：总覆盖率 90%。
- `python -m compileall -q src tests`：通过。
- 在忽略当前环境缺失的第三方 type stubs（类型存根）后，严格项目类型检查未发现内部问题；`pandas-stubs` 和 `types-PyYAML` 已声明在开发依赖中。
- `ruff check src tests scripts`：通过（使用项目声明的 `ruff>=0.6,<1` 范围）。

## 重要决策

- 规范时间戳使用带时区的 UTC 值。
- K 线时间戳默认表示 bar-open time（K 线开盘时刻），并且必须在 metadata 中明确标注。
- 在建立供应商特定的交易时段模型之前，missing-candle 结果只作为 warning（警告）。
- 不静默修复无效数据；默认情况下，processed-data persistence（处理后数据持久化）会拒绝含有质量错误的数据。
- Raw data 和生成产物默认排除在 Git 之外；目录占位文件会被跟踪。
- 参考 Event-driven backtester（事件驱动回测器）将作为权威执行模型；vectorized tools（向量化工具）只作为可选工具。
- Event condition 采用可序列化列比较，只允许当前或历史 lag；未来数据只用于计算研究 outcome。
- Event study 使用 bar 数定义 horizon，不把结果解释为交易入场、持仓或 PnL。
- 完整实验必须固定 dataset checksum、配置 fingerprint、随机种子和 code version。
- Experiment registry 将运行状态与研究结论分离；框架不自动认定 hypothesis supported。
- 默认 baseline 是所有 eligible observations，包含 event observations；统计报告必须披露这一点。
- Phase 3 pilot 的样本窗口、event、horizon、bootstrap 和 seed 均在运行前固定。
- Pilot 结果只能用于验证 workflow，不能升级为候选策略或市场规律。
- Research first、evidence first、validation before deployment 是长期项目原则。
- Research Finding 与 Strategy Definition 必须分层保存；一个 finding 可以产生多个独立策略候选。
- 长期数据架构以不可变 Tick Data 为 single source of truth，timeframe bar 属于可重建的 processed artifact。
- AIQuantLab 是 research and validation platform；MT5 EA 是最终 execution layer。
- 参考执行语义固定为 signal bar 完全收盘后计算、下一 observed bar open 成交；long 支付 ask entry / bid exit。
- 初版禁用 stop loss / take profit，避免 bar 数据无法判定同 bar intrabar 触发顺序。
- 未通过 research gate 的 finding 只能产生 `pipeline_probe`，validation assessment 强制不得 qualifying。
- Final-test 结果不得用于修改同一 candidate revision。

## 待完成

- 为选定的执行环境锁定依赖版本。
- 添加供应商特定的交易日历和节假日支持。
- 添加只使用已收盘高时间周期 K 线的 multi-timeframe alignment（多时间框架对齐）。
- 扩展参考执行模型的 broker contract、financing、latency、market impact 和经验证的 intrabar/tick replay 语义。
- 添加滚动 Walk-forward validation、参数敏感性、bootstrap robustness validation（区别于当前统计置信区间）和 Cross-asset validation。
- 使用独立时期和报价源复核数据语义后，再考虑扩大描述性研究范围。
- 完善 Research Knowledge Base 的 finding 归并、结构化查询、replication link 和长期结论管理。
- 将当前 Parquet-to-M15 聚合扩展为完整 Tick ingestion、通用 M1/M5/M15/H1/H4/D1 generation 和 tick replay。
- 在获得 accepted finding 后扩展通用 Strategy Research Framework；当前 rejected finding 只能产生 pipeline probe。
- 完成 Backtesting、Walk-forward Validation、Paper Trading 后，才评估 MT5 EA Integration。

## 已知问题与限制

- 通用 weekday calendar 不知道 XAUUSD 的每日维护时段或经纪商节假日。
- OHLC K 线无法确定同一根 K 线内止损和止盈触发的先后顺序。
- Tick volume 不是集中式实际成交量，不得按实际成交量解释。
- 首个 HistData pipeline 有 bid/ask 报价，但 latency、market impact、rejected fills、swap 与 broker sizing 仍未建模。
- 在完成兼容性和语义评估前，`vectorbt` 不会作为 core dependency（核心依赖）。
- JSON experiment registry 采用 atomic replacement，但当前只支持 single-process workflow，没有跨进程文件锁。
- Moving-block bootstrap 只能部分缓解重叠 event window 和时间序列依赖。
- Bootstrap confidence interval 当前不重采样 baseline uncertainty，baseline mean 被视为固定值。
- 多 horizon 样本可能因数据尾部没有完整 forward window 而具有不同样本量。
- Tick-first 仍是长期架构原则；当前仅实现已规范化 Tick Parquet 到单一 timeframe 的聚合，尚无完整 ingestion、通用 aggregation 或 tick replay。

## 长期 Roadmap

| Phase | 能力 | 状态 |
| --- | --- | --- |
| Phase 0 | Architecture and Data Foundation | 已完成基础实现 |
| Phase 1 | Data Validation and Processing | 已完成基础实现，provider calendar 等仍待完善 |
| Phase 2 | Research Experiment Framework | 已完成基础实现 |
| Phase 3 | Research Knowledge Base | 最小 finding promotion/index 已实现，完整知识管理待建设 |
| Phase 4 | Strategy Research Framework | 已有单候选纵向切片；通用生成/比较未实现 |
| Phase 5 | Backtesting and Validation | 已有参考执行与固定 chronological splits；完整 validation suite 未实现 |
| Phase 6 | Paper Trading | 未开始 |
| Phase 7 | MT5 EA Integration | 未开始 |

## 实验结果

Phase 3 使用固定两周 XAUUSD M15 小样本完成两项描述性实验：

- `PHASE3-XAUUSD-BULLISH-001`：451 个 raw events，52 个 non-overlapping events。
- `PHASE3-XAUUSD-BEARISH-001`：467 个 raw events，52 个 non-overlapping events。
- 六个 horizon 结果的 excess-return confidence interval 均跨越 0。
- 六个 Benjamini-Hochberg adjusted q-value 均高于 0.05。
- 两项结论均为 `inconclusive`。

这些结果只验证 ingestion、event study、registry 和 statistical reporting。没有形成交易策略，也不能视为稳健市场证据。详细记录见 `reports/phase3_xauusd_pilot.md`。

### First complete XAUUSD pipeline

- 固定研究事件：fully closed bullish M15 candle 且 `body_ratio >= 0.5`；horizon 固定为 4 observed bars。
- 2015 research 有 2,786 个 non-overlapping events；conditional mean `-0.00280%`，baseline `-0.00172%`，excess `-0.00108%`。
- 95% excess-mean CI 为 `[-0.00851%, 0.00586%]`，adjusted q-value `0.618`，结论为 `not_supported`。
- Finding `FND-XAUUSD-M15-STRONG-BULLISH-001` 以 `rejected` 发布并保留全部限制和 non-claims。
- 预声明 long rule 只以 `pipeline_probe` 运行：research / validation / final-test 分别 3,159 / 3,193 / 3,214 笔 primary trades。
- Primary mean/trade 分别为 `-0.0329%` / `-0.0268%` / `-0.0267%`；三个 split 均违反正 expectancy 与 25% drawdown 门槛。
- 添加 1 bp/side adverse slippage 后结果进一步恶化；最终 assessment 为 `not_supported`。
- 该结果证明 rejection、成本建模、样本隔离和不可变报告链路有效，不证明任何市场或策略优势。详见 `reports/xauusd_m15_first_pipeline.md`。

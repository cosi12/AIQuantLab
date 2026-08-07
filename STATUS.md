# AIQuantLab 状态

最后更新：2026-08-07

## 当前里程碑

Phase 2：research experiment framework（研究实验框架）。

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
- 添加完整实验 runner；未添加任何交易策略、订单规则或 Backtesting 逻辑。

## 验证结果

- `python -m pytest`：29 项测试通过。
- `python -m pytest --cov=aiquantlab --cov-report=term-missing`：总覆盖率 91%。
- `python -m compileall -q src tests`：通过。
- 在忽略当前环境缺失的第三方 type stubs（类型存根）后，严格项目类型检查未发现内部问题；`pandas-stubs` 和 `types-PyYAML` 已声明在开发依赖中。
- Ruff 已声明为开发依赖，但当前解释器中尚未安装，因此本轮未运行 Ruff。

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

## 待完成

- 为选定的执行环境锁定依赖版本。
- 添加供应商特定的交易日历和节假日支持。
- 添加 causal feature（因果特征）接口、registry、warm-up metadata 和特征测试。
- 添加只使用已收盘高时间周期 K 线的 multi-timeframe alignment（多时间框架对齐）。
- 添加参考执行模型、accounting、交易成本和风险指标。
- 添加 Walk-forward validation、参数敏感性、bootstrap robustness validation（区别于当前统计置信区间）和 Cross-asset validation。
- 使用小型、经过检查的 XAUUSD 样本对框架进行试运行。

## 已知问题与限制

- 通用 weekday calendar 不知道 XAUUSD 的每日维护时段或经纪商节假日。
- OHLC K 线无法确定同一根 K 线内止损和止盈触发的先后顺序。
- Tick volume 不是集中式实际成交量，不得按实际成交量解释。
- 缺少 bid/ask 数据会限制 spread 和 execution-cost simulation（执行成本模拟）的精度。
- 在完成兼容性和语义评估前，`vectorbt` 不会作为 core dependency（核心依赖）。
- JSON experiment registry 采用 atomic replacement，但当前只支持 single-process workflow，没有跨进程文件锁。
- Moving-block bootstrap 只能部分缓解重叠 event window 和时间序列依赖。
- Bootstrap confidence interval 当前不重采样 baseline uncertainty，baseline mean 被视为固定值。
- 多 horizon 样本可能因数据尾部没有完整 forward window 而具有不同样本量。

## 实验结果

尚未使用真实市场数据测试任何 hypothesis，也未创建任何交易策略。当前测试仅使用合成数据验证研究框架，不能视为市场证据。

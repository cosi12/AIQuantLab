# AIQuantLab Phase 3 XAUUSD Pilot

日期：2026-08-07

## 目的与范围

本 pilot 只验证以下工程流程：

1. Data ingestion pipeline
2. Event study workflow
3. Experiment registry
4. Statistical reporting

研究对象仅为一个固定的 XAUUSD 小样本。没有优化参数、搜索最佳时间窗口、生成 buy/sell signal、创建交易策略或运行 Backtesting。

## 数据来源与检查

原始文件：`data/raw/XAUUSD_M5.csv`

| 项目 | 结果 |
| --- | --- |
| 文件大小 | 347,385 bytes |
| SHA-256 | `4647fe87b8fb8d51f10d7ebc75e1b569dda6136d5156ee067ad43387b956552b` |
| 行数 | 5,000 |
| 时间范围 | 2026-07-10 11:00 至 2026-08-05 13:35 UTC |
| Symbol / timeframe | 全部为 XAUUSD / M5 |
| 时间戳 | 无解析失败、无重复、顺序递增 |
| 价格范围 | 3,959.69 至 4,179.55 |
| Spread 原始值 | min 0、median 5、max 40；CSV 未记录单位 |
| Volume | tick activity，不是集中式实际成交量 |

本地数据清单将同目录 tick 数据标记为 `ICMarketsSC-Demo` MT5 验证数据。M5 首根 bar 与对应 tick 文件的首个 bid 报价一致，因此本 pilot 按 bid OHLC 解释，但 CSV 本身没有独立编码 provider 和 price basis。MetaTrader 5 Python API 文档说明取得的 tick 和 bar 时间使用 UTC：[MQL5 `copy_ticks_range` 文档](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py)。

## 固定样本

选择窗口在实验前固定为：

```text
[2026-07-13 00:00:00 UTC, 2026-07-25 00:00:00 UTC)
```

| 阶段 | 行数 | 实际时间范围 | Missing candle |
| --- | ---: | --- | ---: |
| 完整原始 M5 文件 | 5,000 | 2026-07-10 11:00 至 2026-08-05 13:35 | 216 |
| 固定 M5 样本 | 2,760 | 2026-07-13 01:00 至 2026-07-24 23:55 | 108 |
| Resampled M15 | 920 | 2026-07-13 01:00 至 2026-07-24 23:45 | 36 |

所有数据层级均通过 error-level validation。缺失值对应 9 次可见的每日 `00:00-00:55` session gap；这些 gap 没有填充或插值，继续作为 warning 保留。周末由 `weekdays` calendar 排除。

处理后文件：`data/processed/xauusd_m15_phase3_pilot.parquet`

处理后 SHA-256：`78bee01b0ad9075fb76b9ae3f2a56a83b0d94d9c0c7851a9021238f74743b133`

## 实验设计

两个实验在运行前使用相同固定设置：

- Timeframe：M15
- Forward horizons：1、4、16 bars（15 分钟、1 小时、4 小时）
- Event sampling：`non_overlapping`
- Baseline：所有 eligible observations 的 unconditional forward return
- Bootstrap：moving block，2,000 samples，block size 5
- Random seed：`20260807`
- Multiple testing：Benjamini-Hochberg
- Minimum sample size：30

实验定义：

| Experiment ID | Event | Expected direction |
| --- | --- | --- |
| `PHASE3-XAUUSD-BULLISH-001` | 当前 M15 `close > open` | positive excess return |
| `PHASE3-XAUUSD-BEARISH-001` | 当前 M15 `close < open` | negative excess return |

以上 event 只是描述性分组条件，不是交易信号。

## 统计结果

Excess mean 和 confidence interval 使用 basis points（1 bp = 0.01%）。p-value 和 q-value 是相对于配置中 expected direction 的单侧结果。

### Bullish Candle

Raw events：451；non-overlapping selected events：52。

| Horizon | N | Event mean | Positive probability | Excess mean | 95% CI | p-value | q-value |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 52 | -0.128 bp | 48.1% | -0.060 bp | [-4.440, 4.126] bp | 0.502 | 0.773 |
| 4 | 52 | -6.046 bp | 38.5% | -5.793 bp | [-13.916, 1.947] bp | 0.908 | 0.908 |
| 16 | 51 | -0.973 bp | 39.2% | -0.187 bp | [-15.179, 13.774] bp | 0.515 | 0.773 |

### Bearish Candle

Raw events：467；non-overlapping selected events：52。

| Horizon | N | Event mean | Positive probability | Excess mean | 95% CI | p-value | q-value |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 51 | 2.060 bp | 68.6% | 2.127 bp | [-0.128, 4.192] bp | 0.981 | 0.981 |
| 4 | 51 | 0.786 bp | 49.0% | 1.039 bp | [-4.535, 7.756] bp | 0.632 | 0.948 |
| 16 | 51 | -1.456 bp | 41.2% | -0.669 bp | [-14.263, 11.584] bp | 0.439 | 0.948 |

## 结论

- 所有 excess-return confidence interval 均跨越 0。
- 所有 Benjamini-Hochberg adjusted q-value 均明显高于 0.05。
- 该固定小样本没有为 bullish 或 bearish candle continuation hypothesis 提供支持。
- Bearish 1-bar 结果方向与预期相反，但其区间仍跨越 0；不能据此提出 mean-reversion 策略。
- 两项 registry conclusion 均记录为 `inconclusive`。

本结果的目的只是确认研究管道可以完整、可复现地运行。它不是候选策略，也不能推广到其他时期、报价源或资产。

## Workflow 验证

| 组件 | 状态 |
| --- | --- |
| CSV ingestion、UTC normalization、OHLCV validation | 通过 |
| M5 -> M15 resampling | 通过 |
| Dataset manifest 与 SHA-256 | 通过 |
| Structured hypothesis/event config | 通过 |
| Event study observations 与 baseline | 通过 |
| Experiment registry lifecycle | 两项 run 均 `completed` |
| Artifact integrity | 所有登记文件 checksum 通过 |
| Statistical report | 生成成功，并保留方法限制 warning |

Run IDs：

- Bullish：`0276b407b5ce47e0aef768fbfe5203d4`
- Bearish：`f2b7f95afc614a6baa9ac12f9434a2cb`

两项 run 记录的 code version 均为：

```text
source-tree:670bb8308b188eefe4f51dfd9ff37548983bce392bbbf298b41a35e55b164f26
```

## 限制

- 只有两周数据和单一 local quote source。
- Provider 和 price basis 根据本地 manifest 及 tick 对照解释，M5 CSV 本身未独立编码这些元数据。
- 没有 out-of-sample、Walk-forward validation 或 Cross-asset validation。
- Baseline 包含 event observations，bootstrap confidence interval 未重采样 baseline uncertainty。
- Event sample 约 51-52，足以运行框架但不足以建立稳健市场结论。
- 没有研究 spread、slippage、commission 或执行可行性，因为本阶段不进行 Backtesting。

## 复现

在项目根目录执行：

```powershell
$env:PYTHONPATH='src'
python scripts/run_phase3_xauusd_pilot.py --overwrite
```

脚本会重新运行 ingestion、固定窗口选择、M15 resampling、两项 event study、registry 更新和 artifact 生成。每次 run 使用新 run ID，但配置 fingerprint、dataset checksum、random seed 和 source-tree code fingerprint 均会被记录。

本次运行环境：Python 3.13.2、NumPy 2.3.0、pandas 3.0.2、PyArrow 23.0.1、Pydantic 2.10.3。项目尚未生成 dependency lockfile，因此跨版本 Parquet byte-level checksum 可能变化；重新运行前应保留本环境或先锁定依赖。

# AIQuantLab Web 架构

版本：v0.1  
最后更新：2026-08-07

本文档定义 AIQuantLab Web Application 的架构边界。它是 Web 层的权威设计约束，任何 Web 层改动都必须先与本文档一致。

Web Application 的定位是 **research control interface（研究控制界面）**，不是 trading terminal，不是 signal dashboard，也不是 execution interface。

## 目录

1. [设计目标与非目标](#1-设计目标与非目标)
2. [整体架构](#2-整体架构)
3. [Frontend 职责](#3-frontend-职责)
4. [Backend 职责](#4-backend-职责)
5. [API 边界](#5-api-边界)
6. [数据访问策略](#6-数据访问策略)
7. [页面职责](#7-页面职责)
8. [状态词汇与展示规则](#8-状态词汇与展示规则)
9. [未来扩展点](#9-未来扩展点)
10. [目录结构](#10-目录结构)
11. [测试策略](#101-测试策略)
12. [已知限制](#11-已知限制)

---

## 1. 设计目标与非目标

### 1.1 Web 层要回答的问题

| 研究问题 | 承载页面 |
| --- | --- |
| 用了什么数据？ | Dataset Explorer / Dataset Detail |
| 这份数据可信吗？ | Dataset Detail（quality report、provenance、checksum 校验） |
| 检验了什么假设？ | Experiment Detail（hypothesis、falsification criteria） |
| 做了什么实验？ | Experiment Detail（resolved config、event、horizon、statistics spec） |
| 产生了什么证据？ | Experiment Detail（statistical report）/ Report Viewer |
| 得到了什么结论？ | Experiment Detail（conclusion + notes）/ Research Findings |
| 策略候选为什么被接受或拒绝？ | Strategy Candidate Detail（validation report、失败原因、warnings） |

### 1.2 Web 层禁止的行为

Web 层是**只读观察层**。以下行为在架构上被禁止，而不是靠约定避免：

- 不把被拒绝的实验展示为成功策略。
- 不隐藏统计不确定性：confidence interval、q-value、样本量、warnings 必须与点估计同屏展示。
- 不自动宣称盈利能力。
- 不替代人工研究判断（Web 层不写入 conclusion，不改写 finding，不改写 candidate）。
- 不生成交易信号。
- 不执行交易。
- 不向 artifact 目录写入任何文件。

### 1.3 v0.1 范围

v0.1 只实现 Dashboard、Dataset Explorer、Research Explorer、Report Viewer、Strategy Candidate Explorer，以及 AI Agent / Execution Layer / Settings 的路由占位页。占位页明确标注"未实现"，不展示虚构数据。

---

## 2. 整体架构

```text
┌──────────────────────────────────────────────────────────────┐
│  Browser（React SPA，中文 UI）                                │
│  路由、导航、页面渲染、只读展示                                 │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP / JSON（仅 GET）
┌───────────────────────────▼──────────────────────────────────┐
│  Web Backend（FastAPI，aiquantlab_web）                       │
│  artifact 发现 → 宽松解析 → 派生展示状态 → API schema          │
│  只读文件访问；无数据库；无写入路径                             │
└───────────────────────────┬──────────────────────────────────┘
                            │ 只读文件系统访问
┌───────────────────────────▼──────────────────────────────────┐
│  AIQuantLab Artifact Layer（single source of truth）          │
│  data/processed/*.manifest.json                              │
│  experiments/**/(experiment_registry|*_registry).json         │
│  experiments/**/research_runs/**                              │
│  experiments/**/findings/**                                   │
│  experiments/**/validation/**                                 │
│  reports/*.md                                                 │
└───────────────────────────┬──────────────────────────────────┘
                            │ 由 CLI / scripts 生成
┌───────────────────────────▼──────────────────────────────────┐
│  Research Engine（src/aiquantlab，Web 层不修改）               │
│  data / features / research / findings / strategies /          │
│  backtest / validation                                        │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 依赖方向

```text
frontend ──► backend ──► artifacts ◄── research engine
                  └────► src/aiquantlab（仅导入枚举与只读读取函数）
```

强制约束：

- **`src/aiquantlab` 不得导入 `aiquantlab_web`。** 研究引擎对 Web 层零感知。
- Web 层可以导入 `src/aiquantlab` 的**枚举与只读读取工具**，用于统一状态词汇，避免在 Web 层重复定义 `not_supported`、`pipeline_probe` 之类的字面量。
- Web 层不得导入研究引擎的 runner、registry 写入方法或 backtest engine。
- Web 层不得调用任何产生 artifact 的代码路径。

### 2.2 为什么采用前后端分离

| 备选方案 | 否决原因 |
| --- | --- |
| 在研究引擎内嵌模板渲染 | UI 逻辑会污染核心研究模块，违反分层原则 |
| Streamlit / Gradio 单页脚本 | 无法支撑多页面信息层级，状态与路由不可控，难以扩展到 Agent 与实时监控 |
| 前端直接读取本地文件 | 浏览器无法安全遍历文件系统；checksum 校验与路径白名单必须在服务端完成 |

FastAPI + React 的组合让 artifact 解析、路径白名单、完整性校验集中在服务端，前端只消费稳定的 JSON 契约。

---

## 3. Frontend 职责

### 3.1 负责

- 路由与导航（多页面结构，Dashboard 只是入口）。
- 把后端 JSON 渲染为研究可读的信息层级。
- 中文 UI 文案、状态标签与研究术语对照。
- 展示不确定性：把置信区间、q-value、样本量、warnings 与点估计并列。
- Markdown 报告与 JSON artifact 的浏览器内查看。
- 加载态、空态、错误态的显式提示。

### 3.2 不负责

- 统计计算。任何指标都不在前端重新计算或重新推导。
- artifact 路径拼接与文件读取。
- 状态判定逻辑。展示状态由后端派生并下发，前端只负责映射到中文标签与配色。
- 数据缓存持久化。前端只做进程内内存缓存。

### 3.3 技术选择

| 项 | 选择 | 理由 |
| --- | --- | --- |
| 框架 | React 19 + TypeScript | 类型化契约，避免字段名漂移 |
| 构建 | Vite | 无需服务端渲染；研究界面是纯客户端只读视图 |
| 路由 | react-router | 多页面结构的最小可行方案 |
| 样式 | 原生 CSS（单份设计令牌） | 拒绝引入 UI 框架；实验室界面需要密集信息排版，而非组件库风格 |
| Markdown | marked | 报告查看器的唯一渲染需求 |

不引入图表库、状态管理库、组件库。v0.1 的目标是功能正确与信息可读，不是视觉复杂度。

---

## 4. Backend 职责

### 4.1 负责

1. **artifact 发现（discovery）**：扫描白名单目录，建立 dataset / experiment / finding / candidate / report 索引。
2. **宽松解析（lenient parsing）**：把 artifact JSON 解析为 dict，再按需提取字段。
3. **展示状态派生**：把 `purpose`、`research_gate_passed`、`assessment`、finding status 组合为单一 `display_status`。
4. **完整性校验**：按需计算 dataset 文件 SHA-256 并与 manifest 比对。
5. **路径白名单**：所有文件访问必须落在允许的 artifact 根目录内。
6. **稳定 API schema**：用 pydantic 定义响应契约，与前端 TypeScript 类型一一对应。

### 4.2 不负责

- 运行实验、生成 finding、执行回测、执行验证。
- 写入任何文件。
- 用户认证与多用户隔离（v0.1 假定本地单研究者使用）。

### 4.3 为什么使用宽松解析而不是核心 pydantic 模型

Artifact 是**不可变历史记录**，可能使用旧 schema：

- `experiments/phase3_xauusd_runs/**/config.resolved.json` 是 `schema_version: 1`，没有 `feature_dataset`。
- `experiments/xauusd_m15_first_pipeline/research_runs/**/config.resolved.json` 是 `schema_version: 2`。
- `data/processed/xauusd_m15_phase3_pilot.parquet.manifest.json` 是 `schema_version: 1`，缺少 `columns`。

核心模型使用 `extra="forbid"` 且字段约束严格。如果 Web 层用核心模型强校验历史 artifact，一次核心 schema 升级就会让旧实验在界面上整体消失——这与"失败研究是有价值的知识，必须保持可见"直接冲突。

因此规则是：

- **写入路径（研究引擎）继续使用严格模型。** 严格性保护的是新产出的正确性。
- **读取路径（Web 层）使用宽松解析。** 缺字段渲染为"未记录"，不使整条记录不可访问。
- Web 层仍导入核心**枚举**（`ExperimentConclusion`、`FindingStatus`、`CandidatePurpose`、`CandidateAssessment`）作为状态词汇的单一来源。未知状态值原样透传并在 UI 标为未知，不静默改写。

---

## 5. API 边界

### 5.1 通用约定

- 前缀：`/api`。
- 方法：**只有 `GET`**。v0.1 不存在任何写入端点。这是架构约束，不是暂缺功能。
- 编码：JSON，UTF-8。时间统一为 ISO-8601 UTC 字符串。
- 错误：`404` artifact 不存在；`400` 参数非法；`422` artifact 无法解析。错误体为 `{"detail": "..."}`。
- ID：使用 artifact 自身标识符（`dataset_id` = manifest 文件名去掉后缀；`experiment_id` + `revision`；`finding_id`；`candidate_id`；`report_id` = 报告文件名 stem）。不引入代理主键。

### 5.2 端点清单

| 端点 | 用途 |
| --- | --- |
| `GET /api/health` | 服务与 artifact 根目录可用性 |
| `GET /api/overview` | Dashboard 总览：计数、最近实验、最新研究结果、系统状态 |
| `GET /api/datasets` | 数据集列表 |
| `GET /api/datasets/{dataset_id}` | 数据集详情：metadata、provenance、quality report、处理信息 |
| `GET /api/datasets/{dataset_id}/integrity` | 按需 SHA-256 校验（可能耗时，前端显式触发） |
| `GET /api/datasets/{dataset_id}/preview` | 首/尾若干根 K 线预览 |
| `GET /api/quality-reports` | 全部数据集质量报告汇总 |
| `GET /api/experiments` | 实验列表：名称、假设、状态、结论、创建时间 |
| `GET /api/experiments/{experiment_id}` | 实验详情：假设、resolved config、event、horizon、统计证据、run 列表 |
| `GET /api/experiments/{experiment_id}/runs/{run_id}/artifacts` | run artifact 清单（含 checksum） |
| `GET /api/experiments/{experiment_id}/runs/{run_id}/artifacts/{artifact_name}` | 单个 JSON artifact 原文 |
| `GET /api/findings` | 研究发现列表 |
| `GET /api/findings/{finding_id}` | 研究发现详情：claim、证据链、限制、非声明、评审记录 |
| `GET /api/candidates` | 策略候选列表 |
| `GET /api/candidates/{candidate_id}` | 策略候选详情：规则、来源证据、validation plan 与 report |
| `GET /api/reports` | Markdown 报告列表 |
| `GET /api/reports/{report_id}` | Markdown 报告原文 |

`experiment_id` 在 URL 中唯一，`revision` 通过查询参数 `?revision=` 指定，默认取最新 revision。

### 5.3 契约稳定性规则

- 已发布字段不重命名、不改变语义；只做新增。
- 列表端点返回摘要，详情端点返回完整内容。列表端点不得因为某个页面需要而无限膨胀。
- 派生字段（如 `display_status`）必须与其来源字段（`purpose`、`assessment`、`research_gate_passed`）同时下发，使前端可以展示判定依据而不是只展示结论。

---

## 6. 数据访问策略

### 6.1 Artifact 是唯一事实来源

Web 层**不引入数据库**，**不复制研究数据**，**不建立派生存储**。所有内容在请求时从 artifact 文件读取。

理由：

- artifact 已经带有 checksum、provenance 与不可变运行目录，本身就是审计级记录。
- 引入数据库会立即产生"数据库内容与 artifact 不一致时以谁为准"的问题，破坏证据链。
- 当前数据规模（3 个 dataset manifest、2 个 registry、3 个实验条目、1 个 finding、1 个 candidate、2 份报告）远未到需要索引的量级。

引入数据库的门槛是明确的：**当出现跨 artifact 的结构化查询需求（例如按 symbol、时间范围、effect size 联合筛选上千个 finding）时才重新评估**，且届时数据库只能作为可从 artifact 完整重建的缓存。

### 6.2 根目录解析

后端通过 `AIQUANTLAB_ROOT` 环境变量确定仓库根目录；未设置时从模块位置向上定位包含 `pyproject.toml` 的目录。允许访问的子树：

```text
data/processed/     dataset manifest 与 parquet
experiments/        registry、research run、finding、validation
reports/            Markdown 报告
```

`data/raw/` **不在**白名单内。原始供应商数据不通过 Web 层暴露：它可能带有授权限制，且未经校验的原始数据不应作为研究界面的展示对象。

### 6.2.1 启动方式

```powershell
python -m pip install -e ".[web,dev]"
python -m uvicorn aiquantlab_web.app:app --reload --app-dir web/backend
```

```powershell
cd web/frontend
npm install
npm run dev
```

开发期前端由 Vite 在 `5173` 提供服务，并把 `/api` 代理到 `127.0.0.1:8000`；后端 CORS 只放行这两个本地来源。生产部署应由同源反向代理同时托管静态资源与 `/api`，此时 CORS 配置不再需要。

### 6.3 路径安全

所有由请求参数推导出的路径必须经过 `artifacts/paths.py` 的两道检查：

- `ensure_within(roots, candidate)`：解析为绝对路径后验证其位于允许根目录之内，否则抛 `ArtifactPathError`（映射为 `400`）。
- `ensure_plain_name(name)`：artifact 名称参数不接受路径分隔符、`..` 与前导点。

这两道检查必须在 artifact 层独立成立，不能依赖 HTTP 路由的路径归一化：`GET` 路径中的 `%2F` 会被 Starlette 先行解码并变成路由未命中，因此路由层的拒绝是附带效果，不是安全边界。

### 6.4 缓存策略

- 目录扫描结果按 **文件 mtime + size** 组成的指纹缓存在进程内。artifact 变化后自动失效。
- SHA-256 校验**不**随列表请求自动执行（70,879 行 parquet 每次校验都做会让列表页变慢），只在 `/integrity` 端点显式触发。
- 不使用跨进程缓存，不使用磁盘缓存。

### 6.5 Registry 与 run 目录的关联

registry 中的 `artifact_directory` 记录的是**生成时的绝对路径**（例如 `C:\Users\...`），仓库迁移后会失效。因此 run 目录解析顺序为：

1. 按约定结构在 artifact 根内查找 `<registry 所在目录>/**/<experiment_id>/revision-<n>/<run_id>/`。
2. 仅当 1 失败时，才回退使用 registry 记录的绝对路径，且仍须通过路径白名单检查。

这让 Web 层不依赖机器特定路径。

---

## 7. 页面职责

```text
AIQuantLab Web Application
├── /                        Dashboard（总览）
├── /data                    数据集列表
│   ├── /data/:datasetId     数据集详情（metadata / provenance / 质量报告 / 处理信息）
│   └── /data/quality        数据质量报告汇总
├── /research                实验列表
│   ├── /research/:experimentId       实验详情（假设 / 配置 / 统计证据 / 结论）
│   ├── /research/findings            研究发现列表
│   └── /research/findings/:findingId 研究发现详情
├── /strategies              策略候选列表
│   └── /strategies/:candidateId      候选详情（规则 / 验证报告 / 拒绝原因）
├── /reports                 报告列表
│   └── /reports/:reportId   报告查看器（Markdown）
├── /agent                   AI 研究助手（占位，未实现）
├── /execution               执行层（占位，未实现）
└── /settings                设置（artifact 根目录与运行环境信息）
```

### 7.1 单页职责约束

| 页面 | 必须做 | 禁止做 |
| --- | --- | --- |
| Dashboard | 系统规模计数、最近实验、最新研究结论、系统状态 | 承载数据集/实验/策略的完整功能；给出任何"当前可交易"暗示 |
| Dataset 列表 | 名称、symbol、timeframe、时间范围、记录数、checksum、校验状态 | 隐藏 quality warning 数量 |
| Dataset 详情 | provenance notes、质量问题明细与样本、时间戳约定、价格基准、volume 类型 | 把 warning 显示为"通过"而不给出数量 |
| 实验列表 | 名称、假设、run 状态、人工结论、创建时间 | 按结论好坏排序或折叠失败实验 |
| 实验详情 | 研究问题、可证伪标准、resolved config、event 定义、forward horizon、统计证据、run 完整性链 | 只展示点估计而不展示置信区间与 q-value |
| 研究发现 | claim、状态、证据链 checksum、限制、显式非声明、评审记录 | 隐藏 `rejected` 状态的 finding |
| 策略候选 | 规则、来源 finding、证据 checksum、purpose、验证结论、逐 split 指标与失败原因 | 把 `pipeline_probe` 展示为可交易策略；隐藏被拒绝的候选 |
| 报告查看器 | Markdown 渲染、JSON artifact 查看 | 编辑或重新生成报告 |

### 7.2 信息层级原则

每个详情页遵循同一顺序：**身份 → 结论 → 证据 → 限制**。

结论紧跟身份出现，避免研究者在滚动完统计表格之后才看到"未被支持"。限制与非声明必须与证据同页，不放在折叠区域的默认收起状态之外。

---

## 8. 状态词汇与展示规则

### 8.1 实验结论（来自 `ExperimentConclusion`）

| 值 | 中文标签 | 语义 |
| --- | --- | --- |
| `not_reviewed` | 未评审 | 已有 run，但无人工结论 |
| `supported` | 假设被支持 | 人工判定证据支持预声明方向 |
| `not_supported` | 假设未被支持 | 人工判定证据不支持预声明方向 |
| `inconclusive` | 结论不确定 | 证据不足以判定任一方向 |
| `invalid` | 实验无效 | 实验本身存在缺陷 |

框架不自动推断结论；未评审就显示未评审。

### 8.2 研究发现状态（来自 `FindingStatus`）

| 值 | 中文标签 |
| --- | --- |
| `accepted_for_research` | 已接受用于后续研究 |
| `rejected` | 已拒绝 |

`rejected` 的 finding 永久保留并可浏览。失败研究是知识资产。

### 8.3 策略候选展示状态（后端派生）

派生输入：`purpose`、`research_gate_passed`、来源 finding 的 `status`、validation report 的 `assessment`。

判定顺序（先命中先返回）：

| 顺序 | 条件 | `display_status` | 中文标签 |
| --- | --- | --- | --- |
| 1 | `purpose == pipeline_probe` | `PIPELINE_PROBE` | 流程探针 |
| 2 | 来源 finding 状态为 `rejected` | `REJECTED` | 已拒绝 |
| 3 | 无 validation report | `PENDING_REVIEW` | 待验证 |
| 4 | `assessment == supported` | `SUPPORTED` | 验证支持 |
| 5 | `assessment == not_supported` | `NOT_SUPPORTED` | 验证未支持 |
| 6 | `assessment == inconclusive` | `PENDING_REVIEW` | 待验证 |

`PIPELINE_PROBE` 优先级最高，因为它是最强的诚实性信号：这类候选在契约上就**不可能**取得 qualification，UI 必须首先说明这一点，再展示其验证指标。

`display_status` 永远与来源字段一起下发，UI 同时展示派生结论和判定依据。

### 8.4 强制免责展示

以下内容不是可选的 UI 装饰，而是页面契约：

- 策略候选页必须展示 `purpose` 说明。`pipeline_probe` 必须显示"该候选仅用于验证流程链路，不构成策略结论"。
- validation report 的 `warnings` 数组必须完整展示，不截断。
- finding 的 `limitations` 与 `explicit_non_claims` 必须完整展示。
- 统计报告的 `warnings` 必须与 horizon 指标同屏。
- 正收益指标不使用"盈利""收益机会"等表述，只使用中性的"均值收益""累计收益"。

---

## 9. 未来扩展点

架构预留以下扩展位。目标是后续开发**不需要重建 Web 层**。

### 9.1 LLM Research Agent

目标流程：

```text
Research Data → AI Research Agent → Hypothesis Generation
              → Experiment Engine → Human Review → Strategy Candidate
```

预留方式：

- 路由占位 `/agent` 已存在，导航结构无需改动。
- Agent 的产出必须是 **experiment config 提案**，写入 `experiments/proposals/`，成为新的 artifact 类型；Web 层新增 `GET /api/proposals` 与 `POST /api/proposals/{id}/review` 即可接入。
- Agent **不得**绕过 experiment runner，不得写入 finding，不得写入 conclusion。人工评审仍是唯一的 finding 发布路径。
- 这是第一个引入写端点的场景。届时需要在本文档补充写路径的鉴权与幂等规则，`GET`-only 约束在此明确解除，但仅限 proposal 与 review 资源。

### 9.2 Paper Trading

- 新增 artifact 根 `paper_trading/`，结构与 `validation/` 对称（plan + report + 逐笔账本）。
- 新增路由段 `/execution/paper`，复用现有 split 指标表格组件。
- Paper trading 结果是**证据的一种**，进入相同的"身份 → 结论 → 证据 → 限制"版式，不获得特殊待遇。

### 9.3 MT5 Execution

- Web 层只做**只读监控与审计**：展示 EA 配置指纹、已部署 candidate revision、实际成交与参考执行模型的偏差。
- 下单指令不经过本 Web 层。Web 后端不持有交易凭证，不暴露下单端点。
- 前置条件保持不变：Backtesting、Walk-forward Validation、Paper Trading 全部完成后才评估 MT5 集成。

### 9.4 实时监控

- 当前所有端点为请求-响应模式。实时能力通过新增 `GET /api/stream/{topic}`（SSE）实现，不改造既有端点。
- 选择 SSE 而非 WebSocket：监控数据是服务端单向推送，SSE 依赖更少且可直接复用 HTTP 基础设施。
- 前端以独立 hook 订阅，页面组件保持只读渲染语义。

### 9.5 多用户与鉴权

v0.1 假定本地单研究者。引入多用户时：

- 鉴权在 FastAPI middleware 层加入，不侵入 artifact 读取层。
- artifact 层已经是无状态纯函数，可直接按用户可见范围过滤根目录。

---

## 10. 目录结构

```text
AIQuantLab
├── src/aiquantlab/              研究引擎（Web 层不修改）
├── web/
│   ├── backend/
│   │   └── aiquantlab_web/
│   │       ├── app.py           FastAPI 应用工厂
│   │       ├── settings.py      artifact 根目录解析
│   │       ├── errors.py        领域异常 → HTTP 映射
│   │       ├── schemas.py       API 响应契约
│   │       ├── artifacts/       artifact 发现与宽松解析
│   │       │   ├── paths.py     路径白名单与 JSON 读取
│   │       │   ├── datasets.py
│   │       │   ├── experiments.py
│   │       │   ├── findings.py
│   │       │   ├── candidates.py
│   │       │   ├── reports.py
│   │       │   └── overview.py
│   │       └── routers/         HTTP 层，仅做参数校验与序列化
│   └── frontend/
│       ├── src/
│       │   ├── api/             类型化 API client
│       │   ├── components/      通用只读展示组件
│       │   ├── pages/           页面
│       │   ├── labels.ts        英文状态 → 中文标签映射
│       │   └── styles.css       设计令牌与布局
│       └── vite.config.ts
├── docs/WEB_ARCHITECTURE.md
└── tests/web/
    ├── synthetic_repository.py  合成 artifact 仓库构造器
    ├── conftest.py              ArtifactRoots 与 TestClient fixture
    └── test_*.py                后端 API 与 artifact 层测试
```

分层规则：

- `routers/` 不含 artifact 解析逻辑，只做参数校验、调用 artifacts 层、返回 schema。
- `artifacts/` 不含 HTTP 概念，抛领域异常，可被 CLI 或测试直接调用。
- `schemas.py` 是前后端唯一契约面，前端 TypeScript 类型与之对应。

---

## 10.1 测试策略

`tests/web/` 针对 `tests/web/synthetic_repository.py` 构造的合成 artifact 仓库运行，**不针对仓库中的真实研究产物**。

理由：真实产物会随研究推进变化。若测试断言真实 artifact 的数值或结论，测试就被绑定在当前研究结论上——一次新实验或一次结论修订都会让测试失败，且失败信号与 Web 层的正确性无关。

合成仓库刻意包含以下"不利形状"，用于把研究诚实性约束固定成可执行断言：

| 合成条件 | 被固定的约束 |
| --- | --- |
| 质量报告 `passed = true` 但含 1 条 warning | warning 数量不得被 `passed` 掩盖 |
| feature manifest 自身没有 symbol / timeframe | 继承而来的 provenance 必须标注 `provenance_inherited` |
| 一次 `failed` run 与一次 `completed` run 并存 | 失败 run 必须计数并可见；失败 run 不得凭空生成统计报告 |
| registry 中 `artifact_directory` 指向不存在的绝对路径 | run 目录必须能按约定结构定位 |
| 两个 horizon 的置信区间均跨零、q 值均高于阈值 | 不得呈现为显著 |
| `purpose = pipeline_probe` 且来源 finding 为 `rejected` | `display_status` 必须是 `PIPELINE_PROBE` |
| 空仓库（artifact 根目录全部缺失） | 集合端点返回空数组；系统检查必须报告目录不可用 |

此外有两项结构性断言：`GET /openapi.json` 中所有端点的方法集合必须恰好为 `{"get"}`（把"无写端点"变成可执行约束），以及 `ensure_within` / `ensure_plain_name` 的越权拒绝在 artifact 层直接测试。

---

## 11. 已知限制

- 无鉴权、无多用户隔离；默认仅本地访问。
- 无写端点，因此无法在界面上登记结论、发布 finding 或运行实验。这些操作仍通过 `scripts/` 完成，属于有意设计。
- 目录扫描为同步阻塞 IO。当前 artifact 数量下可忽略，artifact 规模显著增长后需要引入异步或后台索引。
- `/integrity` 端点对大 parquet 计算完整 SHA-256，是有意的慢操作，必须由用户显式触发。
- Dataset 预览读取整个 parquet 文件后再切片，未做 row group 级别裁剪。
- Markdown 渲染信任本地 artifact 内容，未做 HTML 清洗。这依赖"artifact 由本仓库脚本生成"这一前提；一旦引入外部来源报告，必须加入清洗层。
- registry 的 `artifact_directory` 为绝对路径，跨机器不可移植；Web 层已用约定结构查找规避，但 registry 本身的这一限制仍存在。

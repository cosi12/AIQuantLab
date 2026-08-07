/**
 * 未实现能力的占位页。
 *
 * 占位页明确标注"未实现"，不展示任何虚构数据或模拟指标。
 */

import { Notice, PageHeader, Section } from "../components/primitives";

export function AgentPlaceholderPage() {
  return (
    <>
      <PageHeader
        title="AI 研究助手"
        subtitle="尚未实现。此页面保留路由位置，使后续接入不需要改动导航结构。"
      />
      <Notice tone="neutral" title="当前状态：未实现">
        本项目中不存在任何自动化 AI agent 组件。"AI 辅助"描述的是研究协作方式，人类研究者与 AI 助手使用同一套可复现契约。
      </Notice>
      <Section title="规划中的流程">
        <pre className="json">{`研究数据
  ↓
AI 研究助手
  ↓
生成假设提案
  ↓
实验引擎（既有，不可绕过）
  ↓
人工评审
  ↓
策略候选`}</pre>
      </Section>
      <Section title="设计约束">
        <ul className="plain-list">
          <li>AI 的产出只能是实验配置提案，成为新的 artifact 类型，不直接写入研究发现。</li>
          <li>AI 不得绕过数据质量检查、统计检验或人工研究结论。</li>
          <li>人工评审仍是研究发现发布的唯一路径。</li>
          <li>AI 协助研究，不替代验证。</li>
        </ul>
      </Section>
    </>
  );
}

export function ExecutionPlaceholderPage() {
  return (
    <>
      <PageHeader
        title="执行层"
        subtitle="尚未实现。Paper Trading 与 MT5 执行都需要在完整验证之后才进入评估。"
      />
      <Notice tone="caution" title="当前状态：未实现">
        先验证后部署。在完成回测、walk-forward 验证与 paper trading 之前，不评估任何实盘执行集成。本 Web 层不持有交易凭证，也不提供下单端点。
      </Notice>
      <Section title="Paper Trading">
        <p className="text-muted">
          规划中的 paper trading 产物与验证产物结构对称（计划 + 报告 + 逐笔账本），并进入与其他证据相同的展示版式。Paper trading 结果只是证据的一种，不获得特殊待遇。
        </p>
      </Section>
      <Section title="MT5 集成">
        <p className="text-muted">
          Web 层在该场景中只做只读监控与审计：展示已部署候选修订、EA 配置指纹，以及实际成交与参考执行模型的偏差。下单指令不经过本 Web 层。
        </p>
      </Section>
    </>
  );
}

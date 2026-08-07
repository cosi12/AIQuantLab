/**
 * 策略候选详情与验证报告。
 *
 * 展示要求：purpose 说明、验证 warnings、逐 split 指标与失败原因必须完整呈现。
 * 收益指标一律使用中性表述，不出现"盈利"这类暗示可交易性的措辞。
 */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useResource } from "../api/client";
import type { CandidateDetail, SplitValidationResult } from "../api/types";
import { EventDefinitionView } from "../components/EventDefinitionView";
import { JsonViewer } from "../components/JsonViewer";
import {
  Badge,
  Empty,
  KeyValues,
  Mono,
  Notice,
  PageHeader,
  Resource,
  Section,
  StringList,
  ToneBadge,
} from "../components/primitives";
import {
  assessmentLabel,
  candidateStatusLabel,
  failureLabel,
  findingStatusLabel,
  formatBoolean,
  formatBytes,
  formatDate,
  formatDateTime,
  formatInteger,
  formatNumber,
  formatPercent,
  purposeLabel,
  splitRoleLabel,
  term,
} from "../labels";

function SplitResultTable({ results }: { results: SplitValidationResult[] }) {
  return (
    <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            <th>时段</th>
            <th>执行模型</th>
            <th className="numeric">交易笔数</th>
            <th className="numeric">单笔均值收益</th>
            <th className="numeric">单笔中位收益</th>
            <th className="numeric">累计收益</th>
            <th className="numeric">胜率</th>
            <th className="numeric">最大回撤</th>
            <th className="numeric">累计执行成本</th>
            <th>标准</th>
          </tr>
        </thead>
        <tbody>
          {results.flatMap((result) => {
            const rows = [
              { key: "primary", label: "主执行模型", summary: result.primary },
              { key: "stress", label: "压力（加滑点）", summary: result.stress },
            ];
            return rows.map((row, index) => (
              <tr key={`${result.split.name}-${row.key}`}>
                {index === 0 ? (
                  <td rowSpan={2}>
                    <Badge label={splitRoleLabel(result.split.role)} />
                    <div className="text-faint mono">{result.split.name}</div>
                    <div className="text-faint nowrap">
                      {formatDate(result.split.start)} — {formatDate(result.split.end)}
                    </div>
                  </td>
                ) : null}
                <td className="nowrap">{row.label}</td>
                <td className="numeric">{formatInteger(row.summary.trade_count)}</td>
                <td className="numeric">{formatPercent(row.summary.mean_trade_return, 4)}</td>
                <td className="numeric">{formatPercent(row.summary.median_trade_return, 4)}</td>
                <td className="numeric">{formatPercent(row.summary.cumulative_return, 2)}</td>
                <td className="numeric">{formatPercent(row.summary.win_rate, 2)}</td>
                <td className="numeric">{formatPercent(row.summary.maximum_drawdown, 2)}</td>
                <td className="numeric">
                  {formatPercent(row.summary.total_execution_cost_return, 2)}
                </td>
                {index === 0 ? (
                  <td rowSpan={2}>
                    {result.criteria_passed === true ? (
                      <ToneBadge text="全部通过" tone="positive" />
                    ) : (
                      <ToneBadge text="未通过" tone="negative" />
                    )}
                    {result.failures.length > 0 ? (
                      <ul className="plain-list" style={{ marginTop: 6 }}>
                        {result.failures.map((failure) => (
                          <li key={failure} className="text-muted">
                            {failureLabel(failure)}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </td>
                ) : null}
              </tr>
            ));
          })}
        </tbody>
      </table>
    </div>
  );
}

export function CandidateDetailPage() {
  const { candidateId = "" } = useParams();
  const [showManifest, setShowManifest] = useState(false);
  const state = useResource<CandidateDetail>(`/candidates/${encodeURIComponent(candidateId)}`);

  return (
    <Resource state={state}>
      {(candidate) => (
        <>
          <PageHeader
            breadcrumb={<Link to="/strategies">策略候选</Link>}
            title={candidate.title}
            meta={
              <>
                <Badge label={candidateStatusLabel(candidate.display_status)} />
                <span className="tag mono">{candidate.candidate_id}</span>
                <span className="tag">修订 {candidate.revision}</span>
                <span className="tag">{candidate.symbol ?? "品种未记录"}</span>
                <span className="tag">{candidate.timeframe ?? "周期未记录"}</span>
                <span className="tag">{term(candidate.direction)}</span>
              </>
            }
          />

          {candidate.purpose === "pipeline_probe" ? (
            <Notice tone="caution" title="该候选仅用于验证流程链路，不构成策略结论">
              来源研究发现未通过研究门槛，因此该候选只能以流程探针的身份运行。它的验证结果证明的是
              rejection、成本建模、样本隔离与不可变报告链路有效，而不是任何市场或策略优势。按契约，该候选不得被判定为通过资格验证。
            </Notice>
          ) : null}

          {candidate.validation_report !== null ? (
            <Notice
              tone={
                candidate.validation_report.assessment === "supported" ? "neutral" : "caution"
              }
              title={`验证结论：${assessmentLabel(candidate.validation_report.assessment).text}`}
            >
              全部三个按时间划分的样本均已完成回测。验证结论由预声明标准判定，不在观察结果之后调整标准。
            </Notice>
          ) : (
            <Notice tone="neutral" title="该候选尚未产生验证报告">
              没有验证报告意味着无法判断该规则集在独立样本上的表现。
            </Notice>
          )}

          <div className="grid-two">
            <Section title="候选身份与来源证据">
              <KeyValues
                fields={[
                  {
                    label: "展示状态",
                    value: <Badge label={candidateStatusLabel(candidate.display_status)} />,
                    hint: "由用途、研究门槛、来源发现状态与验证结论共同派生",
                  },
                  {
                    label: "用途",
                    value: <Badge label={purposeLabel(candidate.purpose)} />,
                  },
                  {
                    label: "研究门槛",
                    value:
                      candidate.research_gate_passed === true ? (
                        <ToneBadge text="已通过" tone="positive" />
                      ) : (
                        <ToneBadge text="未通过" tone="negative" />
                      ),
                  },
                  {
                    label: "来源研究发现",
                    value: candidate.source_finding_id ? (
                      <span className="inline-actions">
                        <Link to={`/research/findings/${candidate.source_finding_id}`}>
                          <span className="mono">{candidate.source_finding_id}</span>
                        </Link>
                        <Badge label={findingStatusLabel(candidate.source_finding_status)} />
                      </span>
                    ) : (
                      "未记录"
                    ),
                  },
                  {
                    label: "来源证据 checksum",
                    value: <Mono>{candidate.source_evidence_sha256 ?? "未记录"}</Mono>,
                  },
                  { label: "artifact 路径", value: <Mono>{candidate.artifact_path}</Mono> },
                ]}
              />
            </Section>

            <Section title="执行规则" note="候选被冻结后不可修改">
              <KeyValues
                fields={[
                  { label: "方向", value: term(candidate.direction) },
                  { label: "持有 K 线数", value: formatInteger(candidate.holding_bars) },
                  {
                    label: "信号语义",
                    value: candidate.signal_semantics ?? "未记录",
                    hint: "信号在 K 线完全收盘后才计算",
                  },
                  { label: "成交时点", value: term(candidate.execution_timing) },
                  {
                    label: "仓位方法",
                    value: `${term(candidate.position_sizing.method)}（${formatNumber(
                      candidate.position_sizing.fraction,
                      2,
                    )}）`,
                    hint: "固定名义比例是研究抽象，不是经纪商手数",
                  },
                  {
                    label: "最大同时持仓",
                    value: formatInteger(candidate.risk_rules.maximum_concurrent_positions),
                  },
                  {
                    label: "止损 / 止盈",
                    value:
                      candidate.risk_rules.stop_loss_fraction === null &&
                      candidate.risk_rules.take_profit_fraction === null
                        ? "已禁用"
                        : `${formatNumber(candidate.risk_rules.stop_loss_fraction, 4)} / ${formatNumber(
                            candidate.risk_rules.take_profit_fraction,
                            4,
                          )}`,
                    hint: "K 线数据无法判定同一根 K 线内的触发先后顺序，因此初版禁用",
                  },
                ]}
              />
            </Section>
          </div>

          <Section title="入场事件">
            <EventDefinitionView definition={candidate.entry_event} />
          </Section>

          <Section title="建模假设" note="这些假设决定了结果的适用边界">
            <StringList items={candidate.assumptions} empty="未记录假设" />
          </Section>

          {candidate.validation_plan !== null ? (
            <Section title="验证计划" note="标准在验证前预声明">
              <KeyValues
                fields={[
                  {
                    label: "计划 ID",
                    value: <Mono>{candidate.validation_plan.plan_id ?? "未记录"}</Mono>,
                  },
                  {
                    label: "候选冻结",
                    value: formatBoolean(candidate.validation_plan.frozen_before_validation, "已冻结", "未冻结"),
                  },
                  {
                    label: "最小交易笔数",
                    value: formatInteger(
                      candidate.validation_plan.criteria.minimum_trades_per_evaluation_split,
                    ),
                  },
                  {
                    label: "要求正的均值收益",
                    value: formatBoolean(candidate.validation_plan.criteria.require_positive_mean_return),
                  },
                  {
                    label: "最大回撤上限",
                    value: formatPercent(candidate.validation_plan.criteria.maximum_drawdown_limit, 2),
                  },
                  {
                    label: "压力测试滑点",
                    value: `${formatNumber(
                      candidate.validation_plan.criteria.stress_slippage_bps_per_side,
                      2,
                    )} bp/边`,
                  },
                  {
                    label: "时段划分",
                    value: candidate.validation_plan.splits
                      .map(
                        (split) =>
                          `${splitRoleLabel(split.role).text} ${formatDate(split.start)}—${formatDate(
                            split.end,
                          )}`,
                      )
                      .join("；"),
                  },
                  {
                    label: "参考执行模型",
                    value: (
                      <Mono>
                        {Object.entries(candidate.validation_plan.primary_execution_model)
                          .map(([key, value]) => `${key}=${String(value)}`)
                          .join(", ") || "未记录"}
                      </Mono>
                    ),
                  },
                ]}
              />
            </Section>
          ) : null}

          {candidate.validation_report === null ? (
            <Section title="验证结果">
              <Empty>该候选目录下没有验证报告</Empty>
            </Section>
          ) : (
            <>
              <Section
                title="验证结果"
                note={`生成于 ${formatDateTime(candidate.validation_report.generated_at)}`}
              >
                <KeyValues
                  fields={[
                    {
                      label: "总体结论",
                      value: <Badge label={assessmentLabel(candidate.validation_report.assessment)} />,
                    },
                    {
                      label: "研究门槛",
                      value:
                        candidate.validation_report.research_gate_passed === true ? (
                          <ToneBadge text="已通过" tone="positive" />
                        ) : (
                          <ToneBadge
                            text="未通过"
                            tone="negative"
                            hint="研究门槛未通过时，本次运行只能是流程探针"
                          />
                        ),
                    },
                    {
                      label: "候选 checksum",
                      value: <Mono>{candidate.validation_report.candidate_sha256 ?? "未记录"}</Mono>,
                    },
                    {
                      label: "计划 checksum",
                      value: <Mono>{candidate.validation_report.plan_sha256 ?? "未记录"}</Mono>,
                    },
                    {
                      label: "数据集 checksum",
                      value: <Mono>{candidate.validation_report.dataset_sha256 ?? "未记录"}</Mono>,
                    },
                    { label: "报告路径", value: <Mono>{candidate.validation_report.artifact_path}</Mono> },
                  ]}
                />
                <div style={{ marginTop: 12 }}>
                  <SplitResultTable results={candidate.validation_report.split_results} />
                </div>
              </Section>

              <Notice tone="caution" title="验证报告的强制声明">
                <StringList items={candidate.validation_report.warnings} empty="未记录声明" />
              </Notice>
            </>
          )}

          <Section title="逐笔交易账本" note="表格 artifact 不在浏览器中展开">
            {candidate.trade_ledgers.length === 0 ? (
              <Empty>没有交易账本文件</Empty>
            ) : (
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr>
                      <th>文件</th>
                      <th className="numeric">大小</th>
                      <th>路径</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidate.trade_ledgers.map((ledger) => (
                      <tr key={ledger.name}>
                        <td>
                          <Mono>{ledger.name}</Mono>
                        </td>
                        <td className="numeric">{formatBytes(ledger.size_bytes)}</td>
                        <td className="mono text-faint">{ledger.path}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          {candidate.validation_manifest !== null ? (
            <Section
              title="验证 artifact 清单"
              actions={
                <button
                  className="action"
                  type="button"
                  onClick={() => setShowManifest((value) => !value)}
                >
                  {showManifest ? "收起" : "查看 JSON"}
                </button>
              }
            >
              <p className="text-muted">
                清单记录本次验证全部 artifact 的 SHA-256，可用于核对报告未被事后修改。
              </p>
              {showManifest ? <JsonViewer value={candidate.validation_manifest} /> : null}
            </Section>
          ) : null}
        </>
      )}
    </Resource>
  );
}

/**
 * 策略候选列表。
 *
 * 被拒绝与未通过验证的候选保持可见。展示状态由后端派生，同时列出判定依据
 * （purpose、研究门槛、来源发现状态、验证结论），避免只给结论不给理由。
 */

import { Link } from "react-router-dom";

import { useResource } from "../api/client";
import type { CandidateSummary } from "../api/types";
import { Badge, Notice, PageHeader, Resource, Section, ToneBadge } from "../components/primitives";
import {
  assessmentLabel,
  candidateStatusLabel,
  findingStatusLabel,
  formatDateTime,
  purposeLabel,
  term,
} from "../labels";

export function CandidateListPage() {
  const state = useResource<CandidateSummary[]>("/candidates");

  return (
    <>
      <PageHeader
        title="策略候选"
        subtitle="策略候选是被冻结的完整规则集，只用于历史验证。候选存在不代表它可以交易。"
      />
      <Notice tone="caution" title="策略候选不等于交易策略">
        <ul>
          <li>未通过研究门槛的发现只能派生"流程探针"，其验证结论在契约上不得判定为通过。</li>
          <li>被拒绝与未通过验证的候选保持可见：失败结果是判断哪些路径已被排除的依据。</li>
          <li>本界面不生成交易信号，也不下达任何订单。</li>
        </ul>
      </Notice>
      <Resource
        state={state}
        emptyWhen={(candidates) => candidates.length === 0}
        emptyText="尚未生成任何策略候选"
      >
        {(candidates) => (
          <Section title="候选清单" note={`${candidates.length} 项`}>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th className="wrap">策略候选</th>
                    <th>展示状态</th>
                    <th>用途</th>
                    <th>研究门槛</th>
                    <th>来源发现</th>
                    <th>验证结论</th>
                    <th>方向 / 持有</th>
                    <th>品种 / 周期</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((candidate) => (
                    <tr key={candidate.candidate_id}>
                      <td className="wrap">
                        <Link to={`/strategies/${candidate.candidate_id}`}>{candidate.title}</Link>
                        <div className="text-faint mono">
                          {candidate.candidate_id} · rev {candidate.revision}
                        </div>
                      </td>
                      <td>
                        <Badge label={candidateStatusLabel(candidate.display_status)} />
                      </td>
                      <td>
                        <Badge label={purposeLabel(candidate.purpose)} />
                      </td>
                      <td>
                        {candidate.research_gate_passed === true ? (
                          <ToneBadge text="已通过" tone="positive" />
                        ) : candidate.research_gate_passed === false ? (
                          <ToneBadge
                            text="未通过"
                            tone="negative"
                            hint="来源发现未达到研究门槛"
                          />
                        ) : (
                          <ToneBadge text="未记录" tone="unknown" />
                        )}
                      </td>
                      <td>
                        {candidate.source_finding_id ? (
                          <>
                            <Link to={`/research/findings/${candidate.source_finding_id}`}>
                              <span className="mono">{candidate.source_finding_id}</span>
                            </Link>
                            <div>
                              <Badge label={findingStatusLabel(candidate.source_finding_status)} />
                            </div>
                          </>
                        ) : (
                          "未记录"
                        )}
                      </td>
                      <td>
                        {candidate.validated ? (
                          <>
                            <Badge label={assessmentLabel(candidate.validation_assessment)} />
                            <div className="text-faint">
                              {formatDateTime(candidate.validated_at)}
                            </div>
                          </>
                        ) : (
                          <ToneBadge text="尚未验证" tone="neutral" />
                        )}
                      </td>
                      <td className="nowrap">
                        {term(candidate.direction)} / {candidate.holding_bars ?? "未记录"} 根
                      </td>
                      <td className="nowrap">
                        {candidate.symbol ?? "未记录"} / {candidate.timeframe ?? "未记录"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        )}
      </Resource>
    </>
  );
}

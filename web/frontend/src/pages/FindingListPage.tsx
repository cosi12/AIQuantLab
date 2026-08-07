/** 研究发现列表。被拒绝的发现同样列出，不做折叠或降权。 */

import { Link } from "react-router-dom";

import { useResource } from "../api/client";
import type { FindingSummary } from "../api/types";
import { Badge, Notice, PageHeader, Resource, Section } from "../components/primitives";
import { conclusionLabel, findingStatusLabel, formatDateTime } from "../labels";

export function FindingListPage() {
  const state = useResource<FindingSummary[]>("/findings");

  return (
    <>
      <PageHeader
        title="研究发现"
        subtitle="研究发现是经人工评审的市场行为 claim，绑定完整证据链、限制与显式非声明。一个发现可以派生多个独立的策略候选。"
      />
      <Notice tone="neutral" title="研究发现不是交易信号">
        发现回答"哪种市场行为具有统计证据"，不包含 position sizing、止损止盈或订单执行。把发现变成可执行规则需要独立的策略候选与验证。
      </Notice>
      <Resource
        state={state}
        emptyWhen={(findings) => findings.length === 0}
        emptyText="尚未发布任何研究发现"
      >
        {(findings) => (
          <Section title="已发布的研究发现" note={`${findings.length} 项`}>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th className="wrap">研究发现</th>
                    <th>状态</th>
                    <th>品种 / 周期</th>
                    <th>事件</th>
                    <th>来源实验</th>
                    <th>来源结论</th>
                    <th className="numeric">限制 / 非声明</th>
                    <th>评审时间</th>
                  </tr>
                </thead>
                <tbody>
                  {findings.map((finding) => (
                    <tr key={finding.finding_id}>
                      <td className="wrap">
                        <Link to={`/research/findings/${finding.finding_id}`}>{finding.title}</Link>
                        <div className="text-faint mono">{finding.finding_id}</div>
                      </td>
                      <td>
                        <Badge label={findingStatusLabel(finding.status)} />
                      </td>
                      <td className="nowrap">
                        {finding.symbol ?? "未记录"} / {finding.timeframe ?? "未记录"}
                      </td>
                      <td className="mono">{finding.event_name ?? "未记录"}</td>
                      <td>
                        {finding.source_experiment_id ? (
                          <Link to={`/research/${finding.source_experiment_id}`}>
                            <span className="mono">{finding.source_experiment_id}</span>
                          </Link>
                        ) : (
                          "未记录"
                        )}
                      </td>
                      <td>
                        <Badge label={conclusionLabel(finding.source_conclusion)} />
                      </td>
                      <td className="numeric">
                        {finding.limitation_count} / {finding.non_claim_count}
                      </td>
                      <td className="text-muted">{formatDateTime(finding.reviewed_at)}</td>
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

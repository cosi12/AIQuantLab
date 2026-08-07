/**
 * 研究发现详情。
 *
 * 限制与显式非声明必须与证据同页完整展示，不放入默认收起的折叠区域。
 */

import { Link, useParams } from "react-router-dom";

import { useResource } from "../api/client";
import type { FindingDetail } from "../api/types";
import { EventDefinitionView } from "../components/EventDefinitionView";
import {
  Badge,
  KeyValues,
  Mono,
  Notice,
  PageHeader,
  Resource,
  Section,
  StringList,
} from "../components/primitives";
import { conclusionLabel, findingStatusLabel, formatDateTime } from "../labels";

export function FindingDetailPage() {
  const { findingId = "" } = useParams();
  const state = useResource<FindingDetail>(`/findings/${encodeURIComponent(findingId)}`);

  return (
    <Resource state={state}>
      {(finding) => (
        <>
          <PageHeader
            breadcrumb={<Link to="/research/findings">研究发现</Link>}
            title={finding.title}
            meta={
              <>
                <Badge label={findingStatusLabel(finding.status)} />
                <span className="tag mono">{finding.finding_id}</span>
                <span className="tag">{finding.symbol ?? "品种未记录"}</span>
                <span className="tag">{finding.timeframe ?? "周期未记录"}</span>
              </>
            }
          />

          <Notice
            tone={finding.status === "rejected" ? "caution" : "neutral"}
            title={`评审状态：${findingStatusLabel(finding.status).text}`}
          >
            {finding.status === "rejected"
              ? "该发现的证据不支持其原始假设方向。记录被永久保留，以避免重复相同的研究路径。基于该发现的规则只能作为流程探针运行，不得进入资格验证。"
              : "该发现已被接受用于后续研究。这不代表任何派生策略已经通过验证。"}
          </Notice>

          <Section title="市场行为 claim">
            <p>{finding.market_behavior_claim ?? "未记录"}</p>
          </Section>

          <div className="grid-two">
            <Section title="证据摘要">
              <p>{finding.evidence_summary ?? "未记录"}</p>
            </Section>
            <Section title="经济解释">
              <p>{finding.economic_rationale ?? "未记录"}</p>
            </Section>
          </div>

          <Section title="适用事件">
            <EventDefinitionView definition={finding.applicable_event} />
          </Section>

          <Section title="证据链" note="全部 checksum 可与实验 artifact 逐项核对">
            <KeyValues
              fields={[
                {
                  label: "来源实验",
                  value: finding.source_evidence.experiment_id ? (
                    <Link to={`/research/${finding.source_evidence.experiment_id}`}>
                      <span className="mono">{finding.source_evidence.experiment_id}</span>
                    </Link>
                  ) : (
                    "未记录"
                  ),
                },
                { label: "实验修订", value: finding.source_evidence.revision ?? "未记录" },
                { label: "运行 ID", value: <Mono>{finding.source_evidence.run_id ?? "未记录"}</Mono> },
                {
                  label: "实验结论",
                  value: <Badge label={conclusionLabel(finding.source_evidence.conclusion)} />,
                },
                {
                  label: "配置指纹",
                  value: <Mono>{finding.source_evidence.config_sha256 ?? "未记录"}</Mono>,
                },
                {
                  label: "数据集 checksum",
                  value: <Mono>{finding.source_evidence.dataset_sha256 ?? "未记录"}</Mono>,
                },
                {
                  label: "统计报告 checksum",
                  value: <Mono>{finding.source_evidence.statistical_report_sha256 ?? "未记录"}</Mono>,
                },
                { label: "artifact 路径", value: <Mono>{finding.artifact_path}</Mono> },
                { label: "评审时间", value: formatDateTime(finding.reviewed_at) },
              ]}
            />
          </Section>

          <Section title="已知限制" note="必须与证据同屏阅读">
            <StringList items={finding.limitations} empty="未记录限制" />
          </Section>

          <Section title="显式非声明" note="这些是该发现明确不主张的内容">
            <StringList items={finding.explicit_non_claims} empty="未记录非声明" />
          </Section>

          <Section title="人工评审记录">
            <p>{finding.human_reviewer_notes ?? "未记录"}</p>
          </Section>

          <Section title="派生的策略候选">
            {finding.derived_candidate_ids.length === 0 ? (
              <p className="empty">该发现尚未派生任何策略候选</p>
            ) : (
              <span className="inline-actions">
                {finding.derived_candidate_ids.map((candidateId) => (
                  <Link key={candidateId} to={`/strategies/${candidateId}`}>
                    {candidateId}
                  </Link>
                ))}
              </span>
            )}
          </Section>
        </>
      )}
    </Resource>
  );
}

/**
 * 研究总览。
 *
 * 这是入口页，不承载数据集、实验或策略的完整功能。它只回答"这个研究系统现在有多大、
 * 最近发生了什么"，并且用 artifact 的原始状态呈现结果。
 */

import { Link } from "react-router-dom";

import { useResource } from "../api/client";
import type { LatestResult, Overview } from "../api/types";
import { Badge, KeyValues, Notice, PageHeader, Resource, Section, StatCard, Tally, ToneBadge } from "../components/primitives";
import {
  candidateStatusLabel,
  conclusionLabel,
  findingStatusLabel,
  formatDateTime,
  formatInteger,
  term,
} from "../labels";

function statusLabel(result: LatestResult) {
  if (result.kind === "finding") {
    return findingStatusLabel(result.status);
  }
  if (result.kind === "candidate") {
    return candidateStatusLabel(result.status);
  }
  return conclusionLabel(result.status);
}

export function DashboardPage() {
  const state = useResource<Overview>("/overview");

  return (
    <>
      <PageHeader
        title="AIQuantLab 研究总览"
        subtitle="研究优先、证据优先、先验证后部署。本界面只读取既有研究 artifact，不产生新的研究结论。"
      />
      <Resource state={state}>
        {(overview) => (
          <>
            <div className="stat-grid">
              <StatCard
                label="数据集"
                value={formatInteger(overview.counts.datasets)}
                note={`${overview.dataset_warning_total} 项质量警告`}
                to="/data"
              />
              <StatCard
                label="实验"
                value={formatInteger(overview.counts.experiments)}
                note={`${overview.counts.experiment_runs} 次运行`}
                to="/research"
              />
              <StatCard
                label="研究发现"
                value={formatInteger(overview.counts.findings)}
                note="含被拒绝的发现"
                to="/research/findings"
              />
              <StatCard
                label="策略候选"
                value={formatInteger(overview.counts.strategy_candidates)}
                note="候选不等于交易策略"
                to="/strategies"
              />
              <StatCard
                label="研究报告"
                value={formatInteger(overview.counts.reports)}
                note="Markdown 报告"
                to="/reports"
              />
            </div>

            <Notice tone="caution" title="研究诚实性声明">
              <ul>
                {overview.notices.map((notice) => (
                  <li key={notice}>{notice}</li>
                ))}
              </ul>
            </Notice>

            <div className="grid-two">
              <Section title="最新研究结果" note="按发生时间排序">
                {overview.latest_results.length === 0 ? (
                  <p className="empty">暂无研究结果</p>
                ) : (
                  <div className="table-scroll">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>类型</th>
                          <th className="wrap">名称</th>
                          <th>状态</th>
                          <th>时间</th>
                        </tr>
                      </thead>
                      <tbody>
                        {overview.latest_results.map((result) => (
                          <tr key={`${result.kind}-${result.identifier}`}>
                            <td>{term(result.kind)}</td>
                            <td className="wrap">
                              <Link to={result.link}>{result.title}</Link>
                              <div className="text-faint mono">{result.identifier}</div>
                            </td>
                            <td>
                              <Badge label={statusLabel(result)} />
                            </td>
                            <td className="text-muted">{formatDateTime(result.occurred_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Section>

              <Section title="状态分布" note="不折叠失败与不确定结论">
                <div className="stack">
                  <div>
                    <div className="stat-label">实验结论</div>
                    <Tally
                      items={overview.experiments_by_conclusion.map((item) => ({
                        label: conclusionLabel(item.label).text,
                        count: item.count,
                      }))}
                    />
                  </div>
                  <div>
                    <div className="stat-label">研究发现状态</div>
                    <Tally
                      items={overview.findings_by_status.map((item) => ({
                        label: findingStatusLabel(item.label).text,
                        count: item.count,
                      }))}
                    />
                  </div>
                  <div>
                    <div className="stat-label">策略候选状态</div>
                    <Tally
                      items={overview.candidates_by_display_status.map((item) => ({
                        label: candidateStatusLabel(item.label).text,
                        count: item.count,
                      }))}
                    />
                  </div>
                </div>
              </Section>
            </div>

            <Section title="最近实验" note="最多显示 5 条">
              {overview.recent_experiments.length === 0 ? (
                <p className="empty">暂无实验</p>
              ) : (
                <div className="table-scroll">
                  <table className="table">
                    <thead>
                      <tr>
                        <th className="wrap">实验</th>
                        <th>品种</th>
                        <th>周期</th>
                        <th>结论</th>
                        <th>运行次数</th>
                        <th>登记时间</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.recent_experiments.map((experiment) => (
                        <tr key={`${experiment.experiment_id}-${experiment.revision}`}>
                          <td className="wrap">
                            <Link to={`/research/${experiment.experiment_id}`}>
                              {experiment.title}
                            </Link>
                            <div className="text-faint mono">{experiment.experiment_id}</div>
                          </td>
                          <td>{experiment.symbol ?? "未记录"}</td>
                          <td>{experiment.timeframe ?? "未记录"}</td>
                          <td>
                            <Badge label={conclusionLabel(experiment.conclusion)} />
                          </td>
                          <td className="numeric">{experiment.run_count}</td>
                          <td className="text-muted">{formatDateTime(experiment.registered_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Section>

            <Section title="系统状态" note={`生成于 ${formatDateTime(overview.generated_at)}`}>
              <KeyValues
                fields={overview.system_checks.map((check) => ({
                  label: term(check.name),
                  value: (
                    <span className="inline-actions">
                      <ToneBadge
                        text={check.ok ? "正常" : "不可用"}
                        tone={check.ok ? "positive" : "negative"}
                      />
                      <span className="mono text-muted">{check.detail}</span>
                    </span>
                  ),
                }))}
              />
            </Section>
          </>
        )}
      </Resource>
    </>
  );
}

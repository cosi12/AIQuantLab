/** 数据质量报告汇总：把全部数据集的质量结论放在同一屏，便于横向核对。 */

import { Link } from "react-router-dom";

import { useResource } from "../api/client";
import type { QualityReportEntry } from "../api/types";
import { Badge, Notice, PageHeader, Resource, Section, ToneBadge } from "../components/primitives";
import { formatDateTime, formatInteger, qualityCodeLabel, severityLabel } from "../labels";

export function QualityReportsPage() {
  const state = useResource<QualityReportEntry[]>("/quality-reports");

  return (
    <>
      <PageHeader
        title="数据质量报告"
        subtitle="质量报告由数据管线在持久化时生成并写入 manifest。此处只做汇总展示，不重新计算任何指标。"
      />
      <Notice tone="neutral" title="质量结论的含义">
        <ul>
          <li>存在错误的数据集默认无法被持久化；错误出现在此处意味着 artifact 生成流程需要复核。</li>
          <li>警告不会被自动修复，也不会被静默忽略：缺失 K 线可能来自供应商交易时段，需要人工判断。</li>
          <li>特征数据集没有独立质量报告，其数据质量由来源 OHLCV 数据集决定。</li>
        </ul>
      </Notice>
      <Resource
        state={state}
        emptyWhen={(entries) => entries.length === 0}
        emptyText="没有可用的质量报告"
      >
        {(entries) => (
          <>
            <Section title="质量结论汇总" note={`${entries.length} 个数据集`}>
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr>
                      <th className="wrap">数据集</th>
                      <th>品种 / 周期</th>
                      <th>结论</th>
                      <th className="numeric">实际行数</th>
                      <th className="numeric">预期 K 线</th>
                      <th className="numeric">缺失 K 线</th>
                      <th className="numeric">错误</th>
                      <th className="numeric">警告</th>
                      <th>生成时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map((entry) => (
                      <tr key={entry.dataset_id}>
                        <td className="wrap">
                          <Link to={`/data/${entry.dataset_id}`}>{entry.dataset_id}</Link>
                        </td>
                        <td className="nowrap">
                          {entry.symbol ?? "未记录"} / {entry.timeframe ?? "未记录"}
                        </td>
                        <td>
                          {entry.quality_report.passed === true ? (
                            <ToneBadge text="通过" tone="positive" />
                          ) : entry.quality_report.passed === false ? (
                            <ToneBadge text="未通过" tone="negative" />
                          ) : (
                            <ToneBadge text="无报告" tone="unknown" />
                          )}
                        </td>
                        <td className="numeric">
                          {formatInteger(entry.quality_report.row_count ?? entry.row_count)}
                        </td>
                        <td className="numeric">
                          {formatInteger(entry.quality_report.expected_candle_count)}
                        </td>
                        <td className="numeric">
                          {formatInteger(entry.quality_report.missing_candle_count)}
                        </td>
                        <td className="numeric">{entry.quality_report.error_count}</td>
                        <td className="numeric">{entry.quality_report.warning_count}</td>
                        <td className="text-muted">
                          {formatDateTime(entry.quality_report.generated_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>

            {entries
              .filter((entry) => entry.quality_report.issues.length > 0)
              .map((entry) => (
                <Section
                  key={entry.dataset_id}
                  title={`问题明细：${entry.dataset_id}`}
                  note={`${entry.quality_report.issues.length} 类问题`}
                >
                  <div className="table-scroll">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>问题</th>
                          <th>严重程度</th>
                          <th className="numeric">数量</th>
                          <th className="wrap">说明</th>
                          <th className="wrap">样本时间戳</th>
                        </tr>
                      </thead>
                      <tbody>
                        {entry.quality_report.issues.map((issue) => (
                          <tr key={issue.code}>
                            <td>{qualityCodeLabel(issue.code)}</td>
                            <td>
                              <Badge label={severityLabel(issue.severity)} />
                            </td>
                            <td className="numeric">{formatInteger(issue.count)}</td>
                            <td className="wrap text-muted">{issue.message}</td>
                            <td className="wrap mono text-faint">
                              {issue.samples.length === 0 ? "未记录" : issue.samples.join("、")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Section>
              ))}
          </>
        )}
      </Resource>
    </>
  );
}

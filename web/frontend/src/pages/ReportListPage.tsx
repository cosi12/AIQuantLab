/** 研究报告列表。 */

import { Link } from "react-router-dom";

import { useResource } from "../api/client";
import type { ReportSummary } from "../api/types";
import { Mono, PageHeader, Resource, Section } from "../components/primitives";
import { formatBytes, formatDateTime } from "../labels";

export function ReportListPage() {
  const state = useResource<ReportSummary[]>("/reports");

  return (
    <>
      <PageHeader
        title="研究报告"
        subtitle="报告是研究过程的叙述性记录，与 artifact 中的结构化证据互补。报告在浏览器中只读展示，不可在此编辑或重新生成。"
      />
      <Resource
        state={state}
        emptyWhen={(reports) => reports.length === 0}
        emptyText="reports 目录下没有 Markdown 报告"
      >
        {(reports) => (
          <Section title="报告清单" note={`${reports.length} 篇`}>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th className="wrap">标题</th>
                    <th>文件</th>
                    <th className="numeric">大小</th>
                    <th>最后修改</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((report) => (
                    <tr key={report.report_id}>
                      <td className="wrap">
                        <Link to={`/reports/${report.report_id}`}>{report.title}</Link>
                      </td>
                      <td>
                        <Mono>{report.file_name}</Mono>
                      </td>
                      <td className="numeric">{formatBytes(report.size_bytes)}</td>
                      <td className="text-muted">{formatDateTime(report.modified_at)}</td>
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

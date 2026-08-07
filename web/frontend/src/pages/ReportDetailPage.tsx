/**
 * Markdown 报告查看器。
 *
 * 渲染信任本地 artifact 内容，前提是报告由本仓库脚本生成。一旦引入外部来源报告，
 * 必须加入 HTML 清洗层（见 docs/WEB_ARCHITECTURE.md 已知限制）。
 */

import { marked } from "marked";
import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";

import { useResource } from "../api/client";
import type { ReportDetail } from "../api/types";
import { Mono, PageHeader, Resource, Section } from "../components/primitives";
import { formatBytes, formatDateTime } from "../labels";

marked.setOptions({ gfm: true, breaks: false });

function MarkdownBody({ content }: { content: string }) {
  const html = useMemo(() => marked.parse(content) as string, [content]);
  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />;
}

export function ReportDetailPage() {
  const { reportId = "" } = useParams();
  const state = useResource<ReportDetail>(`/reports/${encodeURIComponent(reportId)}`);

  return (
    <Resource state={state}>
      {(report) => (
        <>
          <PageHeader
            breadcrumb={<Link to="/reports">研究报告</Link>}
            title={report.title}
            meta={
              <>
                <span className="tag">
                  <Mono>{report.path}</Mono>
                </span>
                <span className="tag">{formatBytes(report.size_bytes)}</span>
                <span className="tag">最后修改 {formatDateTime(report.modified_at)}</span>
              </>
            }
          />
          <Section title="报告内容" note="只读渲染">
            <MarkdownBody content={report.content} />
          </Section>
        </>
      )}
    </Resource>
  );
}

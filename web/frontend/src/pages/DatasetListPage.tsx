/** 数据集列表：回答"有哪些数据可用，它们的身份与质量状态是什么"。 */

import { Link } from "react-router-dom";

import { useResource } from "../api/client";
import type { DatasetSummary } from "../api/types";
import { Badge, Notice, PageHeader, Resource, Section, ToneBadge } from "../components/primitives";
import { datasetKindLabel, formatDate, formatInteger, shortHash } from "../labels";

function QualityCell({ dataset }: { dataset: DatasetSummary }) {
  if (dataset.error_count > 0) {
    return <ToneBadge text={`${dataset.error_count} 项错误`} tone="negative" />;
  }
  if (dataset.warning_count > 0) {
    return (
      <ToneBadge
        text={`${dataset.warning_count} 项警告`}
        tone="caution"
        hint="校验通过但存在需要人工确认的警告"
      />
    );
  }
  if (dataset.quality_passed === true) {
    return <ToneBadge text="校验通过" tone="positive" />;
  }
  return <ToneBadge text="无质量报告" tone="unknown" hint="该 manifest 未包含质量报告" />;
}

export function DatasetListPage() {
  const state = useResource<DatasetSummary[]>("/datasets");

  return (
    <>
      <PageHeader
        title="数据集浏览"
        subtitle="数据集来自 data/processed 下的 manifest sidecar。每个数据集都带有 checksum 与溯源信息；缺少这些信息的数据不可安全使用。"
      />
      <Notice tone="neutral">
        质量报告中的"警告"表示校验通过但存在需要人工确认的现象，例如缺失 K 线可能是供应商交易时段而非数据丢失。警告不会被隐藏，也不会被自动判定为无害。
      </Notice>
      <Resource
        state={state}
        emptyWhen={(datasets) => datasets.length === 0}
        emptyText="data/processed 下没有 manifest 文件"
      >
        {(datasets) => (
          <Section title="数据集" note={`${datasets.length} 个`}>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th className="wrap">数据集</th>
                    <th>类型</th>
                    <th>品种</th>
                    <th>周期</th>
                    <th>时间范围</th>
                    <th className="numeric">记录数</th>
                    <th>校验和</th>
                    <th>校验状态</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((dataset) => (
                    <tr key={dataset.dataset_id}>
                      <td className="wrap">
                        <Link to={`/data/${dataset.dataset_id}`}>{dataset.dataset_id}</Link>
                        <div className="text-faint">{dataset.source ?? "来源未记录"}</div>
                      </td>
                      <td>
                        <Badge label={datasetKindLabel(dataset.kind)} />
                      </td>
                      <td>{dataset.symbol ?? "未记录"}</td>
                      <td>{dataset.timeframe ?? "未记录"}</td>
                      <td>
                        {dataset.start === null && dataset.end === null ? (
                          "未记录"
                        ) : (
                          <span className="nowrap">
                            {formatDate(dataset.start)} — {formatDate(dataset.end)}
                          </span>
                        )}
                        {dataset.provenance_inherited ? (
                          <div className="text-faint">溯源继承自来源数据集</div>
                        ) : null}
                      </td>
                      <td className="numeric">{formatInteger(dataset.row_count)}</td>
                      <td className="mono" title={dataset.sha256 ?? undefined}>
                        {shortHash(dataset.sha256)}
                      </td>
                      <td>
                        <QualityCell dataset={dataset} />
                        {dataset.data_file_exists ? null : (
                          <div>
                            <ToneBadge text="数据文件缺失" tone="negative" />
                          </div>
                        )}
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

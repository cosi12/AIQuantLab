/**
 * 数据集详情：回答"这份数据从哪来"与"能不能信任它"。
 *
 * 版式顺序：身份 → 结论（质量与完整性）→ 证据（溯源、问题明细、预览）→ 限制。
 */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useLazyResource, useResource } from "../api/client";
import type { DatasetDetail, DatasetIntegrity, DatasetPreview } from "../api/types";
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
  datasetKindLabel,
  formatBytes,
  formatDateTime,
  formatInteger,
  qualityCodeLabel,
  severityLabel,
  term,
} from "../labels";

function IntegritySection({ datasetId }: { datasetId: string }) {
  const state = useLazyResource<DatasetIntegrity>(`/datasets/${datasetId}/integrity`);
  return (
    <Section
      title="完整性校验"
      actions={
        <button className="action" type="button" onClick={state.run} disabled={state.loading}>
          {state.loading ? "正在计算 SHA-256…" : "运行校验"}
        </button>
      }
    >
      <p className="text-muted">
        校验会重新计算整个 Parquet 文件的 SHA-256 并与 manifest 记录比对。这是有意的慢操作，因此不随页面自动执行。
      </p>
      {state.error !== null ? <p className="state error">{state.error}</p> : null}
      {state.data !== null ? (
        <KeyValues
          fields={[
            {
              label: "校验结果",
              value: state.data.matches ? (
                <ToneBadge text="校验和一致" tone="positive" />
              ) : (
                <ToneBadge text="校验和不一致" tone="negative" />
              ),
              hint: state.data.matches
                ? "文件内容与 manifest 记录一致"
                : "文件内容与 manifest 记录不一致，该数据集不可用于研究",
            },
            { label: "manifest 记录", value: <Mono>{state.data.expected_sha256 ?? "未记录"}</Mono> },
            { label: "实际计算", value: <Mono>{state.data.actual_sha256 ?? "无法计算"}</Mono> },
            { label: "文件大小", value: formatBytes(state.data.data_file_size_bytes) },
            { label: "校验时间", value: formatDateTime(state.data.checked_at) },
          ]}
        />
      ) : null}
    </Section>
  );
}

function PreviewSection({ datasetId }: { datasetId: string }) {
  const [position, setPosition] = useState<"head" | "tail">("head");
  const state = useResource<DatasetPreview>(
    `/datasets/${datasetId}/preview?position=${position}&limit=10`,
  );
  return (
    <Section
      title="数据预览"
      actions={
        <span className="inline-actions">
          <button
            className={`action${position === "head" ? " selected" : ""}`}
            type="button"
            onClick={() => setPosition("head")}
          >
            起始 10 行
          </button>
          <button
            className={`action${position === "tail" ? " selected" : ""}`}
            type="button"
            onClick={() => setPosition("tail")}
          >
            末尾 10 行
          </button>
        </span>
      }
    >
      <Resource state={state}>
        {(preview) => (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  {preview.columns.map((column) => (
                    <th key={column} className="numeric">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, index) => (
                  <tr key={index}>
                    {preview.columns.map((column) => (
                      <td key={column} className="numeric">
                        {formatCell(row[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Resource>
    </Section>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(5);
  }
  return String(value);
}

export function DatasetDetailPage() {
  const { datasetId = "" } = useParams();
  const state = useResource<DatasetDetail>(`/datasets/${encodeURIComponent(datasetId)}`);

  return (
    <Resource state={state}>
      {(dataset) => (
        <>
          <PageHeader
            breadcrumb={<Link to="/data">数据集浏览</Link>}
            title={dataset.dataset_id}
            subtitle={dataset.source ?? "来源未记录"}
            meta={
              <>
                <Badge label={datasetKindLabel(dataset.kind)} />
                <span className="tag">{dataset.symbol ?? "品种未记录"}</span>
                <span className="tag">{dataset.timeframe ?? "周期未记录"}</span>
                <span className="tag">{formatInteger(dataset.row_count)} 行</span>
              </>
            }
          />

          {dataset.error_count > 0 ? (
            <Notice tone="negative" title="该数据集存在质量错误">
              质量报告中包含 {dataset.error_count} 项错误。数据管线默认拒绝持久化含错误的数据，请核对该 artifact 的生成过程。
            </Notice>
          ) : null}
          {dataset.warning_count > 0 ? (
            <Notice tone="caution" title={`该数据集存在 ${dataset.warning_count} 类质量警告`}>
              警告表示校验通过但需要人工确认。在建立供应商特定的交易时段模型之前，缺失 K 线只能作为警告，不能直接判定为数据丢失。
            </Notice>
          ) : null}
          {dataset.provenance_inherited ? (
            <Notice tone="neutral" title="溯源信息为继承而来">
              这是特征数据集，本身不包含独立的采集溯源与质量报告。其品种、周期与时间范围继承自来源 OHLCV 数据集
              {dataset.source_dataset_id ? (
                <>
                  {" "}
                  <Link to={`/data/${dataset.source_dataset_id}`}>{dataset.source_dataset_id}</Link>
                </>
              ) : null}
              。
            </Notice>
          ) : null}

          <div className="grid-two">
            <Section title="数据身份">
              <KeyValues
                fields={[
                  { label: "数据文件", value: <Mono>{dataset.data_file}</Mono> },
                  { label: "manifest", value: <Mono>{dataset.manifest_path}</Mono> },
                  { label: "SHA-256", value: <Mono>{dataset.sha256 ?? "未记录"}</Mono> },
                  { label: "记录数", value: formatInteger(dataset.row_count) },
                  { label: "文件大小", value: formatBytes(dataset.data_file_size_bytes) },
                  {
                    label: "文件存在",
                    value: dataset.data_file_exists ? (
                      <ToneBadge text="是" tone="positive" />
                    ) : (
                      <ToneBadge text="否" tone="negative" />
                    ),
                  },
                  { label: "manifest schema", value: formatInteger(dataset.schema_version) },
                  { label: "生成时间", value: formatDateTime(dataset.created_at) },
                ]}
              />
            </Section>

            <Section title="数据溯源与解释方式" note="缺少这些信息的数据不可安全使用">
              <KeyValues
                fields={[
                  { label: "品种", value: dataset.provenance.symbol ?? dataset.symbol ?? "未记录" },
                  { label: "来源", value: dataset.provenance.source ?? dataset.source ?? "未记录" },
                  {
                    label: "时间周期",
                    value: dataset.provenance.timeframe ?? dataset.timeframe ?? "未记录",
                  },
                  {
                    label: "源时区 / 规范时区",
                    value: `${dataset.provenance.source_timezone ?? "未记录"} / ${
                      dataset.provenance.canonical_timezone ?? "未记录"
                    }`,
                  },
                  {
                    label: "时间戳约定",
                    value: term(dataset.provenance.timestamp_convention),
                    hint: "K 线时间戳代表哪一时刻",
                  },
                  {
                    label: "价格基准",
                    value: term(dataset.provenance.price_basis),
                    hint: "研究价格使用的报价口径",
                  },
                  {
                    label: "成交量类型",
                    value: term(dataset.provenance.volume_type),
                    hint: "报价跳动次数不得按实际成交量解释",
                  },
                  { label: "交易日历策略", value: term(dataset.provenance.calendar_policy) },
                ]}
              />
            </Section>
          </div>

          <Section title="处理说明" note="来自 manifest 的 notes 字段">
            <StringList items={dataset.provenance.notes} empty="未记录处理说明" />
          </Section>

          <Section
            title="质量报告"
            note={
              dataset.quality_report.generated_at
                ? `生成于 ${formatDateTime(dataset.quality_report.generated_at)}`
                : undefined
            }
          >
            {dataset.quality_report.passed === null &&
            dataset.quality_report.issues.length === 0 ? (
              <Empty>该 manifest 未包含质量报告</Empty>
            ) : (
              <>
                <KeyValues
                  fields={[
                    {
                      label: "校验结论",
                      value:
                        dataset.quality_report.passed === true ? (
                          <ToneBadge text="通过" tone="positive" />
                        ) : dataset.quality_report.passed === false ? (
                          <ToneBadge text="未通过" tone="negative" />
                        ) : (
                          <ToneBadge text="未记录" tone="unknown" />
                        ),
                      hint: "通过不代表没有警告",
                    },
                    {
                      label: "时间范围",
                      value: `${formatDateTime(dataset.quality_report.start)} — ${formatDateTime(
                        dataset.quality_report.end,
                      )}`,
                    },
                    {
                      label: "实际 / 预期 K 线数",
                      value: `${formatInteger(dataset.quality_report.row_count)} / ${formatInteger(
                        dataset.quality_report.expected_candle_count,
                      )}`,
                    },
                    {
                      label: "缺失 K 线数",
                      value: formatInteger(dataset.quality_report.missing_candle_count),
                      hint: "缺口被保留，不填充也不插值",
                    },
                  ]}
                />
                {dataset.quality_report.issues.length === 0 ? (
                  <p className="text-muted" style={{ marginTop: 12 }}>
                    未记录质量问题。
                  </p>
                ) : (
                  <div className="table-scroll" style={{ marginTop: 12 }}>
                    <table className="table">
                      <thead>
                        <tr>
                          <th>问题</th>
                          <th>严重程度</th>
                          <th className="numeric">数量</th>
                          <th className="wrap">说明</th>
                          <th className="wrap">样本</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dataset.quality_report.issues.map((issue) => (
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
                )}
              </>
            )}
          </Section>

          {dataset.feature_bundle !== null ? (
            <Section title="特征契约" note="lookback 与 leakage 说明来自 feature manifest">
              <KeyValues
                fields={[
                  { label: "bundle", value: <Mono>{dataset.feature_bundle.bundle_id ?? "未记录"}</Mono> },
                  { label: "bundle 修订", value: formatInteger(dataset.feature_bundle.revision) },
                  {
                    label: "bundle SHA-256",
                    value: <Mono>{dataset.feature_bundle_sha256 ?? "未记录"}</Mono>,
                  },
                  {
                    label: "来源 OHLCV SHA-256",
                    value: <Mono>{dataset.source_ohlcv_sha256 ?? "未记录"}</Mono>,
                  },
                  { label: "有效性列", value: <Mono>{dataset.validity_column ?? "未记录"}</Mono> },
                  { label: "warm-up K 线数", value: formatInteger(dataset.warm_up_bars) },
                  { label: "代码版本", value: <Mono>{dataset.code_version ?? "未记录"}</Mono> },
                ]}
              />
              <div className="table-scroll" style={{ marginTop: 12 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>特征</th>
                      <th>族</th>
                      <th>输入列</th>
                      <th className="numeric">lookback</th>
                      <th>使用当前 K 线</th>
                      <th className="wrap">经济含义</th>
                      <th className="wrap">泄漏说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dataset.feature_bundle.features.map((feature) => (
                      <tr key={feature.name}>
                        <td>
                          <Mono>{feature.name ?? "未记录"}</Mono>
                        </td>
                        <td>{feature.family ?? "未记录"}</td>
                        <td className="mono">{feature.input_columns.join(", ") || "未记录"}</td>
                        <td className="numeric">{formatInteger(feature.lookback_bars)}</td>
                        <td>{feature.uses_current_bar === true ? "是" : "否"}</td>
                        <td className="wrap text-muted">{feature.economic_meaning ?? "未记录"}</td>
                        <td className="wrap text-muted">{feature.leakage_notes ?? "未记录"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          ) : null}

          {dataset.columns.length > 0 ? (
            <Section title="列结构" note={`${dataset.columns.length} 列`}>
              <p className="mono">{dataset.columns.join(", ")}</p>
            </Section>
          ) : null}

          <IntegritySection datasetId={dataset.dataset_id} />

          {dataset.data_file_exists ? <PreviewSection datasetId={dataset.dataset_id} /> : null}

          <Section title="关联关系">
            <KeyValues
              fields={[
                {
                  label: "使用该数据集的实验",
                  value:
                    dataset.used_by_experiments.length === 0 ? (
                      <span className="text-faint">无</span>
                    ) : (
                      <span className="inline-actions">
                        {dataset.used_by_experiments.map((experimentId) => (
                          <Link key={experimentId} to={`/research/${experimentId}`}>
                            {experimentId}
                          </Link>
                        ))}
                      </span>
                    ),
                },
                {
                  label: "由该数据集派生的数据集",
                  value:
                    dataset.derived_dataset_ids.length === 0 ? (
                      <span className="text-faint">无</span>
                    ) : (
                      <span className="inline-actions">
                        {dataset.derived_dataset_ids.map((id) => (
                          <Link key={id} to={`/data/${id}`}>
                            {id}
                          </Link>
                        ))}
                      </span>
                    ),
                },
                {
                  label: "来源数据集",
                  value: dataset.source_dataset_id ? (
                    <Link to={`/data/${dataset.source_dataset_id}`}>
                      {dataset.source_dataset_id}
                    </Link>
                  ) : (
                    <span className="text-faint">无</span>
                  ),
                },
              ]}
            />
          </Section>
        </>
      )}
    </Resource>
  );
}

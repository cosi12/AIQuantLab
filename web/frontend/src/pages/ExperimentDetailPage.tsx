/**
 * 实验详情。
 *
 * 版式顺序：身份 → 结论 → 证据 → 限制。结论紧跟身份出现，研究者不必滚动完统计表格
 * 才看到"假设未被支持"。点估计一律与置信区间、q-value、样本量同屏展示。
 */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useResource } from "../api/client";
import type {
  ArtifactFile,
  DistributionSummary,
  ExperimentDetail,
  HorizonStatistics,
} from "../api/types";
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
  conclusionLabel,
  directionLabel,
  formatBytes,
  formatDateTime,
  formatInteger,
  formatInterval,
  formatNumber,
  formatPercent,
  runStatusLabel,
  shortHash,
  term,
} from "../labels";

const DISTRIBUTION_ROWS: { key: keyof HorizonStatistics; label: string; hint?: string }[] = [
  { key: "event_forward_return", label: "事件后收益" },
  { key: "baseline_forward_return", label: "无条件基准收益" },
  { key: "maximum_upside_return", label: "区间内最大上行幅度" },
  { key: "maximum_downside_return", label: "区间内最大下行幅度" },
  { key: "time_to_first_positive_bar", label: "首次正收益所需 K 线数" },
  { key: "time_to_first_negative_bar", label: "首次负收益所需 K 线数" },
];

const BAR_COUNT_KEYS = new Set(["time_to_first_positive_bar", "time_to_first_negative_bar"]);

function DistributionCell({
  value,
  asBarCount,
}: {
  value: number | null;
  asBarCount: boolean;
}) {
  if (value === null) {
    return <>未记录</>;
  }
  return <>{asBarCount ? formatNumber(value, 2) : formatPercent(value, 5)}</>;
}

function HorizonEvidence({ horizon }: { horizon: HorizonStatistics }) {
  return (
    <Section
      title={`Horizon：${formatInteger(horizon.horizon_bars)} 根 K 线`}
      note="Horizon 以 K 线数定义，不解释为交易入场、持仓或盈亏"
    >
      <KeyValues
        fields={[
          {
            label: "超额均值收益",
            value: formatPercent(horizon.excess_mean_return, 5),
            hint: "事件后均值收益减去无条件基准均值收益",
          },
          {
            label: "超额均值置信区间",
            value: (
              <span className="inline-actions">
                <Mono>{formatInterval(horizon.excess_mean_confidence_interval)}</Mono>
                {horizon.confidence_interval_includes_zero === true ? (
                  <ToneBadge
                    text="区间跨越 0"
                    tone="negative"
                    hint="无法排除超额收益为 0 的可能"
                  />
                ) : horizon.confidence_interval_includes_zero === false ? (
                  <ToneBadge text="区间不含 0" tone="neutral" />
                ) : null}
              </span>
            ),
          },
          {
            label: "Bootstrap p 值",
            value: formatNumber(horizon.bootstrap_p_value, 4),
          },
          {
            label: "多重检验调整后 q 值",
            value: (
              <span className="inline-actions">
                <Mono>{formatNumber(horizon.adjusted_q_value, 4)}</Mono>
                {horizon.passes_significance_threshold === true ? (
                  <ToneBadge text="低于阈值" tone="neutral" hint="统计显著不等于可交易" />
                ) : horizon.passes_significance_threshold === false ? (
                  <ToneBadge text="高于阈值" tone="negative" />
                ) : null}
              </span>
            ),
          },
          {
            label: "标准化效应量",
            value: formatNumber(horizon.standardized_effect, 5),
            hint: "效应量极小意味着即使显著也缺乏经济意义",
          },
          {
            label: "事件样本量",
            value: formatInteger(horizon.event_forward_return.count),
          },
          {
            label: "基准样本量",
            value: formatInteger(horizon.baseline_forward_return.count),
            hint: "默认基准包含事件观测本身",
          },
        ]}
      />

      <div className="table-scroll" style={{ marginTop: 12 }}>
        <table className="table">
          <thead>
            <tr>
              <th className="wrap">分布</th>
              <th className="numeric">样本量</th>
              <th className="numeric">均值</th>
              <th className="numeric">中位数</th>
              <th className="numeric">标准差</th>
              <th className="numeric">5% 分位</th>
              <th className="numeric">95% 分位</th>
              <th className="numeric">为正的比例</th>
            </tr>
          </thead>
          <tbody>
            {DISTRIBUTION_ROWS.map((row) => {
              const distribution = horizon[row.key] as DistributionSummary;
              const asBarCount = BAR_COUNT_KEYS.has(row.key as string);
              return (
                <tr key={row.key as string}>
                  <td className="wrap">{row.label}</td>
                  <td className="numeric">{formatInteger(distribution.count)}</td>
                  <td className="numeric">
                    <DistributionCell value={distribution.mean} asBarCount={asBarCount} />
                  </td>
                  <td className="numeric">
                    <DistributionCell value={distribution.median} asBarCount={asBarCount} />
                  </td>
                  <td className="numeric">
                    <DistributionCell
                      value={distribution.standard_deviation}
                      asBarCount={asBarCount}
                    />
                  </td>
                  <td className="numeric">
                    <DistributionCell value={distribution.quantile_05} asBarCount={asBarCount} />
                  </td>
                  <td className="numeric">
                    <DistributionCell value={distribution.quantile_95} asBarCount={asBarCount} />
                  </td>
                  <td className="numeric">
                    {asBarCount ? (
                      <span
                        className="text-faint"
                        title="该分布是根数计数，恒为非负，为正的比例没有解释意义"
                      >
                        不适用
                      </span>
                    ) : distribution.positive_probability === null ? (
                      "未记录"
                    ) : (
                      formatPercent(distribution.positive_probability, 2)
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {horizon.warnings.length > 0 ? (
        <Notice tone="caution" title="该 horizon 的统计警告">
          <StringList items={horizon.warnings} />
        </Notice>
      ) : null}
    </Section>
  );
}

function ArtifactBrowser({
  experimentId,
  runId,
}: {
  experimentId: string;
  runId: string;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const listState = useResource<ArtifactFile[]>(
    `/experiments/${encodeURIComponent(experimentId)}/runs/${encodeURIComponent(runId)}/artifacts`,
  );
  const contentState = useResource<Record<string, unknown>>(
    selected === null
      ? null
      : `/experiments/${encodeURIComponent(experimentId)}/runs/${encodeURIComponent(
          runId,
        )}/artifacts/${encodeURIComponent(selected)}`,
  );

  return (
    <Section title="运行 artifact" note={`run ${shortHash(runId, 10)}`}>
      <Resource state={listState} emptyWhen={(files) => files.length === 0} emptyText="没有 artifact">
        {(files) => (
          <>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th>文件</th>
                    <th className="numeric">大小</th>
                    <th>记录的 SHA-256</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((file) => (
                    <tr key={file.name}>
                      <td>
                        <Mono>{file.name}</Mono>
                      </td>
                      <td className="numeric">{formatBytes(file.size_bytes)}</td>
                      <td className="mono text-faint" title={file.recorded_sha256 ?? undefined}>
                        {shortHash(file.recorded_sha256, 16)}
                      </td>
                      <td>
                        {file.is_json ? (
                          <button
                            className={`action${selected === file.name ? " selected" : ""}`}
                            type="button"
                            onClick={() =>
                              setSelected((current) => (current === file.name ? null : file.name))
                            }
                          >
                            {selected === file.name ? "收起" : "查看"}
                          </button>
                        ) : (
                          <span className="text-faint">表格 artifact，不在浏览器中展开</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selected !== null ? (
              <div style={{ marginTop: 12 }}>
                <Resource state={contentState}>{(payload) => <JsonViewer value={payload} />}</Resource>
              </div>
            ) : null}
          </>
        )}
      </Resource>
    </Section>
  );
}

export function ExperimentDetailPage() {
  const { experimentId = "" } = useParams();
  const [runId, setRunId] = useState<string | null>(null);
  const query = runId === null ? "" : `?run_id=${encodeURIComponent(runId)}`;
  const state = useResource<ExperimentDetail>(
    `/experiments/${encodeURIComponent(experimentId)}${query}`,
  );

  return (
    <Resource state={state}>
      {(experiment) => (
        <>
          <PageHeader
            breadcrumb={<Link to="/research">实验浏览</Link>}
            title={experiment.title}
            subtitle={experiment.hypothesis_statement ?? undefined}
            meta={
              <>
                <Badge label={conclusionLabel(experiment.conclusion)} />
                <span className="tag mono">{experiment.experiment_id}</span>
                <span className="tag">修订 {experiment.revision}</span>
                <span className="tag">{experiment.symbol ?? "品种未记录"}</span>
                <span className="tag">{experiment.timeframe ?? "周期未记录"}</span>
                {experiment.tags.map((tag) => (
                  <span className="tag" key={tag}>
                    {tag}
                  </span>
                ))}
              </>
            }
          />

          <Notice
            tone={
              experiment.conclusion === "supported"
                ? "neutral"
                : experiment.conclusion === "not_reviewed"
                  ? "neutral"
                  : "caution"
            }
            title={`研究结论：${conclusionLabel(experiment.conclusion).text}`}
          >
            {experiment.conclusion_notes ?? "尚未记录人工结论说明。"}
          </Notice>

          {experiment.related_finding_ids.length > 0 ? (
            <Notice tone="neutral" title="由该实验发布的研究发现">
              <span className="inline-actions">
                {experiment.related_finding_ids.map((findingId) => (
                  <Link key={findingId} to={`/research/findings/${findingId}`}>
                    {findingId}
                  </Link>
                ))}
              </span>
            </Notice>
          ) : null}

          <Section title="研究问题" note="假设在运行前固定，且必须可证伪">
            {experiment.hypothesis === null ? (
              <Empty>该运行的 artifact 中没有假设记录</Empty>
            ) : (
              <>
                <KeyValues
                  fields={[
                    { label: "假设陈述", value: experiment.hypothesis.statement ?? "未记录" },
                    { label: "研究动机", value: experiment.hypothesis.rationale ?? "未记录" },
                    { label: "原假设", value: experiment.hypothesis.null_hypothesis ?? "未记录" },
                    {
                      label: "备择假设",
                      value: experiment.hypothesis.alternative_hypothesis ?? "未记录",
                    },
                    {
                      label: "预声明方向",
                      value: <Badge label={directionLabel(experiment.hypothesis.expected_direction)} />,
                      hint: "方向在观察结果之前确定，不允许事后调整",
                    },
                  ]}
                />
                <div style={{ marginTop: 12 }}>
                  <div className="stat-label">证伪标准</div>
                  <StringList items={experiment.hypothesis.falsification_criteria} />
                </div>
              </>
            )}
          </Section>

          <div className="grid-two">
            <Section title="数据集" note="实验固定 dataset checksum">
              {experiment.dataset === null ? (
                <Empty>未记录数据集引用</Empty>
              ) : (
                <KeyValues
                  fields={[
                    {
                      label: "数据集",
                      value: experiment.dataset.dataset_id ? (
                        <Link to={`/data/${experiment.dataset.dataset_id}`}>
                          {experiment.dataset.dataset_id}
                        </Link>
                      ) : (
                        <Mono>{experiment.dataset.path ?? "未记录"}</Mono>
                      ),
                    },
                    { label: "文件路径", value: <Mono>{experiment.dataset.path ?? "未记录"}</Mono> },
                    { label: "SHA-256", value: <Mono>{experiment.dataset.sha256 ?? "未记录"}</Mono> },
                    {
                      label: "样本窗口",
                      value: `${formatDateTime(experiment.dataset.sample_start)} — ${formatDateTime(
                        experiment.dataset.sample_end,
                      )}`,
                      hint: "窗口在运行前固定，不做有利区间搜索",
                    },
                  ]}
                />
              )}
              {experiment.feature_dataset !== null ? (
                <div style={{ marginTop: 12 }}>
                  <div className="stat-label">特征数据集完整性链</div>
                  <KeyValues
                    fields={[
                      {
                        label: "manifest",
                        value: <Mono>{experiment.feature_dataset.manifest_path ?? "未记录"}</Mono>,
                      },
                      {
                        label: "manifest SHA-256",
                        value: <Mono>{shortHash(experiment.feature_dataset.manifest_sha256, 24)}</Mono>,
                      },
                      {
                        label: "特征 bundle SHA-256",
                        value: (
                          <Mono>{shortHash(experiment.feature_dataset.feature_bundle_sha256, 24)}</Mono>
                        ),
                      },
                      {
                        label: "有效性列",
                        value: <Mono>{experiment.feature_dataset.validity_column ?? "未记录"}</Mono>,
                      },
                    ]}
                  />
                </div>
              ) : null}
            </Section>

            <Section title="统计设定" note="随机种子固定，结果可复现">
              {experiment.statistics === null ? (
                <Empty>未记录统计设定</Empty>
              ) : (
                <KeyValues
                  fields={[
                    {
                      label: "置信水平",
                      value:
                        experiment.statistics.confidence_level === null
                          ? "未记录"
                          : formatPercent(experiment.statistics.confidence_level, 0),
                    },
                    { label: "Bootstrap 方法", value: term(experiment.statistics.bootstrap_method) },
                    {
                      label: "Bootstrap 次数",
                      value: formatInteger(experiment.statistics.bootstrap_samples),
                    },
                    { label: "区块长度", value: formatInteger(experiment.statistics.block_size) },
                    { label: "随机种子", value: formatInteger(experiment.statistics.random_seed) },
                    {
                      label: "最小样本量",
                      value: formatInteger(experiment.statistics.minimum_sample_size),
                    },
                    {
                      label: "多重检验调整",
                      value: experiment.statistical_report?.multiple_testing_adjustment ?? "未记录",
                    },
                    {
                      label: "显著性阈值",
                      value:
                        experiment.statistical_report === null
                          ? "未记录"
                          : formatNumber(experiment.statistical_report.significance_threshold, 2),
                    },
                  ]}
                />
              )}
            </Section>
          </div>

          <Section title="事件定义" note="只允许当前值与非负历史滞后，防止引用未来数据">
            <EventDefinitionView definition={experiment.event_study?.event ?? null} />
          </Section>

          {experiment.event_study?.eligibility ? (
            <Section title="样本资格条件" note="决定哪些 K 线可以进入基准与事件样本">
              <EventDefinitionView definition={experiment.event_study.eligibility} />
            </Section>
          ) : null}

          <Section title="事件研究设定">
            {experiment.event_study === null ? (
              <Empty>未记录事件研究设定</Empty>
            ) : (
              <KeyValues
                fields={[
                  {
                    label: "Forward horizon",
                    value:
                      experiment.event_study.horizons_bars.length === 0
                        ? "未记录"
                        : `${experiment.event_study.horizons_bars.join(" / ")} 根 K 线`,
                    hint: "以 K 线数计量，不等于持仓时间",
                  },
                  { label: "价格列", value: <Mono>{experiment.event_study.price_column ?? "未记录"}</Mono> },
                  {
                    label: "高低价列",
                    value: (
                      <Mono>
                        {experiment.event_study.high_column ?? "未记录"} /{" "}
                        {experiment.event_study.low_column ?? "未记录"}
                      </Mono>
                    ),
                  },
                  { label: "收益类型", value: term(experiment.event_study.return_type) },
                  {
                    label: "重叠策略",
                    value: term(experiment.event_study.overlap_policy),
                    hint: "不重叠采样减少同一段行情被重复计入",
                  },
                ]}
              />
            )}
          </Section>

          {experiment.statistical_report === null ? (
            <Section title="统计证据">
              <Empty>该运行没有可读的统计报告</Empty>
            </Section>
          ) : (
            <>
              <Notice tone="caution" title="统计报告的整体限制">
                <StringList items={experiment.statistical_report.warnings} empty="未记录整体限制" />
              </Notice>
              {experiment.statistical_report.horizons.map((horizon) => (
                <HorizonEvidence key={horizon.horizon_bars} horizon={horizon} />
              ))}
            </>
          )}

          <Section title="可复现性链" note="配置、数据、代码与 artifact 的 checksum">
            {experiment.run_integrity === null ? (
              <Empty>未记录运行清单</Empty>
            ) : (
              <>
                <KeyValues
                  fields={[
                    { label: "运行 ID", value: <Mono>{experiment.run_integrity.run_id ?? "未记录"}</Mono> },
                    {
                      label: "配置指纹",
                      value: <Mono>{experiment.run_integrity.config_sha256 ?? "未记录"}</Mono>,
                    },
                    {
                      label: "数据集 checksum",
                      value: <Mono>{experiment.run_integrity.dataset_sha256 ?? "未记录"}</Mono>,
                    },
                    {
                      label: "数据帧 checksum",
                      value: <Mono>{experiment.run_integrity.frame_sha256 ?? "未记录"}</Mono>,
                    },
                    {
                      label: "代码版本",
                      value: <Mono>{experiment.run_integrity.code_version ?? "未记录"}</Mono>,
                    },
                    {
                      label: "原始事件数",
                      value: formatInteger(experiment.run_integrity.raw_event_count),
                    },
                    {
                      label: "选中事件数",
                      value: formatInteger(experiment.run_integrity.selected_event_count),
                      hint: "应用重叠策略后实际进入统计的事件数",
                    },
                    {
                      label: "合格观测数",
                      value: formatInteger(experiment.run_integrity.eligible_observation_count),
                    },
                    {
                      label: "配置 schema 版本",
                      value: formatInteger(experiment.config_schema_version),
                    },
                    { label: "registry 文件", value: <Mono>{experiment.registry_path}</Mono> },
                  ]}
                />
              </>
            )}
          </Section>

          <Section title="运行记录" note={`${experiment.run_count} 次运行`}>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th>运行 ID</th>
                    <th>状态</th>
                    <th>开始</th>
                    <th>结束</th>
                    <th>代码版本</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {experiment.runs.map((run) => {
                    const isCurrent = run.run_id === experiment.evidence_run_id;
                    return (
                      <tr key={run.run_id}>
                        <td className="mono" title={run.run_id}>
                          {shortHash(run.run_id, 12)}
                          {isCurrent ? (
                            <div>
                              <span className="tag">当前展示的证据</span>
                            </div>
                          ) : null}
                        </td>
                        <td>
                          <Badge label={runStatusLabel(run.status)} />
                          {run.error ? <div className="text-faint">{run.error}</div> : null}
                        </td>
                        <td className="text-muted nowrap">{formatDateTime(run.started_at)}</td>
                        <td className="text-muted nowrap">{formatDateTime(run.completed_at)}</td>
                        <td className="mono text-faint" title={run.code_version ?? undefined}>
                          {shortHash(run.code_version, 20)}
                        </td>
                        <td>
                          {run.artifacts_available ? (
                            <button
                              className={`action${isCurrent ? " selected" : ""}`}
                              type="button"
                              onClick={() => setRunId(run.run_id)}
                              disabled={isCurrent}
                            >
                              {isCurrent ? "已选中" : "查看该运行"}
                            </button>
                          ) : (
                            <span className="text-faint">artifact 目录不可用</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Section>

          {experiment.evidence_run_id !== null ? (
            <ArtifactBrowser
              experimentId={experiment.experiment_id}
              runId={experiment.evidence_run_id}
            />
          ) : null}
        </>
      )}
    </Resource>
  );
}

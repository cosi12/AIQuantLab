/**
 * 实验列表。
 *
 * 按登记时间排序，不按结论好坏排序，也不折叠失败或不确定的实验。
 */

import { Link } from "react-router-dom";

import { useResource } from "../api/client";
import type { ExperimentSummary } from "../api/types";
import { Badge, Notice, PageHeader, Resource, Section } from "../components/primitives";
import { conclusionLabel, formatDateTime, runStatusLabel } from "../labels";

export function ExperimentListPage() {
  const state = useResource<ExperimentSummary[]>("/experiments");

  return (
    <>
      <PageHeader
        title="实验浏览"
        subtitle="实验来自 experiments 目录下的 registry。registry 把运行状态与研究结论分离：框架不会因为运行成功就认定假设成立。"
      />
      <Notice tone="neutral" title="结论由人工评审给出">
        运行状态回答"实验是否执行完成"，研究结论回答"证据是否支持假设"。两者互相独立，未评审的实验会显式标记为未评审。
      </Notice>
      <Resource
        state={state}
        emptyWhen={(experiments) => experiments.length === 0}
        emptyText="experiments 目录下没有 registry 记录"
      >
        {(experiments) => (
          <Section title="实验" note={`${experiments.length} 项`}>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th className="wrap">实验</th>
                    <th className="wrap">研究假设</th>
                    <th>品种 / 周期</th>
                    <th>Horizon</th>
                    <th>运行状态</th>
                    <th>研究结论</th>
                    <th>登记时间</th>
                  </tr>
                </thead>
                <tbody>
                  {experiments.map((experiment) => (
                    <tr key={`${experiment.experiment_id}-${experiment.revision}`}>
                      <td className="wrap">
                        <Link to={`/research/${experiment.experiment_id}`}>{experiment.title}</Link>
                        <div className="text-faint mono">
                          {experiment.experiment_id} · rev {experiment.revision}
                        </div>
                        <div className="text-faint">registry：{experiment.registry_name}</div>
                      </td>
                      <td className="wrap text-muted">
                        {experiment.hypothesis_statement ?? "未记录"}
                      </td>
                      <td className="nowrap">
                        {experiment.symbol ?? "未记录"} / {experiment.timeframe ?? "未记录"}
                      </td>
                      <td className="numeric">
                        {experiment.horizons_bars.length === 0
                          ? "未记录"
                          : `${experiment.horizons_bars.join(" / ")} 根`}
                      </td>
                      <td>
                        <Badge label={runStatusLabel(experiment.latest_run_status)} />
                        <div className="text-faint">
                          {experiment.completed_run_count}/{experiment.run_count} 次完成
                          {experiment.failed_run_count > 0
                            ? `，${experiment.failed_run_count} 次失败`
                            : ""}
                        </div>
                      </td>
                      <td>
                        <Badge label={conclusionLabel(experiment.conclusion)} />
                      </td>
                      <td className="text-muted">{formatDateTime(experiment.registered_at)}</td>
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

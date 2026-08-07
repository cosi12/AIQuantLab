/** 设置：展示后端运行环境与 artifact 根目录。当前没有可写配置项。 */

import { useResource } from "../api/client";
import type { Health } from "../api/types";
import { KeyValues, Mono, Notice, PageHeader, Resource, Section, ToneBadge } from "../components/primitives";
import { term } from "../labels";

export function SettingsPage() {
  const state = useResource<Health>("/health");

  return (
    <>
      <PageHeader
        title="设置"
        subtitle="Web 层是无状态只读服务，唯一的运行期配置是 artifact 根目录位置。"
      />
      <Notice tone="neutral" title="没有可在界面中修改的配置">
        artifact 根目录通过环境变量 <code>AIQUANTLAB_ROOT</code> 指定；未设置时后端会向上查找包含
        <code>pyproject.toml</code> 的目录。修改配置需要重启后端进程。
      </Notice>
      <Resource state={state}>
        {(health) => (
          <>
            <Section title="服务信息">
              <KeyValues
                fields={[
                  { label: "服务状态", value: <ToneBadge text="正常" tone="positive" /> },
                  { label: "后端版本", value: <Mono>{health.version}</Mono> },
                  { label: "仓库根目录", value: <Mono>{health.repository_root}</Mono> },
                  {
                    label: "写入端点",
                    value: <ToneBadge text="不存在" tone="neutral" />,
                    hint: "这是架构约束，不是暂缺功能",
                  },
                ]}
              />
            </Section>
            <Section title="artifact 根目录" note="Web 层只能读取这些目录">
              <KeyValues
                fields={Object.entries(health.roots).map(([name, description]) => ({
                  label: term(name),
                  value: (
                    <span className="inline-actions">
                      <ToneBadge
                        text={description.exists ? "存在" : "缺失"}
                        tone={description.exists ? "positive" : "negative"}
                      />
                      <Mono>{description.path}</Mono>
                    </span>
                  ),
                }))}
              />
            </Section>
            <Section title="研究操作在哪里执行">
              <p className="text-muted">
                运行实验、发布研究发现、生成策略候选与执行验证都通过仓库中的 <code>scripts/</code> 完成。
                Web 层有意不提供这些操作：研究结论必须由人工在可复现的脚本流程中登记，而不是在界面上点击产生。
              </p>
            </Section>
          </>
        )}
      </Resource>
    </>
  );
}

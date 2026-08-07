/**
 * 事件定义展示。
 *
 * 明确展示 lag：event condition 只允许当前值和非负历史 lag，展示 lag 让研究者
 * 能直接核对事件识别没有引用未来数据。
 */

import type { EventCondition, EventDefinition } from "../api/types";
import { term } from "../labels";
import { Empty, KeyValues, Mono } from "./primitives";

function describeTarget(condition: EventCondition): string {
  if (condition.right_column !== null) {
    const lag = condition.right_lag_bars ?? 0;
    return lag > 0 ? `${condition.right_column}（滞后 ${lag} 根）` : condition.right_column;
  }
  if (condition.value === null || condition.value === undefined) {
    return "未记录";
  }
  if (typeof condition.value === "boolean") {
    return condition.value ? "true" : "false";
  }
  return String(condition.value);
}

export function EventDefinitionView({
  definition,
  emptyText = "未记录事件定义",
}: {
  definition: EventDefinition | null;
  emptyText?: string;
}) {
  if (definition === null) {
    return <Empty>{emptyText}</Empty>;
  }
  return (
    <>
      <KeyValues
        fields={[
          { label: "事件名称", value: <Mono>{definition.name ?? "未记录"}</Mono> },
          { label: "事件说明", value: definition.description ?? "未记录" },
          { label: "条件组合方式", value: term(definition.combination) },
        ]}
      />
      {definition.conditions.length === 0 ? (
        <Empty>未记录条件</Empty>
      ) : (
        <div className="table-scroll" style={{ marginTop: 12 }}>
          <table className="table">
            <thead>
              <tr>
                <th>左侧列</th>
                <th>左侧滞后</th>
                <th>比较</th>
                <th>右侧目标</th>
              </tr>
            </thead>
            <tbody>
              {definition.conditions.map((condition, index) => (
                <tr key={`${condition.left_column}-${index}`}>
                  <td>
                    <Mono>{condition.left_column ?? "未记录"}</Mono>
                  </td>
                  <td className="numeric">{condition.left_lag_bars ?? 0}</td>
                  <td>{term(condition.operator)}</td>
                  <td>
                    <Mono>{describeTarget(condition)}</Mono>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

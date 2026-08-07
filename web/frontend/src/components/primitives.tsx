/** 通用只读展示组件。这些组件不含业务判定逻辑，只负责排版。 */

import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import type { LabelSpec, Tone } from "../labels";

export function PageHeader({
  title,
  subtitle,
  meta,
  breadcrumb,
}: {
  title: string;
  subtitle?: ReactNode;
  meta?: ReactNode;
  breadcrumb?: ReactNode;
}) {
  return (
    <header className="page-header">
      {breadcrumb ? <div className="breadcrumb">{breadcrumb}</div> : null}
      <h1>{title}</h1>
      {subtitle ? <p className="page-subtitle">{subtitle}</p> : null}
      {meta ? <div className="page-header-meta">{meta}</div> : null}
    </header>
  );
}

export function Section({
  title,
  note,
  actions,
  children,
}: {
  title: string;
  note?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2>{title}</h2>
        {actions ?? (note ? <span className="section-note">{note}</span> : null)}
      </div>
      <div className="section-body">{children}</div>
    </section>
  );
}

export function Badge({ label }: { label: LabelSpec }) {
  return (
    <span className={`badge ${label.tone}`} title={label.hint ?? undefined}>
      {label.text}
    </span>
  );
}

export function ToneBadge({ text, tone, hint }: { text: string; tone: Tone; hint?: string }) {
  return (
    <span className={`badge ${tone}`} title={hint}>
      {text}
    </span>
  );
}

export interface Field {
  label: string;
  value: ReactNode;
  hint?: string;
}

export function KeyValues({ fields }: { fields: Field[] }) {
  return (
    <dl className="kv">
      {fields.map((field) => (
        <ItemPair key={field.label} field={field} />
      ))}
    </dl>
  );
}

function ItemPair({ field }: { field: Field }) {
  return (
    <>
      <dt>{field.label}</dt>
      <dd>
        {field.value}
        {field.hint ? <span className="kv-hint">{field.hint}</span> : null}
      </dd>
    </>
  );
}

export function Mono({ children }: { children: ReactNode }) {
  return <span className="mono">{children}</span>;
}

export function Notice({
  tone = "neutral",
  title,
  children,
}: {
  tone?: "neutral" | "caution" | "negative";
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className={`notice ${tone}`}>
      {title ? <div className="notice-title">{title}</div> : null}
      {children}
    </div>
  );
}

export function StringList({ items, empty = "未记录" }: { items: string[]; empty?: string }) {
  if (items.length === 0) {
    return <p className="empty">{empty}</p>;
  }
  return (
    <ul className="plain-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function Tally({ items }: { items: { label: string; count: number }[] }) {
  if (items.length === 0) {
    return <p className="empty">暂无数据</p>;
  }
  return (
    <div className="tally">
      {items.map((item) => (
        <div className="tally-item" key={item.label}>
          <span>{item.label}</span>
          <span className="tally-count">{item.count}</span>
        </div>
      ))}
    </div>
  );
}

export function StatCard({
  label,
  value,
  note,
  to,
}: {
  label: string;
  value: ReactNode;
  note?: string;
  to?: string;
}) {
  const body = (
    <>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {note ? <div className="stat-note">{note}</div> : null}
    </>
  );
  if (to) {
    return (
      <Link className="stat clickable" to={to} style={{ color: "inherit" }}>
        {body}
      </Link>
    );
  }
  return <div className="stat">{body}</div>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}

export function Loading({ children = "正在读取 artifact…" }: { children?: ReactNode }) {
  return <div className="state">{children}</div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state error">
      <p>{message}</p>
      {onRetry ? (
        <button className="action" type="button" onClick={onRetry}>
          重新加载
        </button>
      ) : null}
    </div>
  );
}

/** 统一处理加载态、错误态与空数据态，避免各页面重复实现。 */
export function Resource<T>({
  state,
  children,
  emptyWhen,
  emptyText = "暂无 artifact",
}: {
  state: { data: T | null; loading: boolean; error: string | null; reload: () => void };
  children: (data: T) => ReactNode;
  emptyWhen?: (data: T) => boolean;
  emptyText?: string;
}) {
  if (state.loading) {
    return <Loading />;
  }
  if (state.error !== null) {
    return <ErrorState message={state.error} onRetry={state.reload} />;
  }
  if (state.data === null) {
    return <Empty>暂无数据</Empty>;
  }
  if (emptyWhen && emptyWhen(state.data)) {
    return <Empty>{emptyText}</Empty>;
  }
  return <>{children(state.data)}</>;
}

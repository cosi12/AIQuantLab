/** 应用外壳：侧边导航 + 内容区。导航结构对应 docs/WEB_ARCHITECTURE.md 第 7 节。 */

import { NavLink, Outlet } from "react-router-dom";

interface NavigationItem {
  to: string;
  text: string;
  end?: boolean;
}

interface NavigationGroup {
  title: string;
  items: NavigationItem[];
}

const NAVIGATION: NavigationGroup[] = [
  {
    title: "总览",
    items: [{ to: "/", text: "研究总览", end: true }],
  },
  {
    title: "数据",
    items: [
      { to: "/data", text: "数据集浏览", end: true },
      { to: "/data/quality", text: "数据质量报告" },
    ],
  },
  {
    title: "研究",
    items: [
      { to: "/research", text: "实验浏览", end: true },
      { to: "/research/findings", text: "研究发现" },
      { to: "/reports", text: "研究报告" },
    ],
  },
  {
    title: "策略",
    items: [{ to: "/strategies", text: "策略候选", end: true }],
  },
  {
    title: "未来能力",
    items: [
      { to: "/agent", text: "AI 研究助手" },
      { to: "/execution", text: "执行层" },
    ],
  },
  {
    title: "系统",
    items: [{ to: "/settings", text: "设置" }],
  },
];

export function Layout() {
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="sidebar-brand">
          <strong>AIQuantLab</strong>
          <span>量化研究实验室界面</span>
        </div>
        {NAVIGATION.map((group) => (
          <div className="sidebar-group" key={group.title}>
            <div className="sidebar-group-title">{group.title}</div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
              >
                {item.text}
              </NavLink>
            ))}
          </div>
        ))}
        <div className="sidebar-footer">
          只读研究界面
          <br />
          不生成信号，不执行交易
        </div>
      </nav>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

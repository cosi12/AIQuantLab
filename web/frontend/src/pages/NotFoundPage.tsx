import { Link } from "react-router-dom";

import { Notice, PageHeader } from "../components/primitives";

export function NotFoundPage() {
  return (
    <>
      <PageHeader title="页面不存在" subtitle="请求的路径不在当前应用的路由表中。" />
      <Notice tone="neutral">
        返回 <Link to="/">研究总览</Link>，或从左侧导航选择功能模块。
      </Notice>
    </>
  );
}

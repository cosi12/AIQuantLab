/** 路由表。页面职责见 docs/WEB_ARCHITECTURE.md 第 7 节。 */

import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { CandidateDetailPage } from "./pages/CandidateDetailPage";
import { CandidateListPage } from "./pages/CandidateListPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DatasetDetailPage } from "./pages/DatasetDetailPage";
import { DatasetListPage } from "./pages/DatasetListPage";
import { ExperimentDetailPage } from "./pages/ExperimentDetailPage";
import { ExperimentListPage } from "./pages/ExperimentListPage";
import { FindingDetailPage } from "./pages/FindingDetailPage";
import { FindingListPage } from "./pages/FindingListPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { AgentPlaceholderPage, ExecutionPlaceholderPage } from "./pages/PlaceholderPages";
import { QualityReportsPage } from "./pages/QualityReportsPage";
import { ReportDetailPage } from "./pages/ReportDetailPage";
import { ReportListPage } from "./pages/ReportListPage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />

        <Route path="data" element={<DatasetListPage />} />
        <Route path="data/quality" element={<QualityReportsPage />} />
        <Route path="data/:datasetId" element={<DatasetDetailPage />} />

        <Route path="research" element={<ExperimentListPage />} />
        <Route path="research/findings" element={<FindingListPage />} />
        <Route path="research/findings/:findingId" element={<FindingDetailPage />} />
        <Route path="research/:experimentId" element={<ExperimentDetailPage />} />

        <Route path="strategies" element={<CandidateListPage />} />
        <Route path="strategies/:candidateId" element={<CandidateDetailPage />} />

        <Route path="reports" element={<ReportListPage />} />
        <Route path="reports/:reportId" element={<ReportDetailPage />} />

        <Route path="agent" element={<AgentPlaceholderPage />} />
        <Route path="execution" element={<ExecutionPlaceholderPage />} />
        <Route path="settings" element={<SettingsPage />} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

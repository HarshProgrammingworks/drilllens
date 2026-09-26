import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { RoleGuard } from "./auth/RoleGuard";
import { AppLayout } from "./layouts/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { AdminWellsPage, AuditPage, SystemAdminPage, ThresholdPage, UsersAdminPage } from "./pages/AdminPages";
import { AlertsPage, ComparisonPage, EvidencePage, ReportsDashboardPage, ReportDetailPage, ReportsPage, ReviewPage, RiskPage, SettingsPage, UploadPage } from "./pages/KnowledgePages";
import { DashboardPage, LivePage, MapPage, NearbyPage, WellDetailPage, WellsPage } from "./pages/OperationsPages";

function Shell({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute><AppLayout>{children}</AppLayout></ProtectedRoute>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<Shell><DashboardPage /></Shell>} />
      <Route path="/live-monitoring" element={<Shell><LivePage /></Shell>} />
      <Route path="/wells" element={<Shell><WellsPage /></Shell>} />
      <Route path="/wells/:id" element={<Shell><WellDetailPage /></Shell>} />
      <Route path="/nearby-wells" element={<Shell><NearbyPage /></Shell>} />
      <Route path="/reports" element={<Shell><ReportsPage /></Shell>} />
      <Route path="/reports/upload" element={<Shell><RoleGuard allow={["ADMIN", "DRILLING_ENGINEER"]}><UploadPage /></RoleGuard></Shell>} />
      <Route path="/reports/:id" element={<Shell><ReportDetailPage /></Shell>} />
      <Route path="/well-comparison" element={<Shell><ComparisonPage /></Shell>} />
      <Route path="/risk" element={<Shell><RiskPage /></Shell>} />
      <Route path="/alerts" element={<Shell><AlertsPage /></Shell>} />
      <Route path="/alerts/:id" element={<Shell><AlertsPage /></Shell>} />
      <Route path="/evidence" element={<Shell><EvidencePage /></Shell>} />
      <Route path="/evidence/:id" element={<Shell><EvidencePage /></Shell>} />
      <Route path="/map" element={<Shell><MapPage /></Shell>} />
      <Route path="/engineering-review" element={<Shell><ReviewPage /></Shell>} />
      <Route path="/reports-dashboard" element={<Shell><ReportsDashboardPage /></Shell>} />
      <Route path="/settings" element={<Shell><SettingsPage /></Shell>} />
      <Route path="/admin/users" element={<Shell><RoleGuard allow={["ADMIN"]}><UsersAdminPage /></RoleGuard></Shell>} />
      <Route path="/admin/wells" element={<Shell><RoleGuard allow={["ADMIN"]}><AdminWellsPage /></RoleGuard></Shell>} />
      <Route path="/admin/risk-thresholds" element={<Shell><RoleGuard allow={["ADMIN"]}><ThresholdPage /></RoleGuard></Shell>} />
      <Route path="/admin/audit-logs" element={<Shell><RoleGuard allow={["ADMIN", "DRILLING_ENGINEER"]}><AuditPage /></RoleGuard></Shell>} />
      <Route path="/admin/system" element={<Shell><RoleGuard allow={["ADMIN"]}><SystemAdminPage /></RoleGuard></Shell>} />
      <Route path="*" element={<Shell><div className="panel p-4">This page is not part of DrillLens.</div></Shell>} />
    </Routes>
  );
}

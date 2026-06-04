import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import SubmitJobPage from "./pages/SubmitJobPage";
import BackendsPage from "./pages/BackendsPage";
import JobsPage from "./pages/JobsPage";
import ResultPage from "./pages/ResultPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/submit" element={<SubmitJobPage />} />
        <Route path="/backends" element={<BackendsPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/results" element={<JobsPage />} />
        <Route path="/results/:jobId" element={<ResultPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

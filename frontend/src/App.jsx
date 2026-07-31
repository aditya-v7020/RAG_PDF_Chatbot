import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Route>
    </Routes>
  );
}

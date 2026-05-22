import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage    from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import ReviewPage   from "@/pages/ReviewPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login"             element={<LoginPage />} />
        <Route path="/dashboard"         element={<DashboardPage />} />
        <Route path="/revisao/:documentoId" element={<ReviewPage />} />
        <Route path="*"                  element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

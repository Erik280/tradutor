import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        {/* Futuras rotas protegidas serão adicionadas aqui */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

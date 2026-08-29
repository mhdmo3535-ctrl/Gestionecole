import { Spin } from "antd";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { utilisateur, pret } = useAuth();

  if (!pret) {
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100vh" }}>
        <Spin size="large" />
      </div>
    );
  }
  if (!utilisateur) {
    return <Navigate to="/connexion" replace />;
  }
  return <>{children}</>;
}

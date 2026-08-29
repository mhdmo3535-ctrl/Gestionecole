import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppLayout } from "./layout/AppLayout";
import { ElevesPage } from "./pages/ElevesPage";
import { LoginPage } from "./pages/LoginPage";
import { StubPage } from "./pages/StubPage";

export const router = createBrowserRouter([
  { path: "/connexion", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/eleves" replace /> },
      { path: "eleves", element: <ElevesPage /> },
      { path: "classes", element: <StubPage titre="Classes" /> },
      { path: "matieres", element: <StubPage titre="Matières" /> },
      { path: "enseignants", element: <StubPage titre="Enseignants" /> },
      { path: "notes", element: <StubPage titre="Saisie des notes" /> },
      { path: "bulletins", element: <StubPage titre="Bulletins" /> },
    ],
  },
  { path: "*", element: <Navigate to="/eleves" replace /> },
]);

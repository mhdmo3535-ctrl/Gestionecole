import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppLayout } from "./layout/AppLayout";
import { ClassesPage } from "./pages/ClassesPage";
import { ClasseDetailPage } from "./pages/classes/ClasseDetailPage";
import { BulletinsPage } from "./pages/BulletinsPage";
import { ElevesPage } from "./pages/ElevesPage";
import { EleveDossierPage } from "./pages/eleves/EleveDossierPage";
import { EnseignantsPage } from "./pages/EnseignantsPage";
import { EnseignantDetailPage } from "./pages/enseignants/EnseignantDetailPage";
import { LoginPage } from "./pages/LoginPage";
import { MatieresPage } from "./pages/MatieresPage";
import { MatiereDetailPage } from "./pages/matieres/MatiereDetailPage";
import { PaiementsPage } from "./pages/PaiementsPage";
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
      { path: "eleves/:id", element: <EleveDossierPage /> },
      { path: "classes", element: <ClassesPage /> },
      { path: "classes/:id", element: <ClasseDetailPage /> },
      { path: "matieres", element: <MatieresPage /> },
      { path: "matieres/:id", element: <MatiereDetailPage /> },
      { path: "enseignants", element: <EnseignantsPage /> },
      { path: "enseignants/:id", element: <EnseignantDetailPage /> },
      { path: "notes", element: <StubPage titre="Saisie des notes" /> },
      { path: "bulletins", element: <BulletinsPage /> },
      { path: "paiements", element: <PaiementsPage /> },
    ],
  },
  { path: "*", element: <Navigate to="/eleves" replace /> },
]);

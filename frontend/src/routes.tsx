import { createBrowserRouter, Navigate } from "react-router-dom";
import { Accueil } from "./auth/Accueil";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppLayout } from "./layout/AppLayout";
import { ClassesPage } from "./pages/ClassesPage";
import { ClasseDetailPage } from "./pages/classes/ClasseDetailPage";
import { AutorisationsPage } from "./pages/AutorisationsPage";
import { BulletinsPage } from "./pages/BulletinsPage";
import { ElevesPage } from "./pages/ElevesPage";
import { EmploiDuTempsPage } from "./pages/EmploiDuTempsPage";
import { EleveDossierPage } from "./pages/eleves/EleveDossierPage";
import { LoginPage } from "./pages/LoginPage";
import { MatieresPage } from "./pages/MatieresPage";
import { MatiereDetailPage } from "./pages/matieres/MatiereDetailPage";
import { PaiementsPage } from "./pages/PaiementsPage";
import { PersonnelPage } from "./pages/PersonnelPage";
import { PersonnelDetailPage } from "./pages/personnel/PersonnelDetailPage";
import { StubPage } from "./pages/StubPage";
import { TableauDeBordPage } from "./pages/TableauDeBordPage";

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
      { index: true, element: <Accueil /> },
      { path: "tableau-de-bord", element: <TableauDeBordPage /> },
      { path: "eleves", element: <ElevesPage /> },
      { path: "eleves/:id", element: <EleveDossierPage /> },
      { path: "classes", element: <ClassesPage /> },
      { path: "classes/:id", element: <ClasseDetailPage /> },
      { path: "emploi-du-temps", element: <EmploiDuTempsPage /> },
      { path: "matieres", element: <MatieresPage /> },
      { path: "matieres/:id", element: <MatiereDetailPage /> },
      { path: "personnel", element: <PersonnelPage /> },
      { path: "personnel/:id", element: <PersonnelDetailPage /> },
      { path: "enseignants", element: <PersonnelPage enseignantsSeulement /> },
      { path: "notes", element: <StubPage titre="Saisie des notes" /> },
      { path: "autorisations", element: <AutorisationsPage /> },
      { path: "bulletins", element: <BulletinsPage /> },
      { path: "paiements", element: <PaiementsPage /> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);

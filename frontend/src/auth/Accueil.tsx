import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

const ADMINISTRATIFS = ["directeur", "censeur", "surveillant", "comptable", "secretaire"];

/** Page d'arrivée : le tableau de bord pour l'administration, la liste des élèves sinon. */
export function Accueil() {
  const { utilisateur } = useAuth();
  const admin = utilisateur?.roles.some((r) => ADMINISTRATIFS.includes(r));
  return <Navigate to={admin ? "/tableau-de-bord" : "/eleves"} replace />;
}

import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { getDroits } from "../api/endpoints";
import type { Domaine, Role } from "../api/types";
import { useAuth } from "./AuthContext";

const ROLES_ADMINISTRATIFS: Role[] = ["directeur", "censeur", "surveillant", "comptable", "secretaire"];

/** Rôles du personnel, dans l'ordre d'affichage. */
export const ROLES_PERSONNEL: Role[] = [
  "directeur",
  "censeur",
  "surveillant",
  "comptable",
  "secretaire",
  "enseignant",
];

export const LIBELLES_ROLES: Record<Role, string> = {
  directeur: "Directeur",
  censeur: "Censeur",
  surveillant: "Surveillant général",
  comptable: "Comptable / DAF",
  secretaire: "Secrétaire",
  enseignant: "Enseignant",
  parent: "Parent",
  eleve: "Élève",
};

export const COULEURS_ROLES: Record<Role, string> = {
  directeur: "gold",
  censeur: "blue",
  surveillant: "purple",
  comptable: "cyan",
  secretaire: "magenta",
  enseignant: "green",
  parent: "default",
  eleve: "default",
};

export function libellesRoles(roles: Role[]): string {
  return ROLES_PERSONNEL.filter((r) => roles.includes(r))
    .map((r) => LIBELLES_ROLES[r])
    .join(" · ");
}

/**
 * Droits de l'utilisateur connecté. La matrice vient de l'API (/auth/droits),
 * seule source de vérité : l'interface n'affiche que ce que l'API autorise.
 * Tant qu'elle n'est pas chargée, tout est refusé.
 */
export function useDroits() {
  const { utilisateur } = useAuth();
  const droitsQuery = useQuery({
    queryKey: ["droits"],
    queryFn: getDroits,
    staleTime: Infinity,
    enabled: !!utilisateur,
  });
  const matrice = droitsQuery.data;
  const roles = useMemo(() => utilisateur?.roles ?? [], [utilisateur]);

  const peut = useCallback(
    (domaine: Domaine, ecrire = false) => {
      if (!matrice) return false;
      const autorises = matrice[domaine][ecrire ? "ecrire" : "lire"];
      return roles.some((r) => autorises.includes(r));
    },
    [matrice, roles],
  );

  return {
    peut,
    estEnseignant: roles.includes("enseignant"),
    estAdministratif: roles.some((r) => ROLES_ADMINISTRATIFS.includes(r)),
    pret: !!matrice,
  };
}

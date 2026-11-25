import {
  BookOutlined,
  CalendarOutlined,
  DashboardOutlined,
  FileDoneOutlined,
  IdcardOutlined,
  ProfileOutlined,
  ReadOutlined,
  SolutionOutlined,
  TeamOutlined,
  WalletOutlined,
} from "@ant-design/icons";
import type { MenuProps } from "antd";
import type { ReactNode } from "react";
import type { Role } from "../api/types";

/**
 * Menus par métier.
 *
 * Chaque rôle a un menu organisé autour de son travail, pas une copie
 * filtrée de celui du directeur. Un compte qui cumule plusieurs rôles reçoit
 * la réunion de leurs menus (rubriques fusionnées, entrées sans doublon).
 * Le directeur a le menu complet.
 *
 * Le menu n'est qu'un raccourci : les droits réels sont vérifiés par l'API.
 */

interface Entree {
  cle: string;
  libelle: string;
  icone: ReactNode;
}

interface Rubrique {
  titre?: string; // sans titre : en tête du menu
  entrees: Entree[];
}

const tableauDeBord: Entree = {
  cle: "/tableau-de-bord",
  libelle: "Tableau de bord",
  icone: <DashboardOutlined />,
};
const eleves: Entree = { cle: "/eleves", libelle: "Élèves", icone: <IdcardOutlined /> };
const classes: Entree = { cle: "/classes", libelle: "Classes", icone: <TeamOutlined /> };
const emploiDuTemps: Entree = {
  cle: "/emploi-du-temps",
  libelle: "Emploi du temps",
  icone: <CalendarOutlined />,
};
const bulletins: Entree = { cle: "/bulletins", libelle: "Bulletins", icone: <ProfileOutlined /> };
const matieres: Entree = {
  cle: "/matieres",
  libelle: "Matières",
  icone: <BookOutlined />,
};
const enseignants: Entree = {
  cle: "/enseignants",
  libelle: "Enseignants",
  icone: <SolutionOutlined />,
};
const personnel: Entree = { cle: "/personnel", libelle: "Personnel", icone: <SolutionOutlined /> };
const autorisations: Entree = {
  cle: "/autorisations",
  libelle: "Autorisations",
  icone: <FileDoneOutlined />,
};
const paiements: Entree = { cle: "/paiements", libelle: "Paiements", icone: <WalletOutlined /> };

const MENUS: Record<Exclude<Role, "parent" | "eleve">, Rubrique[]> = {
  directeur: [
    { entrees: [tableauDeBord, eleves] },
    { titre: "Vie scolaire", entrees: [autorisations] },
    { titre: "Pédagogie", entrees: [emploiDuTemps, bulletins] },
    { titre: "Organisation", entrees: [classes, matieres] },
    { titre: "Finances", entrees: [paiements] },
    { titre: "Administration", entrees: [personnel] },
  ],
  censeur: [
    { entrees: [tableauDeBord] },
    { titre: "Pédagogie", entrees: [emploiDuTemps, bulletins] },
    { titre: "Organisation", entrees: [classes, matieres, enseignants] },
    { titre: "Consultation", entrees: [eleves] },
  ],
  surveillant: [
    { entrees: [tableauDeBord] },
    { titre: "Vie scolaire", entrees: [autorisations, eleves] },
    { titre: "Consultation", entrees: [emploiDuTemps, classes] },
  ],
  comptable: [
    { entrees: [tableauDeBord] },
    { titre: "Finances", entrees: [paiements] },
    { titre: "Consultation", entrees: [eleves] },
  ],
  secretaire: [
    { entrees: [tableauDeBord] },
    { titre: "Scolarité", entrees: [eleves, { ...paiements, libelle: "Frais de scolarité" }] },
    { titre: "Consultation", entrees: [classes, emploiDuTemps] },
  ],
  enseignant: [
    {
      titre: "Mon espace",
      entrees: [
        { ...emploiDuTemps, libelle: "Mon emploi du temps" },
        { cle: "/notes", libelle: "Saisie des notes", icone: <ReadOutlined /> },
      ],
    },
    { titre: "Consultation", entrees: [classes, eleves] },
  ],
};

const ORDRE: Array<keyof typeof MENUS> = [
  "directeur",
  "censeur",
  "surveillant",
  "comptable",
  "secretaire",
  "enseignant",
];

/** Rubriques du menu pour un compte (un ou plusieurs rôles). */
export function rubriquesPour(roles: Role[]): Rubrique[] {
  const mesRoles = roles.includes("directeur")
    ? (["directeur"] as const)
    : ORDRE.filter((r) => roles.includes(r));
  const fusion: Rubrique[] = [];
  const vues = new Set<string>();
  for (const role of mesRoles) {
    for (const rubrique of MENUS[role]) {
      const nouvelles = rubrique.entrees.filter((e) => !vues.has(e.cle));
      nouvelles.forEach((e) => vues.add(e.cle));
      if (!nouvelles.length) continue;
      const existante = fusion.find((r) => r.titre === rubrique.titre);
      if (existante) existante.entrees.push(...nouvelles);
      else fusion.push({ titre: rubrique.titre, entrees: [...nouvelles] });
    }
  }
  return fusion;
}

/** Les rubriques au format du composant Menu d'Ant Design. */
type ItemMenu = NonNullable<MenuProps["items"]>[number];

export function itemsDuMenu(rubriques: Rubrique[]): ItemMenu[] {
  return rubriques.flatMap((r): ItemMenu[] => {
    const items: ItemMenu[] = r.entrees.map((e) => ({
      key: e.cle,
      icon: e.icone,
      label: e.libelle,
    }));
    return r.titre
      ? [{ type: "group" as const, key: r.titre, label: r.titre, children: items }]
      : items;
  });
}

import type { ModePaiement, StatutPaiementEleve } from "../../api/types";

const nf = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

/** 150000 → « 150 000 FCFA » (espace normale, plus lisible à l'impression). */
export function fcfa(montant: number): string {
  return `${nf.format(montant).replace(/\s/g, " ")} FCFA`;
}

export const MODES: Record<ModePaiement, string> = {
  especes: "Espèces",
  mobile_money: "Mobile Money",
  virement: "Virement",
  cheque: "Chèque",
};

export const STATUT: Record<StatutPaiementEleve, { texte: string; couleur: string }> = {
  solde: { texte: "Soldé", couleur: "green" },
  partiel: { texte: "Partiel", couleur: "blue" },
  non_paye: { texte: "Non payé", couleur: "default" },
  en_retard: { texte: "En retard", couleur: "red" },
  aucune_tranche: { texte: "Aucune tranche", couleur: "default" },
};

// ---------- Montant en toutes lettres (reçus) ----------

const UNITES = [
  "zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
  "onze", "douze", "treize", "quatorze", "quinze", "seize",
];
const DIZAINES = ["", "dix", "vingt", "trente", "quarante", "cinquante", "soixante"];

function moinsDeCent(n: number): string {
  if (n <= 16) return UNITES[n];
  if (n < 20) return `dix-${UNITES[n - 10]}`;
  const d = Math.floor(n / 10);
  const u = n % 10;
  if (d === 7 || d === 9) {
    // 70-79 = soixante-dix…, 90-99 = quatre-vingt-dix…
    const base = d === 7 ? "soixante" : "quatre-vingt";
    if (d === 7 && u === 1) return "soixante et onze";
    return `${base}-${moinsDeCent(10 + u)}`;
  }
  if (d === 8) return u === 0 ? "quatre-vingts" : `quatre-vingt-${UNITES[u]}`;
  if (u === 0) return DIZAINES[d];
  if (u === 1) return `${DIZAINES[d]} et un`;
  return `${DIZAINES[d]}-${UNITES[u]}`;
}

function moinsDeMille(n: number, finale: boolean): string {
  const c = Math.floor(n / 100);
  const reste = n % 100;
  let txt = "";
  if (c === 1) txt = "cent";
  else if (c > 1) txt = `${UNITES[c]} cent${reste === 0 && finale ? "s" : ""}`;
  if (reste > 0) {
    let r = moinsDeCent(reste);
    // « quatre-vingts » perd son s s'il est suivi de « mille »
    if (!finale && r === "quatre-vingts") r = "quatre-vingt";
    txt = txt ? `${txt} ${r}` : r;
  }
  return txt;
}

/** 165250 → « cent soixante-cinq mille deux cent cinquante ». */
export function enLettres(montant: number): string {
  let n = Math.round(Math.abs(montant));
  if (n === 0) return "zéro";
  const parties: string[] = [];
  const milliards = Math.floor(n / 1e9);
  n %= 1e9;
  const millions = Math.floor(n / 1e6);
  n %= 1e6;
  const milliers = Math.floor(n / 1000);
  const unites = n % 1000;
  if (milliards) parties.push(`${moinsDeMille(milliards, true)} milliard${milliards > 1 ? "s" : ""}`);
  if (millions) parties.push(`${moinsDeMille(millions, true)} million${millions > 1 ? "s" : ""}`);
  if (milliers) parties.push(milliers === 1 ? "mille" : `${moinsDeMille(milliers, false)} mille`);
  if (unites) parties.push(moinsDeMille(unites, true));
  return parties.join(" ");
}

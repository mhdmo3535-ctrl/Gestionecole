import type { Jour } from "../../api/types";

export const JOURS: Array<{ numero: Jour; nom: string }> = [
  { numero: 1, nom: "Lundi" },
  { numero: 2, nom: "Mardi" },
  { numero: 3, nom: "Mercredi" },
  { numero: 4, nom: "Jeudi" },
  { numero: 5, nom: "Vendredi" },
  { numero: 6, nom: "Samedi" },
];

/** "07:30:00" → minutes depuis minuit */
export const enMinutes = (h: string) => {
  const [hh, mm] = h.split(":").map(Number);
  return hh * 60 + mm;
};
/** 450 → « 7h30 », 480 → « 8h » */
export const formatHeure = (minutes: number) => {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h}h${String(m).padStart(2, "0")}` : `${h}h`;
};
/** 90 → « 1 h 30 », 120 → « 2 h » */
export const formatDuree = (minutes: number) => {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (!h) return `${m} min`;
  return m ? `${h} h ${String(m).padStart(2, "0")}` : `${h} h`;
};

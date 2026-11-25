import { PlusOutlined } from "@ant-design/icons";
import { theme } from "antd";
import { useState, type CSSProperties } from "react";
import type { Creneau, Jour } from "../../api/types";
import { enMinutes, formatHeure, JOURS } from "./temps";

/** Plage affichée au minimum : 7h–13h. Elle s'élargit pour contenir tous les cours. */
const DEBUT_MIN = 7 * 60;
const FIN_MIN = 13 * 60;

interface Props {
  creneaux: Creneau[];
  /** Sous la matière : le professeur (vue classe) ou la classe (vue professeur). */
  sousTitre: (c: Creneau) => string;
  onCours?: (c: Creneau) => void;
  /** Case vide cliquée : jour et horaire de la tranche. */
  onCaseVide?: (jour: Jour, debut: number, fin: number) => void;
}

/**
 * Emploi du temps présenté comme le tableau papier affiché en classe :
 * une ligne par tranche horaire, une colonne par jour, un cours par case
 * (fusionnée sur plusieurs lignes s'il dure plus d'une tranche).
 *
 * Les durées étant libres, les tranches sont découpées sur les heures de
 * début et de fin de tous les cours affichés.
 */
export function TableauEdt({ creneaux, sousTitre, onCours, onCaseVide }: Props) {
  const { token } = theme.useToken();
  const [survol, setSurvol] = useState<string | null>(null);

  // une ligne par heure pleine, plus une coupure à chaque début / fin de cours hors heure pleine
  const bornesCours = creneaux.flatMap((c) => [enMinutes(c.heure_debut), enMinutes(c.heure_fin)]);
  const premiere = Math.min(DEBUT_MIN, ...bornesCours.map((m) => Math.floor(m / 60) * 60));
  const derniere = Math.max(FIN_MIN, ...bornesCours.map((m) => Math.ceil(m / 60) * 60));
  const heuresPleines = Array.from(
    { length: (derniere - premiere) / 60 + 1 },
    (_, i) => premiere + i * 60,
  );
  const reperes = [...new Set([...heuresPleines, ...bornesCours])].sort((a, b) => a - b);
  const tranches = reperes.slice(0, -1).map((debut, i) => ({ debut, fin: reperes[i + 1] }));

  // cours qui commence à la tranche i, pour chaque jour ; et tranches couvertes par un cours
  const debutDe = new Map<string, { cours: Creneau; lignes: number }>();
  const couvert = new Set<string>();
  creneaux.forEach((c) => {
    const i = tranches.findIndex((t) => t.debut === enMinutes(c.heure_debut));
    const j = tranches.findIndex((t) => t.fin === enMinutes(c.heure_fin));
    if (i < 0 || j < i) return;
    debutDe.set(`${c.jour}-${i}`, { cours: c, lignes: j - i + 1 });
    for (let k = i + 1; k <= j; k++) couvert.add(`${c.jour}-${k}`);
  });

  const bord = `1px solid ${token.colorBorderSecondary}`;
  const cellule: CSSProperties = { border: bord, padding: "6px 8px", verticalAlign: "top" };

  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          minWidth: 820,
          borderCollapse: "collapse",
          tableLayout: "fixed",
          fontSize: 13,
        }}
      >
        <colgroup>
          <col style={{ width: 104 }} />
          {JOURS.map((j) => (
            <col key={j.numero} />
          ))}
        </colgroup>
        <thead>
          <tr>
            <th style={{ ...cellule, background: token.colorFillTertiary, textAlign: "left" }}>
              Horaire
            </th>
            {JOURS.map((j) => (
              <th
                key={j.numero}
                style={{ ...cellule, background: token.colorFillTertiary, textAlign: "center" }}
              >
                {j.nom}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tranches.map((t, i) => {
            // lignes proportionnelles à la durée : 44 px pour une heure, 30 px au minimum
            const hauteur = Math.max(30, Math.round(((t.fin - t.debut) / 60) * 44));
            return (
              <tr key={t.debut} style={{ height: hauteur }}>
                <td
                  style={{
                    ...cellule,
                    whiteSpace: "nowrap",
                    color: token.colorTextSecondary,
                    fontVariantNumeric: "tabular-nums",
                    verticalAlign: "middle",
                  }}
                >
                  {formatHeure(t.debut)} – {formatHeure(t.fin)}
                </td>
                {JOURS.map((jr) => {
                  const cle = `${jr.numero}-${i}`;
                  if (couvert.has(cle)) return null;
                  const d = debutDe.get(cle);
                  if (d) {
                    const c = d.cours;
                    return (
                      <td
                        key={cle}
                        rowSpan={d.lignes}
                        onClick={() => onCours?.(c)}
                        onMouseEnter={() => setSurvol(cle)}
                        onMouseLeave={() => setSurvol(null)}
                        title={onCours ? "Modifier ce cours" : undefined}
                        style={{
                          ...cellule,
                          background:
                            survol === cle && onCours
                              ? token.colorPrimaryBgHover
                              : token.colorPrimaryBg,
                          cursor: onCours ? "pointer" : "default",
                          verticalAlign: "middle",
                          textAlign: "center",
                        }}
                      >
                        <div style={{ fontWeight: 600, color: token.colorText }}>
                          {c.matiere_nom}
                        </div>
                        <div style={{ color: token.colorTextSecondary }}>{sousTitre(c)}</div>
                        {d.lignes > 1 && (
                          <div
                            style={{ color: token.colorTextTertiary, fontSize: 12, marginTop: 2 }}
                          >
                            {formatHeure(enMinutes(c.heure_debut))} –{" "}
                            {formatHeure(enMinutes(c.heure_fin))}
                          </div>
                        )}
                      </td>
                    );
                  }
                  const ajoutable = !!onCaseVide;
                  return (
                    <td
                      key={cle}
                      onClick={() => onCaseVide?.(jr.numero, t.debut, t.fin)}
                      onMouseEnter={() => setSurvol(cle)}
                      onMouseLeave={() => setSurvol(null)}
                      title={
                        ajoutable
                          ? `Ajouter un cours le ${jr.nom.toLowerCase()} de ${formatHeure(t.debut)} à ${formatHeure(t.fin)}`
                          : undefined
                      }
                      style={{
                        ...cellule,
                        cursor: ajoutable ? "pointer" : "default",
                        textAlign: "center",
                        verticalAlign: "middle",
                        color: token.colorTextQuaternary,
                      }}
                    >
                      {ajoutable && survol === cle && <PlusOutlined />}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

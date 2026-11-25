import { PrinterOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Modal, Skeleton } from "antd";
import dayjs from "dayjs";
import { messageErreur } from "../../api/client";
import { getRecu } from "../../api/endpoints";
import type { Recu } from "../../api/types";
import { COULEURS_BENIN, FILET_BENIN } from "../../theme";
import { enLettres, fcfa, MODES } from "./format";

/**
 * Reçu de paiement. Le reçu est un document papier : il garde un fond blanc
 * et une encre sombre quel que soit le thème de l'application.
 * L'impression (window.print) n'imprime que le bloc `.recu-imprimable`
 * (règles @media print dans index.css).
 */
export function RecuModal({ paiementId, onClose }: { paiementId: number | null; onClose: () => void }) {
  const query = useQuery({
    queryKey: ["recu", paiementId],
    queryFn: () => getRecu(paiementId!),
    enabled: paiementId !== null,
  });

  return (
    <Modal
      open={paiementId !== null}
      onCancel={onClose}
      width={760}
      title="Reçu de paiement"
      destroyOnHidden
      footer={[
        <Button key="fermer" onClick={onClose}>
          Fermer
        </Button>,
        <Button
          key="imprimer"
          type="primary"
          icon={<PrinterOutlined />}
          disabled={!query.data}
          onClick={() => window.print()}
        >
          Imprimer
        </Button>,
      ]}
    >
      {query.isLoading && <Skeleton active paragraph={{ rows: 10 }} />}
      {query.isError && <Alert type="error" showIcon message={messageErreur(query.error)} />}
      {query.data && <RecuDocument recu={query.data} />}
    </Modal>
  );
}

const ENCRE = "#1f2328";
const GRIS = "#59636e";
const FILET = "#d0d7de";

function Ligne({ libelle, valeur, fort }: { libelle: string; valeur: React.ReactNode; fort?: boolean }) {
  return (
    <tr>
      <td style={{ padding: "5px 0", color: GRIS, width: "45%" }}>{libelle}</td>
      <td style={{ padding: "5px 0", textAlign: "right", fontWeight: fort ? 700 : 500, fontVariantNumeric: "tabular-nums" }}>
        {valeur}
      </td>
    </tr>
  );
}

function RecuDocument({ recu }: { recu: Recu }) {
  const p = recu.paiement;
  const sousTitre = [recu.ecole_adresse, recu.ecole_telephone && `Tél. ${recu.ecole_telephone}`]
    .filter(Boolean)
    .join(" · ");

  return (
    <div
      className="recu-imprimable"
      style={{
        background: "#fff",
        color: ENCRE,
        border: `1px solid ${FILET}`,
        borderRadius: 8,
        padding: "28px 32px",
        fontSize: 14,
        lineHeight: 1.5,
      }}
    >
      <div style={{ height: 5, background: FILET_BENIN, borderRadius: 3, marginBottom: 20 }} />

      {/* En-tête */}
      <div style={{ display: "flex", justifyContent: "space-between", gap: 24, alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{recu.ecole_nom}</div>
          {sousTitre && <div style={{ color: GRIS, fontSize: 12 }}>{sousTitre}</div>}
          <div style={{ color: GRIS, fontSize: 12 }}>Année scolaire {recu.annee_libelle}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 13, letterSpacing: 1, color: COULEURS_BENIN.vert, fontWeight: 700 }}>
            REÇU DE PAIEMENT
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "ui-monospace, monospace" }}>
            N° {p.numero_recu}
          </div>
          <div style={{ color: GRIS, fontSize: 12 }}>
            du {dayjs(p.date_paiement).format("DD/MM/YYYY")}
          </div>
        </div>
      </div>

      {/* Élève */}
      <div
        style={{
          marginTop: 20,
          padding: "12px 16px",
          border: `1px solid ${FILET}`,
          borderRadius: 6,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: 8,
        }}
      >
        <Champ libelle="Élève" valeur={`${recu.eleve_nom} ${recu.eleve_prenom}`} />
        <Champ libelle="Matricule" valeur={recu.eleve_matricule} />
        <Champ libelle="Classe" valeur={recu.classe_nom ?? "—"} />
      </div>

      {/* Montant */}
      <div style={{ marginTop: 20 }}>
        <div style={{ color: GRIS, fontSize: 12 }}>
          Reçu la somme de — {p.tranche_libelle} · {p.mode_paiement ? MODES[p.mode_paiement] : "—"}
        </div>
        <div style={{ fontSize: 26, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
          {fcfa(p.montant_paye)}
        </div>
        <div style={{ fontStyle: "italic" }}>
          Arrêté le présent reçu à la somme de{" "}
          <strong>{enLettres(p.montant_paye)} francs CFA</strong>.
        </div>
      </div>

      {/* Situation */}
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 20, borderTop: `1px solid ${FILET}` }}>
        <tbody>
          <Ligne libelle={`Montant de la ${p.tranche_libelle.toLowerCase()}`} valeur={fcfa(recu.tranche_montant)} />
          <Ligne libelle="Reste sur cette tranche" valeur={fcfa(recu.tranche_reste_apres)} />
          <tr><td colSpan={2} style={{ borderTop: `1px dashed ${FILET}`, height: 4 }} /></tr>
          <Ligne libelle="Frais de scolarité de l'année" valeur={fcfa(recu.total_du)} />
          <Ligne libelle="Total versé à ce jour" valeur={fcfa(recu.total_paye_a_date)} />
          <Ligne libelle="Reste à payer" valeur={fcfa(recu.reste_global)} fort />
        </tbody>
      </table>

      {/* Signatures */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 32, gap: 24, fontSize: 12, color: GRIS }}>
        <div>
          Enregistré par {p.enregistre_par_nom ?? "—"}
          <br />
          le {dayjs(p.created_at).format("DD/MM/YYYY à HH:mm")}
        </div>
        <div style={{ textAlign: "center", minWidth: 200 }}>
          Signature et cachet
          <div style={{ borderBottom: `1px solid ${GRIS}`, height: 56 }} />
        </div>
      </div>
    </div>
  );
}

function Champ({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div>
      <div style={{ color: GRIS, fontSize: 12 }}>{libelle}</div>
      <div style={{ fontWeight: 600 }}>{valeur}</div>
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { Alert, Descriptions, Skeleton, Statistic, Table, Tag, Typography } from "antd";
import { messageErreur } from "../../api/client";
import { getBulletinEleve } from "../../api/endpoints";
import type { BulletinLigne } from "../../api/types";

const STATUT_TAG: Record<string, { texte: string; couleur: string } | undefined> = {
  incomplete: { texte: "Incomplète", couleur: "gold" },
  sans_note: { texte: "Sans note", couleur: "default" },
};

const DECISION_TAG: Record<string, { texte: string; couleur: string }> = {
  admis: { texte: "Admis", couleur: "green" },
  redouble: { texte: "Redouble", couleur: "red" },
};

export function BulletinEleveVue({
  eleveId,
  trimestreId,
}: {
  eleveId: number;
  trimestreId: number;
}) {
  const query = useQuery({
    queryKey: ["bulletin", eleveId, trimestreId],
    queryFn: () => getBulletinEleve(eleveId, trimestreId),
  });

  if (query.isLoading) return <Skeleton active paragraph={{ rows: 8 }} />;
  if (query.isError || !query.data) {
    return <Alert type="error" showIcon message={messageErreur(query.error, "Bulletin indisponible.")} />;
  }

  const b = query.data;
  const decision = b.decision ? DECISION_TAG[b.decision] : null;

  return (
    <div>
      <Descriptions size="small" column={{ xs: 1, sm: 2 }} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="Élève">
          {b.prenom} {b.nom}
        </Descriptions.Item>
        <Descriptions.Item label="Matricule">{b.matricule}</Descriptions.Item>
        <Descriptions.Item label="Classe">{b.classe_nom}</Descriptions.Item>
        <Descriptions.Item label="Trimestre">{b.trimestre_numero}</Descriptions.Item>
      </Descriptions>

      <Table<BulletinLigne>
        rowKey="matiere_id"
        size="small"
        dataSource={b.lignes}
        pagination={false}
        columns={[
          { title: "Matière", dataIndex: "matiere_nom" },
          {
            title: "Moyenne",
            dataIndex: "moyenne_affichee",
            width: 100,
            align: "right",
            render: (v: string | null, l) => {
              const tag = STATUT_TAG[l.statut];
              if (v == null) return tag ? <Tag color={tag.couleur}>{tag.texte}</Tag> : "—";
              return v;
            },
          },
          { title: "Coef.", dataIndex: "coefficient", width: 70, align: "center" },
          {
            title: "Moy. × coef.",
            dataIndex: "moyenne_coefficientee",
            width: 110,
            align: "right",
            render: (v: number | null) => (v == null ? "—" : v.toFixed(2).replace(".", ",")),
          },
          {
            title: "Rang",
            dataIndex: "rang",
            width: 70,
            align: "center",
            render: (r: number | null) => r ?? "—",
          },
          {
            title: "Appréciation",
            dataIndex: "appreciation",
            render: (a: string | null) => a ?? "",
          },
        ]}
      />

      <div style={{ display: "flex", gap: 32, flexWrap: "wrap", marginTop: 20 }}>
        <Statistic
          title="Moyenne générale du trimestre"
          value={b.moyenne_generale_affichee ?? "—"}
        />
        <Statistic
          title="Rang"
          value={b.rang ? `${b.rang} / ${b.effectif_classe}` : "—"}
        />
        {b.moyenne_annuelle_affichee && (
          <Statistic title="Moyenne annuelle" value={b.moyenne_annuelle_affichee} />
        )}
        {decision && (
          <div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              Décision de fin d'année
            </Typography.Text>
            <div style={{ marginTop: 4 }}>
              <Tag color={decision.couleur} style={{ fontSize: 14, padding: "2px 10px" }}>
                {decision.texte}
              </Tag>
            </div>
          </div>
        )}
      </div>

      {!decision && (
        <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
          La moyenne annuelle et la décision apparaîtront quand les trois trimestres auront une
          moyenne (mode : {b.mode_calcul_annuel === "t3_renforce" ? "3e trimestre renforcé" : "poids égal"}).
        </Typography.Paragraph>
      )}
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { Alert, Card, Drawer, Empty, Select, Space, Table, Tag } from "antd";
import { useMemo, useState } from "react";
import { messageErreur } from "../api/client";
import {
  getAnneesScolaires,
  getBulletinsClasse,
  getClasses,
  getTrimestres,
} from "../api/endpoints";
import type { BulletinClasseLigne } from "../api/types";
import { BulletinEleveVue } from "./bulletins/BulletinEleveVue";

const DECISION_TAG: Record<string, { texte: string; couleur: string }> = {
  admis: { texte: "Admis", couleur: "green" },
  redouble: { texte: "Redouble", couleur: "red" },
};

export function BulletinsPage() {
  const [classeId, setClasseId] = useState<number | undefined>();
  const [trimestreId, setTrimestreId] = useState<number | undefined>();
  const [eleveOuvert, setEleveOuvert] = useState<number | null>(null);

  const anneesQuery = useQuery({ queryKey: ["annees-scolaires"], queryFn: getAnneesScolaires });
  const anneeActive = anneesQuery.data?.find((a) => a.active);

  const classesQuery = useQuery({
    queryKey: ["classes", { annee: anneeActive?.id }],
    queryFn: () => getClasses({ annee_scolaire_id: anneeActive!.id }),
    enabled: !!anneeActive,
  });
  const trimestresQuery = useQuery({
    queryKey: ["trimestres", anneeActive?.id],
    queryFn: () => getTrimestres(anneeActive!.id),
    enabled: !!anneeActive,
  });

  const bulletinsQuery = useQuery({
    queryKey: ["bulletins-classe", classeId, trimestreId],
    queryFn: () => getBulletinsClasse(classeId!, trimestreId!),
    enabled: !!classeId && !!trimestreId,
  });

  const lignesTriees = useMemo(() => {
    const l = bulletinsQuery.data?.eleves ?? [];
    return [...l].sort((a, b) => {
      if (a.rang == null) return 1;
      if (b.rang == null) return -1;
      return a.rang - b.rang;
    });
  }, [bulletinsQuery.data]);

  return (
    <Card title="Bulletins">
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          style={{ width: 240 }}
          placeholder="Classe"
          value={classeId}
          onChange={setClasseId}
          loading={classesQuery.isLoading}
          showSearch
          optionFilterProp="label"
          options={(classesQuery.data ?? []).map((c) => ({ value: c.id, label: c.nom }))}
        />
        <Select
          style={{ width: 200 }}
          placeholder="Trimestre"
          value={trimestreId}
          onChange={setTrimestreId}
          loading={trimestresQuery.isLoading}
          options={(trimestresQuery.data ?? []).map((t) => ({
            value: t.id,
            label: `Trimestre ${t.numero}`,
          }))}
        />
      </Space>

      {!classeId || !trimestreId ? (
        <Empty description="Choisis une classe et un trimestre." />
      ) : bulletinsQuery.isError ? (
        <Alert
          type="error"
          showIcon
          message={messageErreur(bulletinsQuery.error, "Impossible de charger les bulletins.")}
        />
      ) : (
        <Table<BulletinClasseLigne>
          rowKey="eleve_id"
          loading={bulletinsQuery.isLoading}
          dataSource={lignesTriees}
          pagination={{ pageSize: 30, hideOnSinglePage: true }}
          onRow={(l) => ({
            onClick: () => setEleveOuvert(l.eleve_id),
            style: { cursor: "pointer" },
          })}
          footer={() =>
            bulletinsQuery.data
              ? `Effectif classé : ${bulletinsQuery.data.effectif_classe}`
              : ""
          }
          columns={[
            {
              title: "Rang",
              dataIndex: "rang",
              width: 70,
              align: "center",
              render: (r: number | null) => r ?? "—",
            },
            { title: "Matricule", dataIndex: "matricule", width: 130 },
            { title: "Nom", dataIndex: "nom" },
            { title: "Prénom", dataIndex: "prenom" },
            {
              title: "Moyenne",
              dataIndex: "moyenne_generale_affichee",
              width: 110,
              align: "right",
              render: (v: string | null) => v ?? "—",
            },
            {
              title: "Décision",
              dataIndex: "decision",
              width: 120,
              render: (d: string | null) =>
                d ? <Tag color={DECISION_TAG[d].couleur}>{DECISION_TAG[d].texte}</Tag> : "—",
            },
          ]}
        />
      )}

      <Drawer
        title="Bulletin de l'élève"
        width={720}
        open={eleveOuvert !== null}
        onClose={() => setEleveOuvert(null)}
        destroyOnHidden
      >
        {eleveOuvert !== null && trimestreId && (
          <BulletinEleveVue eleveId={eleveOuvert} trimestreId={trimestreId} />
        )}
      </Drawer>
    </Card>
  );
}

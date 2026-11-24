import { useQuery } from "@tanstack/react-query";
import { Select, Space, Table, Tag, Typography } from "antd";
import dayjs from "dayjs";
import { useState } from "react";
import { getHistoriqueNotes, getTrimestres } from "../../api/endpoints";
import type { NoteHistorique, ValeursNote } from "../../api/types";

const LIBELLES: Record<string, string> = {
  interro1: "Interro 1",
  interro2: "Interro 2",
  interro3: "Interro 3",
  devoir1: "Devoir 1",
  devoir2: "Devoir 2",
  note_directe: "Note",
  appreciation: "Appréciation",
};

const ACTIONS: Record<NoteHistorique["action"], { libelle: string; couleur: string }> = {
  creation: { libelle: "Saisie", couleur: "green" },
  modification: { libelle: "Modification", couleur: "orange" },
  suppression: { libelle: "Suppression", couleur: "red" },
};

function fmt(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return typeof v === "number" ? v.toLocaleString("fr-FR") : v;
}

/** Liste lisible des champs : seulement ceux qui ont changé pour une modification. */
function changements(h: NoteHistorique): Array<{ champ: string; avant?: string; apres?: string }> {
  const avant: ValeursNote = h.anciennes_valeurs ?? {};
  const apres: ValeursNote = h.nouvelles_valeurs ?? {};
  return Object.keys(LIBELLES).flatMap((champ) => {
    const a = avant[champ as keyof ValeursNote];
    const b = apres[champ as keyof ValeursNote];
    if (h.action === "modification") {
      return (a ?? null) === (b ?? null) ? [] : [{ champ, avant: fmt(a), apres: fmt(b) }];
    }
    const v = h.action === "creation" ? b : a;
    return v === null || v === undefined ? [] : [{ champ, apres: fmt(v) }];
  });
}

export function HistoriqueNotesTab({ classeId, anneeScolaireId }: { classeId: number; anneeScolaireId: number }) {
  const [trimestreId, setTrimestreId] = useState<number | undefined>();

  const trimestresQuery = useQuery({
    queryKey: ["trimestres", anneeScolaireId],
    queryFn: () => getTrimestres(anneeScolaireId),
  });
  const numeros = new Map((trimestresQuery.data ?? []).map((t) => [t.id, t.numero]));

  const historiqueQuery = useQuery({
    queryKey: ["notes-historique", classeId, trimestreId],
    queryFn: () => getHistoriqueNotes({ classe_id: classeId, trimestre_id: trimestreId }),
  });

  return (
    <Space orientation="vertical" size="middle" style={{ display: "flex" }}>
      <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
        <Typography.Text type="secondary">
          Toute saisie, modification ou suppression de note par un enseignant est enregistrée ici.
        </Typography.Text>
        <Select
          allowClear
          placeholder="Tous les trimestres"
          style={{ width: 190 }}
          value={trimestreId}
          onChange={setTrimestreId}
          options={(trimestresQuery.data ?? []).map((t) => ({ value: t.id, label: `Trimestre ${t.numero}` }))}
        />
      </Space>
      <Table<NoteHistorique>
        rowKey="id"
        size="small"
        loading={historiqueQuery.isLoading}
        dataSource={historiqueQuery.data ?? []}
        pagination={{ pageSize: 25, hideOnSinglePage: true }}
        scroll={{ x: 760 }}
        locale={{ emptyText: "Aucune saisie de note pour l'instant." }}
        columns={[
          {
            title: "Date",
            dataIndex: "le",
            width: 140,
            render: (d: string) => dayjs(d).format("DD/MM/YYYY HH:mm"),
          },
          {
            title: "Trim.",
            dataIndex: "trimestre_id",
            width: 60,
            align: "center",
            render: (id: number) => (numeros.has(id) ? `T${numeros.get(id)}` : "—"),
          },
          { title: "Élève", dataIndex: "eleve_nom" },
          { title: "Matière", dataIndex: "matiere_nom" },
          {
            title: "Action",
            dataIndex: "action",
            width: 120,
            render: (a: NoteHistorique["action"]) => <Tag color={ACTIONS[a].couleur}>{ACTIONS[a].libelle}</Tag>,
          },
          {
            title: "Détail",
            key: "detail",
            render: (_, h) => (
              <Space orientation="vertical" size={0}>
                {changements(h).map((c) => (
                  <span key={c.champ} style={{ whiteSpace: "nowrap" }}>
                    <Typography.Text type="secondary">{LIBELLES[c.champ]} : </Typography.Text>
                    {c.avant !== undefined ? (
                      <>
                        <Typography.Text delete type="secondary">
                          {c.avant}
                        </Typography.Text>{" "}
                        → <Typography.Text strong>{c.apres}</Typography.Text>
                      </>
                    ) : h.action === "suppression" ? (
                      <Typography.Text delete>{c.apres}</Typography.Text>
                    ) : (
                      c.apres
                    )}
                  </span>
                ))}
              </Space>
            ),
          },
          { title: "Par", dataIndex: "auteur_nom", render: (n: string | null) => n ?? "—" },
        ]}
      />
    </Space>
  );
}

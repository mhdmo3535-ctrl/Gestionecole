import { useQuery } from "@tanstack/react-query";
import { Button, Card, Input, Table, Tag } from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getClasses, getEleves } from "../api/endpoints";
import type { Eleve } from "../api/types";
import { EleveFormModal } from "./eleves/EleveFormModal";
import { useDroits } from "../auth/droits";

const STATUT_COULEUR: Record<Eleve["statut"], string> = {
  actif: "green",
  redoublant: "gold",
  archive: "default",
};

export function ElevesPage() {
  const { peut } = useDroits();
  const peutInscrire = peut("eleves", true);
  const navigate = useNavigate();

  const [recherche, setRecherche] = useState("");
  const [modalOuvert, setModalOuvert] = useState(false);

  const classesQuery = useQuery({ queryKey: ["classes"], queryFn: () => getClasses() });
  const elevesQuery = useQuery({
    queryKey: ["eleves", recherche],
    queryFn: () => getEleves(recherche ? { q: recherche } : undefined),
  });

  const classesParId = useMemo(
    () => new Map((classesQuery.data ?? []).map((c) => [c.id, c])),
    [classesQuery.data],
  );

  return (
    <Card
      title="Élèves"
      extra={
        peutInscrire && (
          <Button type="primary" onClick={() => setModalOuvert(true)}>
            Nouvel élève
          </Button>
        )
      }
    >
      <Input.Search
        placeholder="Rechercher par nom, prénom ou matricule"
        allowClear
        onSearch={setRecherche}
        onChange={(e) => !e.target.value && setRecherche("")}
        style={{ maxWidth: 360, marginBottom: 16 }}
      />
      <Table<Eleve>
        rowKey="id"
        loading={elevesQuery.isLoading}
        dataSource={elevesQuery.data ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        onRow={(eleve) => ({
          onClick: () => navigate(`/eleves/${eleve.id}`),
          style: { cursor: "pointer" },
        })}
        columns={[
          { title: "Matricule", dataIndex: "matricule", width: 130 },
          { title: "Nom", dataIndex: "nom" },
          { title: "Prénom", dataIndex: "prenom" },
          { title: "Sexe", dataIndex: "sexe", width: 70, render: (s) => s ?? "—" },
          {
            title: "Classe",
            dataIndex: "classe_id",
            render: (id: number | null) => (id ? (classesParId.get(id)?.nom ?? "—") : "—"),
          },
          {
            title: "Statut",
            dataIndex: "statut",
            width: 110,
            render: (s: Eleve["statut"]) => <Tag color={STATUT_COULEUR[s]}>{s}</Tag>,
          },
          {
            title: "",
            key: "actions",
            width: 90,
            render: (_: unknown, eleve: Eleve) => (
              <Button
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/eleves/${eleve.id}`);
                }}
              >
                Ouvrir
              </Button>
            ),
          },
        ]}
      />

      <EleveFormModal open={modalOuvert} eleve={null} onClose={() => setModalOuvert(false)} />
    </Card>
  );
}

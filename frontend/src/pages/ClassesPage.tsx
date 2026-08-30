import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App as AntApp, Button, Card, Popconfirm, Select, Space, Table, Tag } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { messageErreur } from "../api/client";
import { getAnneesScolaires, getClasses, getNiveaux, supprimerClasse } from "../api/endpoints";
import type { Classe } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ClasseFormModal } from "./classes/ClasseFormModal";

export function ClassesPage() {
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  const { message } = AntApp.useApp();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [anneeId, setAnneeId] = useState<number | undefined>(undefined);
  const [niveauId, setNiveauId] = useState<number | undefined>(undefined);
  const [modalOuvert, setModalOuvert] = useState(false);
  const [enEdition, setEnEdition] = useState<Classe | null>(null);

  const anneesQuery = useQuery({ queryKey: ["annees-scolaires"], queryFn: getAnneesScolaires });
  const niveauxQuery = useQuery({ queryKey: ["niveaux"], queryFn: getNiveaux });

  const anneeEffective = anneeId ?? anneesQuery.data?.find((a) => a.active)?.id;

  const classesQuery = useQuery({
    queryKey: ["classes", { annee: anneeEffective, niveau: niveauId }],
    queryFn: () => getClasses({ annee_scolaire_id: anneeEffective, niveau_id: niveauId }),
    enabled: anneeEffective !== undefined,
  });

  const suppression = useMutation({
    mutationFn: (id: number) => supprimerClasse(id),
    onSuccess: () => {
      message.success("Classe supprimée.");
      qc.invalidateQueries({ queryKey: ["classes"] });
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  function ouvrirCreation() {
    setEnEdition(null);
    setModalOuvert(true);
  }
  function ouvrirEdition(classe: Classe) {
    setEnEdition(classe);
    setModalOuvert(true);
  }

  return (
    <Card
      title="Classes"
      extra={
        estAdmin && (
          <Button type="primary" onClick={ouvrirCreation}>
            Nouvelle classe
          </Button>
        )
      }
    >
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          style={{ width: 200 }}
          value={anneeEffective}
          onChange={setAnneeId}
          loading={anneesQuery.isLoading}
          options={(anneesQuery.data ?? []).map((a) => ({
            value: a.id,
            label: a.active ? `${a.libelle} (active)` : a.libelle,
          }))}
        />
        <Select
          style={{ width: 200 }}
          allowClear
          placeholder="Tous les niveaux"
          value={niveauId}
          onChange={setNiveauId}
          loading={niveauxQuery.isLoading}
          options={(niveauxQuery.data ?? []).map((n) => ({ value: n.id, label: n.nom }))}
        />
      </Space>

      <Table<Classe>
        rowKey="id"
        loading={classesQuery.isLoading}
        dataSource={classesQuery.data ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        onRow={(c) => ({ onClick: () => navigate(`/classes/${c.id}`), style: { cursor: "pointer" } })}
        columns={[
          { title: "Classe", dataIndex: "nom" },
          { title: "Niveau", dataIndex: "niveau_nom", width: 110 },
          {
            title: "Série",
            dataIndex: "serie_nom",
            width: 120,
            render: (s: string | null) => s ?? "—",
          },
          {
            title: "Cycle",
            dataIndex: "cycle",
            width: 110,
            render: (c: string) => (
              <Tag color={c === "college" ? "blue" : "geekblue"}>
                {c === "college" ? "Collège" : "Lycée"}
              </Tag>
            ),
          },
          { title: "Effectif", dataIndex: "effectif", width: 100, align: "center" },
          ...(estAdmin
            ? [
                {
                  title: "",
                  key: "actions",
                  width: 170,
                  render: (_: unknown, classe: Classe) => (
                    <Space onClick={(e) => e.stopPropagation()}>
                      <Button size="small" onClick={() => ouvrirEdition(classe)}>
                        Modifier
                      </Button>
                      <Popconfirm
                        title="Supprimer cette classe ?"
                        okText="Supprimer"
                        cancelText="Annuler"
                        okButtonProps={{ danger: true }}
                        onConfirm={() => suppression.mutate(classe.id)}
                      >
                        <Button size="small" danger>
                          Supprimer
                        </Button>
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]
            : []),
        ]}
      />

      <ClasseFormModal
        open={modalOuvert}
        classe={enEdition}
        onClose={() => {
          setModalOuvert(false);
          setEnEdition(null);
        }}
      />
    </Card>
  );
}

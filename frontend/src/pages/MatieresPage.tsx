import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App as AntApp, Button, Card, Input, Popconfirm, Space, Table, Tag } from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { messageErreur } from "../api/client";
import { getMatieres, supprimerMatiere } from "../api/endpoints";
import type { Matiere } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { MatiereFormModal } from "./matieres/MatiereFormModal";

export function MatieresPage() {
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const [recherche, setRecherche] = useState("");
  const [modalOuvert, setModalOuvert] = useState(false);
  const [enEdition, setEnEdition] = useState<Matiere | null>(null);

  const matieresQuery = useQuery({ queryKey: ["matieres"], queryFn: getMatieres });

  const donnees = useMemo(() => {
    const t = recherche.trim().toLowerCase();
    const liste = matieresQuery.data ?? [];
    return t ? liste.filter((m) => m.nom.toLowerCase().includes(t)) : liste;
  }, [matieresQuery.data, recherche]);

  const suppression = useMutation({
    mutationFn: (id: number) => supprimerMatiere(id),
    onSuccess: () => {
      message.success("Matière supprimée.");
      qc.invalidateQueries({ queryKey: ["matieres"] });
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <Card
      title="Matières"
      extra={
        estAdmin && (
          <Button
            type="primary"
            onClick={() => {
              setEnEdition(null);
              setModalOuvert(true);
            }}
          >
            Nouvelle matière
          </Button>
        )
      }
    >
      <Input.Search
        placeholder="Rechercher une matière"
        allowClear
        onChange={(e) => setRecherche(e.target.value)}
        style={{ maxWidth: 320, marginBottom: 16 }}
      />
      <Table<Matiere>
        rowKey="id"
        loading={matieresQuery.isLoading}
        dataSource={donnees}
        pagination={{ pageSize: 25, hideOnSinglePage: true }}
        onRow={(m) => ({
          onClick: () => navigate(`/matieres/${m.id}`),
          style: { cursor: "pointer" },
        })}
        columns={[
          { title: "Matière", dataIndex: "nom" },
          { title: "Code", dataIndex: "code", width: 120, render: (c: string | null) => c ?? "—" },
          {
            title: "Type",
            key: "type",
            width: 220,
            render: (_: unknown, m: Matiere) =>
              m.note_directe ? (
                <Tag color="gold">Note directe</Tag>
              ) : m.est_choix_langue ? (
                <Tag color="blue">Choix de langue</Tag>
              ) : (
                <Tag>3 interros + 2 devoirs</Tag>
              ),
          },
          ...(estAdmin
            ? [
                {
                  title: "",
                  key: "actions",
                  width: 170,
                  render: (_: unknown, matiere: Matiere) => (
                    <Space onClick={(e) => e.stopPropagation()}>
                      <Button
                        size="small"
                        onClick={() => {
                          setEnEdition(matiere);
                          setModalOuvert(true);
                        }}
                      >
                        Modifier
                      </Button>
                      <Popconfirm
                        title="Supprimer cette matière ?"
                        description="Impossible si des notes y sont enregistrées."
                        okText="Supprimer"
                        cancelText="Annuler"
                        okButtonProps={{ danger: true }}
                        onConfirm={() => suppression.mutate(matiere.id)}
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

      <MatiereFormModal
        open={modalOuvert}
        matiere={enEdition}
        onClose={() => {
          setModalOuvert(false);
          setEnEdition(null);
        }}
      />
    </Card>
  );
}

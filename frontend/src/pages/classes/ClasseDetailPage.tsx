import { ArrowLeftOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Result, Skeleton, Space, Table, Tabs, Tag, Typography } from "antd";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getClasse, getElevesDeLaClasse, getMatieresDeLaClasse } from "../../api/endpoints";
import type { ClasseMatiere, Eleve } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { ClasseFormModal } from "./ClasseFormModal";
import { HistoriqueNotesTab } from "./HistoriqueNotesTab";

export function ClasseDetailPage() {
  const { id } = useParams();
  const classeId = Number(id);
  const navigate = useNavigate();
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  const [editionOuverte, setEditionOuverte] = useState(false);

  const classeQuery = useQuery({
    queryKey: ["classe", classeId],
    queryFn: () => getClasse(classeId),
    enabled: Number.isFinite(classeId),
  });
  const elevesQuery = useQuery({
    queryKey: ["classe", classeId, "eleves"],
    queryFn: () => getElevesDeLaClasse(classeId),
    enabled: Number.isFinite(classeId),
  });
  const matieresQuery = useQuery({
    queryKey: ["classe", classeId, "matieres"],
    queryFn: () => getMatieresDeLaClasse(classeId),
    enabled: Number.isFinite(classeId),
  });

  const classe = classeQuery.data;

  if (classeQuery.isLoading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    );
  }
  if (classeQuery.isError || !classe) {
    return (
      <Card>
        <Result
          status="404"
          title="Classe introuvable"
          extra={
            <Button type="primary" onClick={() => navigate("/classes")}>
              Retour à la liste
            </Button>
          }
        />
      </Card>
    );
  }

  return (
    <Space orientation="vertical" size="middle" style={{ display: "flex" }}>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate("/classes")}
        style={{ paddingInline: 0 }}
      >
        Classes
      </Button>

      <Card
        title={
          <Space size="middle" wrap>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {classe.nom}
            </Typography.Title>
            <Tag>{classe.niveau_nom}</Tag>
            {classe.serie_nom && <Tag color="geekblue">Série {classe.serie_nom}</Tag>}
            <Typography.Text type="secondary">Année {classe.annee_libelle}</Typography.Text>
            <Typography.Text type="secondary">
              Professeur principal : {classe.professeur_principal_nom ?? <em>non désigné</em>}
            </Typography.Text>
          </Space>
        }
        extra={estAdmin && <Button onClick={() => setEditionOuverte(true)}>Modifier</Button>}
      >
        <Tabs
          defaultActiveKey="eleves"
          items={[
            {
              key: "eleves",
              label: `Élèves (${classe.effectif})`,
              children: (
                <Table<Eleve>
                  rowKey="id"
                  size="small"
                  loading={elevesQuery.isLoading}
                  dataSource={elevesQuery.data ?? []}
                  pagination={{ pageSize: 25, hideOnSinglePage: true }}
                  onRow={(e) => ({
                    onClick: () => navigate(`/eleves/${e.id}`),
                    style: { cursor: "pointer" },
                  })}
                  columns={[
                    { title: "Matricule", dataIndex: "matricule", width: 130 },
                    { title: "Nom", dataIndex: "nom" },
                    { title: "Prénom", dataIndex: "prenom" },
                    {
                      title: "Sexe",
                      dataIndex: "sexe",
                      width: 70,
                      render: (s) => s ?? "—",
                    },
                  ]}
                />
              ),
            },
            {
              key: "matieres",
              label: `Matières (${matieresQuery.data?.length ?? 0})`,
              children: (
                <Table<ClasseMatiere>
                  rowKey="matiere_id"
                  size="small"
                  loading={matieresQuery.isLoading}
                  dataSource={matieresQuery.data ?? []}
                  pagination={false}
                  columns={[
                    { title: "Matière", dataIndex: "nom" },
                    {
                      title: "Coefficient",
                      dataIndex: "coefficient",
                      width: 130,
                      align: "center",
                    },
                    {
                      title: "Type",
                      dataIndex: "note_directe",
                      width: 160,
                      render: (directe: boolean) =>
                        directe ? <Tag color="gold">Note directe</Tag> : "3 interros + 2 devoirs",
                    },
                  ]}
                />
              ),
            },
            ...(estAdmin
              ? [
                  {
                    key: "historique",
                    label: "Historique des notes",
                    children: (
                      <HistoriqueNotesTab classeId={classe.id} anneeScolaireId={classe.annee_scolaire_id} />
                    ),
                  },
                ]
              : []),
          ]}
        />
      </Card>

      <ClasseFormModal
        open={editionOuverte}
        classe={classe}
        onClose={() => setEditionOuverte(false)}
      />
    </Space>
  );
}

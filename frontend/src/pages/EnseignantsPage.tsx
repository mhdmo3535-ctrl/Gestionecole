import { useQuery } from "@tanstack/react-query";
import { Button, Card, Segmented, Space, Table, Tag } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getUtilisateurs } from "../api/endpoints";
import type { Utilisateur } from "../api/types";
import { EnseignantFormModal } from "./enseignants/EnseignantFormModal";
import { MotDePasseModal } from "./enseignants/MotDePasseModal";

export function EnseignantsPage() {
  const navigate = useNavigate();
  const [filtre, setFiltre] = useState<"actifs" | "tous">("actifs");
  const [formOuvert, setFormOuvert] = useState(false);
  const [enEdition, setEnEdition] = useState<Utilisateur | null>(null);
  const [mdpPour, setMdpPour] = useState<number | null>(null);

  const query = useQuery({
    queryKey: ["utilisateurs", "enseignant", filtre],
    queryFn: () =>
      getUtilisateurs({ role: "enseignant", actif: filtre === "actifs" ? true : undefined }),
  });

  return (
    <Card
      title="Enseignants"
      extra={
        <Button
          type="primary"
          onClick={() => {
            setEnEdition(null);
            setFormOuvert(true);
          }}
        >
          Nouvel enseignant
        </Button>
      }
    >
      <Segmented
        value={filtre}
        onChange={(v) => setFiltre(v as "actifs" | "tous")}
        options={[
          { label: "Actifs", value: "actifs" },
          { label: "Tous", value: "tous" },
        ]}
        style={{ marginBottom: 16 }}
      />

      <Table<Utilisateur>
        rowKey="id"
        loading={query.isLoading}
        dataSource={query.data ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        onRow={(u) => ({
          onClick: () => navigate(`/enseignants/${u.id}`),
          style: { cursor: "pointer" },
        })}
        columns={[
          { title: "Nom", dataIndex: "nom" },
          { title: "Prénom", dataIndex: "prenom" },
          { title: "Email", dataIndex: "email" },
          {
            title: "Téléphone",
            dataIndex: "telephone",
            width: 140,
            render: (t: string | null) => t ?? "—",
          },
          {
            title: "Compte",
            dataIndex: "actif",
            width: 110,
            render: (a: boolean) =>
              a ? <Tag color="green">Actif</Tag> : <Tag color="red">Désactivé</Tag>,
          },
          {
            title: "",
            key: "actions",
            width: 240,
            render: (_: unknown, u: Utilisateur) => (
              <Space onClick={(e) => e.stopPropagation()}>
                <Button
                  size="small"
                  onClick={() => {
                    setEnEdition(u);
                    setFormOuvert(true);
                  }}
                >
                  Modifier
                </Button>
                <Button size="small" onClick={() => setMdpPour(u.id)}>
                  Mot de passe
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <EnseignantFormModal
        open={formOuvert}
        enseignant={enEdition}
        onClose={() => {
          setFormOuvert(false);
          setEnEdition(null);
        }}
      />
      <MotDePasseModal
        open={mdpPour !== null}
        enseignantId={mdpPour}
        onClose={() => setMdpPour(null)}
      />
    </Card>
  );
}

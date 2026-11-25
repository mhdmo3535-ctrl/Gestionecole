import { useQuery } from "@tanstack/react-query";
import { Button, Card, Segmented, Select, Space, Table, Tag } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getUtilisateurs } from "../api/endpoints";
import type { Role, Utilisateur } from "../api/types";
import { COULEURS_ROLES, LIBELLES_ROLES, ROLES_PERSONNEL, useDroits } from "../auth/droits";
import { MotDePasseModal } from "./personnel/MotDePasseModal";
import { PersonnelFormModal } from "./personnel/PersonnelFormModal";

/**
 * Personnel (directeur : tous les comptes, rôles, mots de passe) ou
 * Enseignants (censeur : les professeurs seulement, en consultation, pour
 * leurs affectations).
 */
export function PersonnelPage({
  enseignantsSeulement = false,
}: {
  enseignantsSeulement?: boolean;
}) {
  const navigate = useNavigate();
  const { peut } = useDroits();
  const peutGerer = peut("personnel", true) && !enseignantsSeulement;
  const [filtre, setFiltre] = useState<"actifs" | "tous">("actifs");
  const [roleChoisi, setRole] = useState<Role | undefined>();
  const role: Role | undefined = enseignantsSeulement ? "enseignant" : roleChoisi;
  const [formOuvert, setFormOuvert] = useState(false);
  const [enEdition, setEnEdition] = useState<Utilisateur | null>(null);
  const [mdpPour, setMdpPour] = useState<number | null>(null);

  const query = useQuery({
    queryKey: ["utilisateurs", role ?? "tous", filtre],
    queryFn: () => getUtilisateurs({ role, actif: filtre === "actifs" ? true : undefined }),
  });

  return (
    <Card
      title={enseignantsSeulement ? "Enseignants" : "Personnel"}
      extra={
        peutGerer && (
          <Button
            type="primary"
            onClick={() => {
              setEnEdition(null);
              setFormOuvert(true);
            }}
          >
            Nouveau membre
          </Button>
        )
      }
    >
      <Space wrap style={{ marginBottom: 16 }}>
        <Segmented
          value={filtre}
          onChange={(v) => setFiltre(v as "actifs" | "tous")}
          options={[
            { label: "Actifs", value: "actifs" },
            { label: "Tous", value: "tous" },
          ]}
        />
        {!enseignantsSeulement && (
          <Select
            allowClear
            placeholder="Tous les rôles"
            style={{ width: 210 }}
            value={role}
            onChange={setRole}
            options={ROLES_PERSONNEL.map((r) => ({ value: r, label: LIBELLES_ROLES[r] }))}
          />
        )}
      </Space>

      <Table<Utilisateur>
        rowKey="id"
        loading={query.isLoading}
        dataSource={query.data ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        scroll={{ x: 820 }}
        onRow={(u) => ({
          onClick: () => navigate(`/personnel/${u.id}`),
          style: { cursor: "pointer" },
        })}
        columns={[
          { title: "Nom", dataIndex: "nom" },
          { title: "Prénom", dataIndex: "prenom" },
          ...(enseignantsSeulement
            ? []
            : [
                {
                  title: "Rôle(s)",
                  dataIndex: "roles",
                  render: (roles: Role[]) => (
                    <Space size={[4, 4]} wrap>
                      {ROLES_PERSONNEL.filter((r) => roles.includes(r)).map((r) => (
                        <Tag key={r} color={COULEURS_ROLES[r]} style={{ marginInlineEnd: 0 }}>
                          {LIBELLES_ROLES[r]}
                        </Tag>
                      ))}
                    </Space>
                  ),
                },
              ]),
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
          ...(peutGerer
            ? [
                {
                  title: "",
                  key: "actions",
                  width: 210,
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
              ]
            : []),
        ]}
      />

      <PersonnelFormModal
        open={formOuvert}
        membre={enEdition}
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

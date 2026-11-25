import { ArrowLeftOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  App as AntApp,
  Button,
  Card,
  Divider,
  Form,
  Popconfirm,
  Result,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { messageErreur } from "../../api/client";
import {
  ajouterAffectation,
  getAffectations,
  getClasses,
  getMatieres,
  getUtilisateur,
  retirerAffectation,
} from "../../api/endpoints";
import type { Affectation } from "../../api/types";
import { COULEURS_ROLES, LIBELLES_ROLES, ROLES_PERSONNEL, useDroits } from "../../auth/droits";
import { PersonnelFormModal } from "./PersonnelFormModal";
import { MotDePasseModal } from "./MotDePasseModal";

export function PersonnelDetailPage() {
  const { id } = useParams();
  const enseignantId = Number(id);
  const navigate = useNavigate();
  const { peut } = useDroits();
  const peutGererCompte = peut("personnel", true);
  // le censeur arrive ici depuis « Enseignants », le directeur depuis « Personnel »
  const retour = peut("personnel")
    ? { chemin: "/personnel", libelle: "Personnel" }
    : { chemin: "/enseignants", libelle: "Enseignants" };
  const peutAffecter = peut("pedagogie", true);
  const { message } = AntApp.useApp();
  const qc = useQueryClient();

  const [editionOuverte, setEditionOuverte] = useState(false);
  const [mdpOuvert, setMdpOuvert] = useState(false);
  const [form] = Form.useForm<{ classe_id: number; matiere_id: number }>();

  const enseignantQuery = useQuery({
    queryKey: ["utilisateur", enseignantId],
    queryFn: () => getUtilisateur(enseignantId),
    enabled: Number.isFinite(enseignantId),
  });
  const affectationsQuery = useQuery({
    queryKey: ["utilisateur", enseignantId, "affectations"],
    queryFn: () => getAffectations(enseignantId),
    enabled: Number.isFinite(enseignantId) && !!enseignantQuery.data?.roles.includes("enseignant"),
  });
  const classesQuery = useQuery({ queryKey: ["classes"], queryFn: () => getClasses() });
  const matieresQuery = useQuery({ queryKey: ["matieres"], queryFn: getMatieres });

  const ajout = useMutation({
    mutationFn: (v: { classe_id: number; matiere_id: number }) =>
      ajouterAffectation(enseignantId, v),
    onSuccess: () => {
      message.success("Affectation ajoutée.");
      qc.invalidateQueries({ queryKey: ["utilisateur", enseignantId, "affectations"] });
      form.resetFields();
    },
    onError: (e) => message.error(messageErreur(e)),
  });
  const retrait = useMutation({
    mutationFn: (affId: number) => retirerAffectation(enseignantId, affId),
    onSuccess: () => {
      message.success("Affectation retirée.");
      qc.invalidateQueries({ queryKey: ["utilisateur", enseignantId, "affectations"] });
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  const enseignant = enseignantQuery.data;
  const estEnseignant = !!enseignant?.roles.includes("enseignant");

  if (enseignantQuery.isLoading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 5 }} />
      </Card>
    );
  }
  if (enseignantQuery.isError || !enseignant) {
    return (
      <Card>
        <Result
          status="404"
          title="Membre du personnel introuvable"
          extra={
            <Button type="primary" onClick={() => navigate(retour.chemin)}>
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
        onClick={() => navigate(retour.chemin)}
        style={{ paddingInline: 0 }}
      >
        {retour.libelle}
      </Button>

      <Card
        title={
          <Space size="middle" wrap>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {enseignant.prenom} {enseignant.nom}
            </Typography.Title>
            {ROLES_PERSONNEL.filter((r) => enseignant.roles.includes(r)).map((r) => (
              <Tag key={r} color={COULEURS_ROLES[r]}>
                {LIBELLES_ROLES[r]}
              </Tag>
            ))}
            <Typography.Text type="secondary">{enseignant.email}</Typography.Text>
            {enseignant.actif ? <Tag color="green">Actif</Tag> : <Tag color="red">Désactivé</Tag>}
          </Space>
        }
        extra={
          peutGererCompte && (
            <Space>
              <Button onClick={() => setEditionOuverte(true)}>Modifier</Button>
              <Button onClick={() => setMdpOuvert(true)}>Mot de passe</Button>
            </Space>
          )
        }
      >
        {!estEnseignant ? (
          <Typography.Text type="secondary">
            Ce compte n'a pas le rôle « Enseignant » : il n'a pas de classes ni de matières
            affectées.
          </Typography.Text>
        ) : (
          <>
            <Typography.Title level={5} style={{ marginTop: 0 }}>
              Affectations
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              Les classes et matières que cet enseignant est autorisé à noter.
            </Typography.Paragraph>

            <Table<Affectation>
              rowKey="id"
              size="small"
              loading={affectationsQuery.isLoading}
              dataSource={affectationsQuery.data ?? []}
              pagination={false}
              columns={[
                { title: "Classe", dataIndex: "classe_nom" },
                { title: "Matière", dataIndex: "matiere_nom" },
                ...(peutAffecter
                  ? [
                      {
                        title: "",
                        key: "actions",
                        width: 100,
                        render: (_: unknown, a: Affectation) => (
                          <Popconfirm
                            title="Retirer cette affectation ?"
                            okText="Retirer"
                            cancelText="Annuler"
                            okButtonProps={{ danger: true }}
                            onConfirm={() => retrait.mutate(a.id)}
                          >
                            <Button size="small" danger>
                              Retirer
                            </Button>
                          </Popconfirm>
                        ),
                      },
                    ]
                  : []),
              ]}
            />

            {peutAffecter && (
              <>
                <Divider />
                <Typography.Text strong>Ajouter une affectation</Typography.Text>
                <Form
                  form={form}
                  layout="inline"
                  onFinish={(v) => ajout.mutate(v)}
                  style={{ marginTop: 12, rowGap: 12 }}
                >
                  <Form.Item name="classe_id" rules={[{ required: true, message: "Classe." }]}>
                    <Select
                      style={{ width: 220 }}
                      placeholder="Classe"
                      loading={classesQuery.isLoading}
                      showSearch
                      optionFilterProp="label"
                      options={(classesQuery.data ?? []).map((c) => ({
                        value: c.id,
                        label: c.nom,
                      }))}
                    />
                  </Form.Item>
                  <Form.Item name="matiere_id" rules={[{ required: true, message: "Matière." }]}>
                    <Select
                      style={{ width: 240 }}
                      placeholder="Matière"
                      loading={matieresQuery.isLoading}
                      showSearch
                      optionFilterProp="label"
                      options={(matieresQuery.data ?? []).map((m) => ({
                        value: m.id,
                        label: m.nom,
                      }))}
                    />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={ajout.isPending}>
                      Ajouter
                    </Button>
                  </Form.Item>
                </Form>
              </>
            )}
          </>
        )}
      </Card>

      <PersonnelFormModal
        open={editionOuverte}
        membre={enseignant}
        onClose={() => setEditionOuverte(false)}
      />
      <MotDePasseModal
        open={mdpOuvert}
        enseignantId={mdpOuvert ? enseignant.id : null}
        onClose={() => setMdpOuvert(false)}
      />
    </Space>
  );
}

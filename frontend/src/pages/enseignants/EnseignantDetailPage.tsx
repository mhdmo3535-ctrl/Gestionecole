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
import { useAuth } from "../../auth/AuthContext";
import { EnseignantFormModal } from "./EnseignantFormModal";
import { MotDePasseModal } from "./MotDePasseModal";

export function EnseignantDetailPage() {
  const { id } = useParams();
  const enseignantId = Number(id);
  const navigate = useNavigate();
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
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
    enabled: Number.isFinite(enseignantId),
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
          title="Enseignant introuvable"
          extra={
            <Button type="primary" onClick={() => navigate("/enseignants")}>
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
        onClick={() => navigate("/enseignants")}
        style={{ paddingInline: 0 }}
      >
        Enseignants
      </Button>

      <Card
        title={
          <Space size="middle" wrap>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {enseignant.prenom} {enseignant.nom}
            </Typography.Title>
            <Typography.Text type="secondary">{enseignant.email}</Typography.Text>
            {enseignant.actif ? (
              <Tag color="green">Actif</Tag>
            ) : (
              <Tag color="red">Désactivé</Tag>
            )}
          </Space>
        }
        extra={
          estAdmin && (
            <Space>
              <Button onClick={() => setEditionOuverte(true)}>Modifier</Button>
              <Button onClick={() => setMdpOuvert(true)}>Mot de passe</Button>
            </Space>
          )
        }
      >
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
            ...(estAdmin
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

        {estAdmin && (
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
                  options={(classesQuery.data ?? []).map((c) => ({ value: c.id, label: c.nom }))}
                />
              </Form.Item>
              <Form.Item name="matiere_id" rules={[{ required: true, message: "Matière." }]}>
                <Select
                  style={{ width: 240 }}
                  placeholder="Matière"
                  loading={matieresQuery.isLoading}
                  showSearch
                  optionFilterProp="label"
                  options={(matieresQuery.data ?? []).map((m) => ({ value: m.id, label: m.nom }))}
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
      </Card>

      <EnseignantFormModal
        open={editionOuverte}
        enseignant={enseignant}
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

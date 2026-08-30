import { ArrowLeftOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  App as AntApp,
  Button,
  Card,
  Divider,
  Form,
  InputNumber,
  Popconfirm,
  Result,
  Segmented,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { messageErreur } from "../../api/client";
import {
  declarerCoefficient,
  getCoefficients,
  getMatiere,
  getNiveaux,
  getSeries,
  retirerCoefficient,
} from "../../api/endpoints";
import type { Coefficient } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { MatiereFormModal } from "./MatiereFormModal";

export function MatiereDetailPage() {
  const { id } = useParams();
  const matiereId = Number(id);
  const navigate = useNavigate();
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  const { message } = AntApp.useApp();
  const qc = useQueryClient();

  const [editionOuverte, setEditionOuverte] = useState(false);
  const [portee, setPortee] = useState<"college" | "lycee">("college");
  const [form] = Form.useForm<{ cible: number; coefficient: number }>();

  const matiereQuery = useQuery({
    queryKey: ["matiere", matiereId],
    queryFn: () => getMatiere(matiereId),
    enabled: Number.isFinite(matiereId),
  });
  const coefficientsQuery = useQuery({
    queryKey: ["matiere", matiereId, "coefficients"],
    queryFn: () => getCoefficients(matiereId),
    enabled: Number.isFinite(matiereId),
  });
  const niveauxQuery = useQuery({ queryKey: ["niveaux"], queryFn: getNiveaux });
  const seriesQuery = useQuery({ queryKey: ["series"], queryFn: getSeries });

  const niveauxParId = useMemo(
    () => new Map((niveauxQuery.data ?? []).map((n) => [n.id, n])),
    [niveauxQuery.data],
  );
  const seriesParId = useMemo(
    () => new Map((seriesQuery.data ?? []).map((s) => [s.id, s])),
    [seriesQuery.data],
  );

  const declaration = useMutation({
    mutationFn: (v: { cible: number; coefficient: number }) =>
      declarerCoefficient(matiereId, {
        niveau_id: portee === "college" ? v.cible : null,
        serie_id: portee === "lycee" ? v.cible : null,
        coefficient: v.coefficient,
      }),
    onSuccess: () => {
      message.success("Coefficient enregistré.");
      qc.invalidateQueries({ queryKey: ["matiere", matiereId, "coefficients"] });
      qc.invalidateQueries({ queryKey: ["classes"] });
      form.resetFields();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  const retrait = useMutation({
    mutationFn: (coefId: number) => retirerCoefficient(matiereId, coefId),
    onSuccess: () => {
      message.success("Coefficient retiré.");
      qc.invalidateQueries({ queryKey: ["matiere", matiereId, "coefficients"] });
      qc.invalidateQueries({ queryKey: ["classes"] });
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  const matiere = matiereQuery.data;

  if (matiereQuery.isLoading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 5 }} />
      </Card>
    );
  }
  if (matiereQuery.isError || !matiere) {
    return (
      <Card>
        <Result
          status="404"
          title="Matière introuvable"
          extra={
            <Button type="primary" onClick={() => navigate("/matieres")}>
              Retour à la liste
            </Button>
          }
        />
      </Card>
    );
  }

  const portee_libelle = (c: Coefficient) =>
    c.niveau_id != null
      ? (niveauxParId.get(c.niveau_id)?.nom ?? `Niveau ${c.niveau_id}`)
      : c.serie_id != null
        ? `Série ${seriesParId.get(c.serie_id)?.nom ?? c.serie_id}`
        : "—";

  const ciblesCollege = (niveauxQuery.data ?? [])
    .filter((n) => n.cycle === "college")
    .map((n) => ({ value: n.id, label: n.nom }));
  const ciblesLycee = (seriesQuery.data ?? []).map((s) => ({ value: s.id, label: s.nom }));

  return (
    <Space orientation="vertical" size="middle" style={{ display: "flex" }}>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate("/matieres")}
        style={{ paddingInline: 0 }}
      >
        Matières
      </Button>

      <Card
        title={
          <Space size="middle" wrap>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {matiere.nom}
            </Typography.Title>
            {matiere.code && <Tag>{matiere.code}</Tag>}
            {matiere.note_directe && <Tag color="gold">Note directe</Tag>}
            {matiere.est_choix_langue && <Tag color="blue">Choix de langue</Tag>}
          </Space>
        }
        extra={estAdmin && <Button onClick={() => setEditionOuverte(true)}>Modifier</Button>}
      >
        <Typography.Title level={5} style={{ marginTop: 0 }}>
          Coefficients par niveau / série
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          Une matière sans coefficient déclaré pour un niveau (collège) ou une série (lycée)
          n'apparaît pas dans les classes de ce niveau/série.
        </Typography.Paragraph>

        <Table<Coefficient>
          rowKey="id"
          size="small"
          loading={coefficientsQuery.isLoading}
          dataSource={coefficientsQuery.data ?? []}
          pagination={false}
          columns={[
            { title: "Portée", key: "portee", render: (_: unknown, c) => portee_libelle(c) },
            { title: "Coefficient", dataIndex: "coefficient", width: 130, align: "center" },
            ...(estAdmin
              ? [
                  {
                    title: "",
                    key: "actions",
                    width: 100,
                    render: (_: unknown, c: Coefficient) => (
                      <Popconfirm
                        title="Retirer ce coefficient ?"
                        okText="Retirer"
                        cancelText="Annuler"
                        okButtonProps={{ danger: true }}
                        onConfirm={() => retrait.mutate(c.id)}
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
            <Typography.Text strong>Déclarer / modifier un coefficient</Typography.Text>
            <Form
              form={form}
              layout="inline"
              onFinish={(v) => declaration.mutate(v)}
              style={{ marginTop: 12, rowGap: 12 }}
            >
              <Form.Item label="Portée">
                <Segmented
                  value={portee}
                  onChange={(v) => {
                    setPortee(v as "college" | "lycee");
                    form.setFieldValue("cible", undefined);
                  }}
                  options={[
                    { label: "Collège (niveau)", value: "college" },
                    { label: "Lycée (série)", value: "lycee" },
                  ]}
                />
              </Form.Item>
              <Form.Item name="cible" rules={[{ required: true, message: "Choisir." }]}>
                <Select
                  style={{ width: 200 }}
                  placeholder={portee === "college" ? "Niveau" : "Série"}
                  options={portee === "college" ? ciblesCollege : ciblesLycee}
                />
              </Form.Item>
              <Form.Item
                name="coefficient"
                rules={[{ required: true, message: "Coefficient." }]}
              >
                <InputNumber min={0.5} max={20} step={0.5} placeholder="Coef." />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={declaration.isPending}>
                  Enregistrer
                </Button>
              </Form.Item>
            </Form>
          </>
        )}
      </Card>

      <MatiereFormModal
        open={editionOuverte}
        matiere={matiere}
        onClose={() => setEditionOuverte(false)}
      />
    </Space>
  );
}

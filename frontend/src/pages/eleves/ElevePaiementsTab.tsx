import { FileTextOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  App as AntApp,
  Button,
  Card,
  DatePicker,
  Empty,
  Form,
  InputNumber,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Skeleton,
  Space,
  Statistic,
  Table,
  Tag,
  theme,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { messageErreur } from "../../api/client";
import { annulerPaiement, enregistrerPaiement, getSituationPaiements } from "../../api/endpoints";
import type { ModePaiement, Paiement, SituationPaiements, SituationTranche } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { fcfa, MODES, STATUT } from "../paiements/format";
import { RecuModal } from "../paiements/RecuModal";

export function ElevePaiementsTab({ eleveId }: { eleveId: number }) {
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const [encaissement, setEncaissement] = useState<{ trancheId?: number } | null>(null);
  const [recuId, setRecuId] = useState<number | null>(null);

  const query = useQuery({
    queryKey: ["paiements", eleveId],
    queryFn: () => getSituationPaiements(eleveId),
    enabled: estAdmin,
  });

  const invalider = () => {
    qc.invalidateQueries({ queryKey: ["paiements", eleveId] });
    qc.invalidateQueries({ queryKey: ["suivi-paiements"] });
    qc.invalidateQueries({ queryKey: ["tranches"] });
  };

  const annulation = useMutation({
    mutationFn: (id: number) => annulerPaiement(eleveId, id),
    onSuccess: () => {
      message.success("Paiement annulé.");
      invalider();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  if (!estAdmin) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="Les paiements ne sont consultables que par l'administration de l'école."
      />
    );
  }
  if (query.isLoading || !query.data) return <Skeleton active paragraph={{ rows: 8 }} />;

  const s = query.data;
  if (s.tranches.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={`Aucune tranche de paiement n'est configurée${s.annee_libelle ? ` pour ${s.annee_libelle}` : ""}.`}
      >
        <Button type="primary" onClick={() => navigate("/paiements?onglet=tranches")}>
          Configurer les tranches
        </Button>
      </Empty>
    );
  }

  const pourcentage = s.total_du > 0 ? Math.round((s.total_paye / s.total_du) * 100) : 0;
  const statut = STATUT[s.statut];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      {/* Synthèse */}
      <Card size="small">
        <Space size={48} wrap align="start">
          <Statistic title={`Frais de scolarité ${s.annee_libelle ?? ""}`} value={fcfa(s.total_du)} />
          <Statistic title="Versé" value={fcfa(s.total_paye)} />
          <Statistic
            title="Reste à payer"
            value={fcfa(s.reste)}
            valueStyle={s.statut === "en_retard" ? { color: token.colorError } : undefined}
          />
          <div style={{ minWidth: 220 }}>
            <Typography.Text type="secondary">Situation</Typography.Text>
            <div style={{ marginTop: 4 }}>
              <Tag color={statut.couleur}>{statut.texte}</Tag>
            </div>
            <Progress
              percent={pourcentage}
              size="small"
              status={s.statut === "en_retard" ? "exception" : s.statut === "solde" ? "success" : "normal"}
            />
          </div>
        </Space>
      </Card>

      {/* Tranches */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <Typography.Title level={5} style={{ margin: 0 }}>
            Tranches
          </Typography.Title>
          {s.reste > 0 && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setEncaissement({})}>
              Enregistrer un paiement
            </Button>
          )}
        </div>
        <Table<SituationTranche>
          rowKey="tranche_id"
          size="small"
          pagination={false}
          dataSource={s.tranches}
          columns={[
            { title: "Tranche", dataIndex: "libelle" },
            {
              title: "Date limite",
              dataIndex: "date_limite",
              width: 120,
              render: (d: string | null) => (d ? dayjs(d).format("DD/MM/YYYY") : "—"),
            },
            { title: "Montant", dataIndex: "montant", align: "right", render: fcfa },
            { title: "Versé", dataIndex: "paye", align: "right", render: fcfa },
            {
              title: "Reste",
              dataIndex: "reste",
              align: "right",
              render: (v: number) => (v > 0 ? <strong>{fcfa(v)}</strong> : fcfa(0)),
            },
            {
              title: "Statut",
              dataIndex: "statut",
              width: 110,
              render: (st: SituationTranche["statut"]) => <Tag color={STATUT[st].couleur}>{STATUT[st].texte}</Tag>,
            },
            {
              title: "",
              key: "action",
              width: 110,
              render: (_: unknown, t: SituationTranche) =>
                t.reste > 0 && (
                  <Button size="small" onClick={() => setEncaissement({ trancheId: t.tranche_id })}>
                    Encaisser
                  </Button>
                ),
            },
          ]}
        />
      </div>

      {/* Historique */}
      <div>
        <Typography.Title level={5} style={{ marginTop: 0 }}>
          Historique des paiements
        </Typography.Title>
        <Table<Paiement>
          rowKey="id"
          size="small"
          dataSource={s.paiements}
          locale={{ emptyText: "Aucun paiement enregistré." }}
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          columns={[
            {
              title: "Date",
              dataIndex: "date_paiement",
              width: 110,
              render: (d: string) => dayjs(d).format("DD/MM/YYYY"),
            },
            {
              title: "N° reçu",
              dataIndex: "numero_recu",
              width: 120,
              render: (n: string) => <Typography.Text code>{n}</Typography.Text>,
            },
            { title: "Tranche", dataIndex: "tranche_libelle" },
            {
              title: "Mode",
              dataIndex: "mode_paiement",
              render: (m: ModePaiement | null) => (m ? MODES[m] : "—"),
            },
            { title: "Montant", dataIndex: "montant_paye", align: "right", render: fcfa },
            { title: "Enregistré par", dataIndex: "enregistre_par_nom", render: (n) => n ?? "—" },
            {
              title: "",
              key: "actions",
              width: 190,
              render: (_: unknown, p: Paiement) => (
                <Space>
                  <Button size="small" icon={<FileTextOutlined />} onClick={() => setRecuId(p.id)}>
                    Reçu
                  </Button>
                  <Popconfirm
                    title="Annuler ce paiement ?"
                    description={`Le reçu ${p.numero_recu} ne sera plus valable.`}
                    okText="Annuler le paiement"
                    okButtonProps={{ danger: true }}
                    cancelText="Non"
                    onConfirm={() => annulation.mutate(p.id)}
                  >
                    <Button size="small" danger>
                      Annuler
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </div>

      <PaiementModal
        eleveId={eleveId}
        situation={s}
        ouvert={encaissement}
        onClose={() => setEncaissement(null)}
        onEnregistre={(p) => {
          setEncaissement(null);
          invalider();
          message.success(`Paiement enregistré — reçu ${p.numero_recu}.`);
          setRecuId(p.id);
        }}
      />
      <RecuModal paiementId={recuId} onClose={() => setRecuId(null)} />
    </Space>
  );
}

// ---------- Saisie d'un paiement ----------

interface Valeurs {
  tranche_id: number;
  montant_paye: number;
  date_paiement: dayjs.Dayjs;
  mode_paiement: ModePaiement;
}

function PaiementModal({
  eleveId,
  situation,
  ouvert,
  onClose,
  onEnregistre,
}: {
  eleveId: number;
  situation: SituationPaiements;
  ouvert: { trancheId?: number } | null;
  onClose: () => void;
  onEnregistre: (p: Paiement) => void;
}) {
  const { message } = AntApp.useApp();
  const [form] = Form.useForm<Valeurs>();
  const ouvertes = situation.tranches.filter((t) => t.reste > 0);
  const trancheId = Form.useWatch("tranche_id", form);
  const tranche = ouvertes.find((t) => t.tranche_id === trancheId);

  const mutation = useMutation({
    mutationFn: (v: Valeurs) =>
      enregistrerPaiement(eleveId, {
        tranche_id: v.tranche_id,
        montant_paye: v.montant_paye,
        date_paiement: v.date_paiement.format("YYYY-MM-DD"),
        mode_paiement: v.mode_paiement,
      }),
    onSuccess: onEnregistre,
    onError: (e) => message.error(messageErreur(e)),
  });

  // Par défaut : la tranche demandée, sinon la première non soldée, pour son reste.
  const initiale = ouvertes.find((t) => t.tranche_id === ouvert?.trancheId) ?? ouvertes[0];

  return (
    <Modal
      open={ouvert !== null}
      title="Enregistrer un paiement"
      onCancel={onClose}
      okText="Enregistrer"
      cancelText="Annuler"
      confirmLoading={mutation.isPending}
      onOk={() => form.submit()}
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        preserve={false}
        onFinish={(v) => mutation.mutate(v)}
        initialValues={{
          tranche_id: initiale?.tranche_id,
          montant_paye: initiale?.reste,
          date_paiement: dayjs(),
          mode_paiement: "especes",
        }}
      >
        <Form.Item name="tranche_id" label="Tranche" rules={[{ required: true, message: "Choisissez une tranche." }]}>
          <Select
            options={ouvertes.map((t) => ({
              value: t.tranche_id,
              label: `${t.libelle} — reste ${fcfa(t.reste)}`,
            }))}
            onChange={(id) => {
              const t = ouvertes.find((x) => x.tranche_id === id);
              if (t) form.setFieldValue("montant_paye", t.reste);
            }}
          />
        </Form.Item>
        <Form.Item
          name="montant_paye"
          label="Montant versé (FCFA)"
          extra={tranche && tranche.paye > 0 ? `Déjà versé sur cette tranche : ${fcfa(tranche.paye)}` : undefined}
          rules={[
            { required: true, message: "Indiquez le montant." },
            {
              validator: (_, v: number | null) =>
                v == null || (v > 0 && (!tranche || v <= tranche.reste))
                  ? Promise.resolve()
                  : Promise.reject(new Error(tranche ? `Entre 1 et ${fcfa(tranche.reste)}.` : "Montant invalide.")),
            },
          ]}
        >
          <InputNumber<number>
            style={{ width: "100%" }}
            min={1}
            step={5000}
            formatter={(v) => `${v ?? ""}`.replace(/\B(?=(\d{3})+(?!\d))/g, " ")}
            parser={(v) => Number((v ?? "").replace(/\s/g, ""))}
          />
        </Form.Item>
        <Space size="middle" style={{ display: "flex" }} align="start">
          <Form.Item name="date_paiement" label="Date du paiement" rules={[{ required: true, message: "Date." }]}>
            <DatePicker format="DD/MM/YYYY" disabledDate={(d) => d.isAfter(dayjs(), "day")} />
          </Form.Item>
          <Form.Item name="mode_paiement" label="Mode de paiement">
            <Select
              style={{ width: 180 }}
              options={Object.entries(MODES).map(([value, label]) => ({ value, label }))}
            />
          </Form.Item>
        </Space>
      </Form>
    </Modal>
  );
}

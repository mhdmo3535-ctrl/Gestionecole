import { PlusOutlined, SearchOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App as AntApp,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  theme,
  Tooltip,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { messageErreur } from "../api/client";
import {
  creerTranche,
  getAnneesScolaires,
  getClasses,
  getSuiviPaiements,
  getTranches,
  modifierTranche,
  supprimerTranche,
} from "../api/endpoints";
import type { StatutPaiementEleve, SuiviLigne, Tranche } from "../api/types";
import { fcfa, STATUT } from "./paiements/format";

export function PaiementsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const onglet = searchParams.get("onglet") === "tranches" ? "tranches" : "suivi";
  const [anneeId, setAnneeId] = useState<number | undefined>(undefined);

  const anneesQuery = useQuery({ queryKey: ["annees-scolaires"], queryFn: getAnneesScolaires });
  const anneeEffective = anneeId ?? anneesQuery.data?.find((a) => a.active)?.id;
  const allerA = (cle: string) => setSearchParams(cle === "suivi" ? {} : { onglet: cle }, { replace: true });

  return (
    <Card
      title="Paiements"
      extra={
        <Select
          style={{ width: 180 }}
          value={anneeEffective}
          onChange={setAnneeId}
          loading={anneesQuery.isLoading}
          options={(anneesQuery.data ?? []).map((a) => ({
            value: a.id,
            label: a.active ? `${a.libelle} (active)` : a.libelle,
          }))}
        />
      }
    >
      <Tabs
        activeKey={onglet}
        onChange={allerA}
        items={[
          {
            key: "suivi",
            label: "Suivi des paiements",
            children: anneeEffective && <Suivi anneeId={anneeEffective} onConfigurer={() => allerA("tranches")} />,
          },
          {
            key: "tranches",
            label: "Tranches",
            children: anneeEffective && <Tranches anneeId={anneeEffective} />,
          },
        ]}
      />
    </Card>
  );
}

// ---------- Suivi ----------

const FILTRES_STATUT: { value: StatutPaiementEleve | "tous"; label: string }[] = [
  { value: "tous", label: "Tous les statuts" },
  { value: "en_retard", label: "En retard" },
  { value: "partiel", label: "Partiel" },
  { value: "non_paye", label: "Non payé" },
  { value: "solde", label: "Soldé" },
];

function Suivi({ anneeId, onConfigurer }: { anneeId: number; onConfigurer: () => void }) {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const [classeId, setClasseId] = useState<number | undefined>(undefined);
  const [statut, setStatut] = useState<StatutPaiementEleve | "tous">("tous");
  const [recherche, setRecherche] = useState("");

  const classesQuery = useQuery({
    queryKey: ["classes", { annee: anneeId }],
    queryFn: () => getClasses({ annee_scolaire_id: anneeId }),
  });
  const query = useQuery({
    queryKey: ["suivi-paiements", anneeId, classeId],
    queryFn: () => getSuiviPaiements({ annee_scolaire_id: anneeId, classe_id: classeId }),
  });

  const lignes = useMemo(() => {
    const q = recherche.trim().toLowerCase();
    return (query.data?.lignes ?? []).filter(
      (l) =>
        (statut === "tous" || l.statut === statut) &&
        (!q || `${l.nom} ${l.prenom} ${l.matricule}`.toLowerCase().includes(q)),
    );
  }, [query.data, statut, recherche]);

  const s = query.data;
  if (s && s.nb_tranches === 0) {
    return (
      <Alert
        type="info"
        showIcon
        message={`Aucune tranche configurée pour ${s.annee_libelle}`}
        description="Définissez d'abord les tranches (montants et dates limites) pour suivre les paiements des élèves."
        action={
          <Button type="primary" onClick={onConfigurer}>
            Configurer les tranches
          </Button>
        }
      />
    );
  }

  const taux = s && s.total_attendu > 0 ? Math.round((s.total_encaisse / s.total_attendu) * 100) : 0;

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" loading={query.isLoading}>
            <Statistic title="Montant attendu" value={s ? fcfa(s.total_attendu) : ""} />
            <Typography.Text type="secondary">{s?.nb_eleves ?? 0} élèves</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" loading={query.isLoading}>
            <Statistic title="Encaissé" value={s ? fcfa(s.total_encaisse) : ""} />
            <Progress percent={taux} size="small" />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" loading={query.isLoading}>
            <Statistic title="Reste à recouvrer" value={s ? fcfa(s.reste) : ""} />
            <Typography.Text type="secondary">{s?.nb_soldes ?? 0} élèves ont soldé</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" loading={query.isLoading}>
            <Statistic
              title="Élèves en retard"
              value={s?.nb_en_retard ?? 0}
              suffix={s ? `/ ${s.nb_eleves}` : undefined}
              valueStyle={s && s.nb_en_retard > 0 ? { color: token.colorError } : undefined}
            />
            {s && s.nb_en_retard > 0 && (
              <Button type="link" size="small" style={{ padding: 0 }} onClick={() => setStatut("en_retard")}>
                Voir la liste
              </Button>
            )}
          </Card>
        </Col>
      </Row>

      <Space wrap>
        <Select
          style={{ width: 200 }}
          allowClear
          placeholder="Toutes les classes"
          value={classeId}
          onChange={setClasseId}
          loading={classesQuery.isLoading}
          options={(classesQuery.data ?? []).map((c) => ({ value: c.id, label: c.nom }))}
        />
        <Select style={{ width: 180 }} value={statut} onChange={setStatut} options={FILTRES_STATUT} />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Nom ou matricule"
          style={{ width: 220 }}
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
        />
      </Space>

      <Table<SuiviLigne>
        rowKey="eleve_id"
        size="middle"
        loading={query.isLoading}
        dataSource={lignes}
        locale={{ emptyText: "Aucun élève ne correspond." }}
        pagination={{ pageSize: 25, hideOnSinglePage: true, showTotal: (n) => `${n} élèves` }}
        onRow={(l) => ({
          onClick: () => navigate(`/eleves/${l.eleve_id}?onglet=paiements`),
          style: { cursor: "pointer" },
        })}
        columns={[
          { title: "Matricule", dataIndex: "matricule", width: 120 },
          {
            title: "Élève",
            key: "nom",
            sorter: (a, b) => `${a.nom} ${a.prenom}`.localeCompare(`${b.nom} ${b.prenom}`),
            render: (_: unknown, l) => `${l.nom} ${l.prenom}`,
          },
          { title: "Classe", dataIndex: "classe_nom", width: 100 },
          {
            title: "Versé",
            dataIndex: "total_paye",
            align: "right",
            sorter: (a, b) => a.total_paye - b.total_paye,
            render: fcfa,
          },
          {
            title: "Reste",
            dataIndex: "reste",
            align: "right",
            sorter: (a, b) => a.reste - b.reste,
            render: (v: number) => (v > 0 ? <strong>{fcfa(v)}</strong> : fcfa(0)),
          },
          {
            title: "Progression",
            key: "progression",
            width: 150,
            render: (_: unknown, l) => (
              <Progress
                percent={l.total_du > 0 ? Math.round((l.total_paye / l.total_du) * 100) : 0}
                size="small"
                status={l.statut === "en_retard" ? "exception" : l.statut === "solde" ? "success" : "normal"}
              />
            ),
          },
          {
            title: "Statut",
            dataIndex: "statut",
            width: 110,
            render: (st: StatutPaiementEleve) => <Tag color={STATUT[st].couleur}>{STATUT[st].texte}</Tag>,
          },
          {
            title: "Dernier paiement",
            dataIndex: "dernier_paiement",
            width: 140,
            render: (d: string | null) => (d ? dayjs(d).format("DD/MM/YYYY") : "—"),
          },
        ]}
      />
    </Space>
  );
}

// ---------- Tranches ----------

interface ValeursTranche {
  libelle?: string;
  montant: number;
  date_limite?: dayjs.Dayjs | null;
}

function Tranches({ anneeId }: { anneeId: number }) {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm<ValeursTranche>();
  const [modal, setModal] = useState<{ tranche: Tranche | null } | null>(null);

  const query = useQuery({ queryKey: ["tranches", anneeId], queryFn: () => getTranches(anneeId) });
  const tranches = query.data ?? [];
  const total = tranches.reduce((acc, t) => acc + t.montant, 0);

  const invalider = () => {
    qc.invalidateQueries({ queryKey: ["tranches"] });
    qc.invalidateQueries({ queryKey: ["suivi-paiements"] });
    qc.invalidateQueries({ queryKey: ["paiements"] });
  };

  const enregistrement = useMutation({
    mutationFn: (v: ValeursTranche) => {
      const payload = {
        libelle: v.libelle?.trim() || null,
        montant: v.montant,
        date_limite: v.date_limite ? v.date_limite.format("YYYY-MM-DD") : null,
      };
      return modal?.tranche
        ? modifierTranche(modal.tranche.id, payload)
        : creerTranche({ ...payload, annee_scolaire_id: anneeId });
    },
    onSuccess: () => {
      message.success(modal?.tranche ? "Tranche modifiée." : "Tranche ajoutée.");
      setModal(null);
      invalider();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  const suppression = useMutation({
    mutationFn: (id: number) => supprimerTranche(id),
    onSuccess: () => {
      message.success("Tranche supprimée.");
      invalider();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
        <Typography.Text type="secondary">
          Les tranches s'appliquent à tous les élèves de l'année. Total annuel par élève :{" "}
          <Typography.Text strong>{fcfa(total)}</Typography.Text>
        </Typography.Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModal({ tranche: null })}>
          Ajouter une tranche
        </Button>
      </div>

      <Table<Tranche>
        rowKey="id"
        loading={query.isLoading}
        dataSource={tranches}
        pagination={false}
        locale={{ emptyText: "Aucune tranche. Ajoutez la 1re tranche des frais de scolarité." }}
        columns={[
          { title: "N°", dataIndex: "numero", width: 60, align: "center" },
          { title: "Libellé", dataIndex: "libelle" },
          { title: "Montant", dataIndex: "montant", align: "right", render: fcfa },
          {
            title: "Date limite",
            dataIndex: "date_limite",
            render: (d: string | null) => (d ? dayjs(d).format("DD/MM/YYYY") : "—"),
          },
          { title: "Paiements reçus", dataIndex: "nb_paiements", align: "center", width: 150 },
          {
            title: "",
            key: "actions",
            width: 180,
            render: (_: unknown, t) => (
              <Space>
                <Button size="small" onClick={() => setModal({ tranche: t })}>
                  Modifier
                </Button>
                {t.nb_paiements > 0 ? (
                  <Tooltip title="Des paiements sont enregistrés sur cette tranche.">
                    <Button size="small" danger disabled>
                      Supprimer
                    </Button>
                  </Tooltip>
                ) : (
                  <Popconfirm
                    title="Supprimer cette tranche ?"
                    okText="Supprimer"
                    cancelText="Annuler"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => suppression.mutate(t.id)}
                  >
                    <Button size="small" danger>
                      Supprimer
                    </Button>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />

      <Modal
        open={modal !== null}
        title={modal?.tranche ? `Modifier — ${modal.tranche.libelle}` : "Nouvelle tranche"}
        okText="Enregistrer"
        cancelText="Annuler"
        confirmLoading={enregistrement.isPending}
        onCancel={() => setModal(null)}
        onOk={() => form.submit()}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          preserve={false}
          onFinish={(v) => enregistrement.mutate(v)}
          initialValues={
            modal?.tranche
              ? {
                  libelle: modal.tranche.libelle,
                  montant: modal.tranche.montant,
                  date_limite: modal.tranche.date_limite ? dayjs(modal.tranche.date_limite) : null,
                }
              : undefined
          }
        >
          <Form.Item name="libelle" label="Libellé" extra="Laissez vide pour « 1re tranche », « 2e tranche »…">
            <Input maxLength={50} placeholder={`${tranches.length + 1}${tranches.length === 0 ? "re" : "e"} tranche`} />
          </Form.Item>
          <Form.Item
            name="montant"
            label="Montant (FCFA)"
            rules={[{ required: true, message: "Indiquez le montant." }]}
          >
            <InputNumber<number>
              style={{ width: "100%" }}
              min={1}
              step={5000}
              formatter={(v) => `${v ?? ""}`.replace(/\B(?=(\d{3})+(?!\d))/g, " ")}
              parser={(v) => Number((v ?? "").replace(/\s/g, ""))}
            />
          </Form.Item>
          <Form.Item name="date_limite" label="Date limite de paiement">
            <DatePicker format="DD/MM/YYYY" style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

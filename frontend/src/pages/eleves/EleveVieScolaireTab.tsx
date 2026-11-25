import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App as AntApp,
  Button,
  Checkbox,
  DatePicker,
  Form,
  Input,
  Popconfirm,
  Select,
  Skeleton,
  Space,
  Table,
  Tabs,
  Tag,
} from "antd";
import dayjs from "dayjs";
import { messageErreur } from "../../api/client";
import {
  ajouterAbsence,
  ajouterDiscipline,
  ajouterPermission,
  getAbsences,
  getDiscipline,
  getPermissions,
  retirerAbsence,
  retirerDiscipline,
  retirerPermission,
  traiterPermission,
} from "../../api/endpoints";
import type { Absence, Discipline, Permission } from "../../api/types";
import { useDroits } from "../../auth/droits";

const { RangePicker } = DatePicker;

const GRAVITE: Record<string, { texte: string; couleur: string }> = {
  mineure: { texte: "Mineure", couleur: "gold" },
  moyenne: { texte: "Moyenne", couleur: "orange" },
  grave: { texte: "Grave", couleur: "red" },
};
const STATUT_PERM: Record<string, { texte: string; couleur: string }> = {
  en_attente: { texte: "En attente", couleur: "gold" },
  approuve: { texte: "Approuvée", couleur: "green" },
  rejete: { texte: "Rejetée", couleur: "red" },
};

function useVieScolaire(eleveId: number) {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const inval = (quoi: string) =>
    qc.invalidateQueries({ queryKey: ["vie-scolaire", eleveId, quoi] });
  const onError = (e: unknown) => message.error(messageErreur(e));
  return { message, inval, onError };
}

// ---------- Absences ----------

function SectionAbsences({ eleveId }: { eleveId: number }) {
  const ecriture = useDroits().peut("vie_scolaire", true);
  const { message, inval, onError } = useVieScolaire(eleveId);
  const [form] = Form.useForm();
  const query = useQuery({
    queryKey: ["vie-scolaire", eleveId, "absences"],
    queryFn: () => getAbsences(eleveId),
  });
  const ajout = useMutation({
    mutationFn: (v: { jour: dayjs.Dayjs; type: "absence" | "retard"; justifiee?: boolean }) =>
      ajouterAbsence(eleveId, {
        date: v.jour.format("YYYY-MM-DD"),
        type: v.type,
        justifiee: !!v.justifiee,
      }),
    onSuccess: () => {
      message.success("Enregistré.");
      inval("absences");
      form.resetFields();
    },
    onError,
  });
  const suppr = useMutation({
    mutationFn: (id: number) => retirerAbsence(eleveId, id),
    onSuccess: () => inval("absences"),
    onError,
  });

  return (
    <>
      {ecriture && (
        <Form
          form={form}
          layout="inline"
          onFinish={(v) => ajout.mutate(v)}
          style={{ marginBottom: 16, rowGap: 12 }}
        >
          <Form.Item name="jour" rules={[{ required: true, message: "Date." }]}>
            <DatePicker format="DD/MM/YYYY" placeholder="Date" />
          </Form.Item>
          <Form.Item name="type" initialValue="absence">
            <Select
              style={{ width: 130 }}
              options={[
                { value: "absence", label: "Absence" },
                { value: "retard", label: "Retard" },
              ]}
            />
          </Form.Item>
          <Form.Item name="justifiee" valuePropName="checked">
            <Checkbox>Justifiée</Checkbox>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={ajout.isPending}>
              Ajouter
            </Button>
          </Form.Item>
        </Form>
      )}
      {query.isLoading ? (
        <Skeleton active />
      ) : (
        <Table<Absence>
          rowKey="id"
          size="small"
          dataSource={query.data ?? []}
          pagination={{ pageSize: 15, hideOnSinglePage: true }}
          columns={[
            {
              title: "Date",
              dataIndex: "date",
              width: 130,
              render: (d: string) => dayjs(d).format("DD/MM/YYYY"),
            },
            {
              title: "Type",
              dataIndex: "type",
              width: 110,
              render: (t: string) => (t === "retard" ? "Retard" : "Absence"),
            },
            {
              title: "Justifiée",
              dataIndex: "justifiee",
              width: 110,
              render: (j: boolean) =>
                j ? <Tag color="green">Oui</Tag> : <Tag color="red">Non</Tag>,
            },
            ...(ecriture
              ? [
                  {
                    title: "",
                    key: "x",
                    width: 90,
                    render: (_: unknown, a: Absence) => (
                      <Popconfirm
                        title="Supprimer ?"
                        okText="Oui"
                        cancelText="Non"
                        onConfirm={() => suppr.mutate(a.id)}
                      >
                        <Button size="small" danger>
                          Supprimer
                        </Button>
                      </Popconfirm>
                    ),
                  },
                ]
              : []),
          ]}
        />
      )}
    </>
  );
}

// ---------- Discipline ----------

function SectionDiscipline({ eleveId }: { eleveId: number }) {
  const ecriture = useDroits().peut("vie_scolaire", true);
  const { message, inval, onError } = useVieScolaire(eleveId);
  const [form] = Form.useForm();
  const query = useQuery({
    queryKey: ["vie-scolaire", eleveId, "discipline"],
    queryFn: () => getDiscipline(eleveId),
  });
  const ajout = useMutation({
    mutationFn: (v: {
      jour?: dayjs.Dayjs;
      description: string;
      gravite: "mineure" | "moyenne" | "grave";
      sanction?: string;
    }) =>
      ajouterDiscipline(eleveId, {
        date: v.jour ? v.jour.format("YYYY-MM-DD") : null,
        description: v.description,
        gravite: v.gravite,
        sanction: v.sanction || null,
      }),
    onSuccess: () => {
      message.success("Enregistré.");
      inval("discipline");
      form.resetFields();
    },
    onError,
  });
  const suppr = useMutation({
    mutationFn: (id: number) => retirerDiscipline(eleveId, id),
    onSuccess: () => inval("discipline"),
    onError,
  });

  return (
    <>
      {ecriture && (
        <Form
          form={form}
          layout="vertical"
          onFinish={(v) => ajout.mutate(v)}
          style={{ marginBottom: 16, maxWidth: 640 }}
        >
          <Space align="start" wrap>
            <Form.Item name="jour" label="Date">
              <DatePicker format="DD/MM/YYYY" placeholder="Aujourd'hui" />
            </Form.Item>
            <Form.Item name="gravite" label="Gravité" initialValue="mineure">
              <Select
                style={{ width: 140 }}
                options={[
                  { value: "mineure", label: "Mineure" },
                  { value: "moyenne", label: "Moyenne" },
                  { value: "grave", label: "Grave" },
                ]}
              />
            </Form.Item>
          </Space>
          <Form.Item
            name="description"
            label="Description"
            rules={[{ required: true, message: "Requis." }]}
          >
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="sanction" label="Sanction (optionnel)">
            <Input />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={ajout.isPending}>
            Ajouter
          </Button>
        </Form>
      )}
      {query.isLoading ? (
        <Skeleton active />
      ) : (
        <Table<Discipline>
          rowKey="id"
          size="small"
          dataSource={query.data ?? []}
          pagination={{ pageSize: 15, hideOnSinglePage: true }}
          columns={[
            {
              title: "Date",
              dataIndex: "date",
              width: 120,
              render: (d: string) => dayjs(d).format("DD/MM/YYYY"),
            },
            {
              title: "Gravité",
              dataIndex: "gravite",
              width: 110,
              render: (g: string) => <Tag color={GRAVITE[g].couleur}>{GRAVITE[g].texte}</Tag>,
            },
            { title: "Description", dataIndex: "description" },
            { title: "Sanction", dataIndex: "sanction", render: (s: string | null) => s ?? "—" },
            ...(ecriture
              ? [
                  {
                    title: "",
                    key: "x",
                    width: 90,
                    render: (_: unknown, f: Discipline) => (
                      <Popconfirm
                        title="Supprimer ?"
                        okText="Oui"
                        cancelText="Non"
                        onConfirm={() => suppr.mutate(f.id)}
                      >
                        <Button size="small" danger>
                          Supprimer
                        </Button>
                      </Popconfirm>
                    ),
                  },
                ]
              : []),
          ]}
        />
      )}
    </>
  );
}

// ---------- Permissions d'absence ----------

function SectionPermissions({ eleveId }: { eleveId: number }) {
  const ecriture = useDroits().peut("vie_scolaire", true);
  const { message, inval, onError } = useVieScolaire(eleveId);
  const [form] = Form.useForm();
  const query = useQuery({
    queryKey: ["vie-scolaire", eleveId, "permissions"],
    queryFn: () => getPermissions(eleveId),
  });
  const ajout = useMutation({
    mutationFn: (v: { periode: [dayjs.Dayjs, dayjs.Dayjs]; motif: string }) =>
      ajouterPermission(eleveId, {
        date_debut: v.periode[0].format("YYYY-MM-DD"),
        date_fin: v.periode[1].format("YYYY-MM-DD"),
        motif: v.motif,
      }),
    onSuccess: () => {
      message.success("Demande enregistrée.");
      inval("permissions");
      form.resetFields();
    },
    onError,
  });
  const traiter = useMutation({
    mutationFn: ({ id, statut }: { id: number; statut: "approuve" | "rejete" }) =>
      traiterPermission(eleveId, id, { statut }),
    onSuccess: () => {
      message.success("Demande traitée.");
      inval("permissions");
    },
    onError,
  });
  const suppr = useMutation({
    mutationFn: (id: number) => retirerPermission(eleveId, id),
    onSuccess: () => inval("permissions"),
    onError,
  });

  return (
    <>
      {ecriture && (
        <Form
          form={form}
          layout="inline"
          onFinish={(v) => ajout.mutate(v)}
          style={{ marginBottom: 16, rowGap: 12 }}
        >
          <Form.Item name="periode" rules={[{ required: true, message: "Période." }]}>
            <RangePicker format="DD/MM/YYYY" />
          </Form.Item>
          <Form.Item name="motif" rules={[{ required: true, message: "Motif." }]}>
            <Input placeholder="Motif" style={{ width: 260 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={ajout.isPending}>
              Ajouter
            </Button>
          </Form.Item>
        </Form>
      )}
      {query.isLoading ? (
        <Skeleton active />
      ) : (
        <Table<Permission>
          rowKey="id"
          size="small"
          dataSource={query.data ?? []}
          pagination={{ pageSize: 15, hideOnSinglePage: true }}
          columns={[
            {
              title: "Période",
              key: "periode",
              width: 200,
              render: (_: unknown, p) =>
                `${dayjs(p.date_debut).format("DD/MM/YYYY")} → ${dayjs(p.date_fin).format("DD/MM/YYYY")}`,
            },
            { title: "Motif", dataIndex: "motif" },
            {
              title: "Statut",
              dataIndex: "statut",
              width: 120,
              render: (s: string) => (
                <Tag color={STATUT_PERM[s].couleur}>{STATUT_PERM[s].texte}</Tag>
              ),
            },
            ...(ecriture
              ? [
                  {
                    title: "",
                    key: "x",
                    width: 230,
                    render: (_: unknown, p: Permission) => (
                      <Space>
                        {p.statut === "en_attente" && (
                          <>
                            <Button
                              size="small"
                              type="primary"
                              onClick={() => traiter.mutate({ id: p.id, statut: "approuve" })}
                            >
                              Approuver
                            </Button>
                            <Button
                              size="small"
                              danger
                              onClick={() => traiter.mutate({ id: p.id, statut: "rejete" })}
                            >
                              Rejeter
                            </Button>
                          </>
                        )}
                        <Popconfirm
                          title="Supprimer ?"
                          okText="Oui"
                          cancelText="Non"
                          onConfirm={() => suppr.mutate(p.id)}
                        >
                          <Button size="small">Supprimer</Button>
                        </Popconfirm>
                      </Space>
                    ),
                  },
                ]
              : []),
          ]}
        />
      )}
    </>
  );
}

export function EleveVieScolaireTab({ eleveId }: { eleveId: number }) {
  const { peut } = useDroits();
  if (!peut("vie_scolaire")) {
    return (
      <Alert
        type="info"
        showIcon
        message="Accès réservé"
        description="Le suivi de vie scolaire (absences, discipline, permissions) est géré par le surveillant général."
      />
    );
  }
  return (
    <Tabs
      defaultActiveKey="absences"
      items={[
        { key: "absences", label: "Absences", children: <SectionAbsences eleveId={eleveId} /> },
        {
          key: "discipline",
          label: "Discipline",
          children: <SectionDiscipline eleveId={eleveId} />,
        },
        {
          key: "permissions",
          label: "Permissions d'absence",
          children: <SectionPermissions eleveId={eleveId} />,
        },
      ]}
    />
  );
}

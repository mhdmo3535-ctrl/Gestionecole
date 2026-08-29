import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  App as AntApp,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
} from "antd";
import { useMemo, useState } from "react";
import { messageErreur } from "../api/client";
import {
  creerEleve,
  getClasses,
  getEleves,
  modifierEleve,
  type ElevePayload,
} from "../api/endpoints";
import type { Eleve } from "../api/types";
import { useAuth } from "../auth/AuthContext";

const STATUT_COULEUR: Record<Eleve["statut"], string> = {
  actif: "green",
  redoublant: "orange",
  archive: "default",
};

export function ElevesPage() {
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  const { message } = AntApp.useApp();
  const qc = useQueryClient();

  const [recherche, setRecherche] = useState("");
  const [modalOuvert, setModalOuvert] = useState(false);
  const [enEdition, setEnEdition] = useState<Eleve | null>(null);
  const [form] = Form.useForm<ElevePayload>();

  const classesQuery = useQuery({ queryKey: ["classes"], queryFn: () => getClasses() });
  const elevesQuery = useQuery({
    queryKey: ["eleves", recherche],
    queryFn: () => getEleves(recherche ? { q: recherche } : undefined),
  });

  const classesParId = useMemo(
    () => new Map((classesQuery.data ?? []).map((c) => [c.id, c])),
    [classesQuery.data],
  );

  const mutation = useMutation({
    mutationFn: (valeurs: ElevePayload) =>
      enEdition ? modifierEleve(enEdition.id, valeurs) : creerEleve(valeurs),
    onSuccess: () => {
      message.success(enEdition ? "Élève modifié." : "Élève créé.");
      qc.invalidateQueries({ queryKey: ["eleves"] });
      qc.invalidateQueries({ queryKey: ["classes"] });
      fermerModal();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  function ouvrirCreation() {
    setEnEdition(null);
    form.resetFields();
    setModalOuvert(true);
  }

  function ouvrirEdition(eleve: Eleve) {
    setEnEdition(eleve);
    form.setFieldsValue({
      matricule: eleve.matricule,
      nom: eleve.nom,
      prenom: eleve.prenom,
      sexe: eleve.sexe,
      classe_id: eleve.classe_id,
    });
    setModalOuvert(true);
  }

  function fermerModal() {
    setModalOuvert(false);
    setEnEdition(null);
  }

  return (
    <Card
      title="Élèves"
      extra={
        estAdmin && (
          <Button type="primary" onClick={ouvrirCreation}>
            Nouvel élève
          </Button>
        )
      }
    >
      <Input.Search
        placeholder="Rechercher par nom, prénom ou matricule"
        allowClear
        onSearch={setRecherche}
        onChange={(e) => !e.target.value && setRecherche("")}
        style={{ maxWidth: 360, marginBottom: 16 }}
      />
      <Table<Eleve>
        rowKey="id"
        loading={elevesQuery.isLoading}
        dataSource={elevesQuery.data ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        columns={[
          { title: "Matricule", dataIndex: "matricule", width: 130 },
          { title: "Nom", dataIndex: "nom" },
          { title: "Prénom", dataIndex: "prenom" },
          { title: "Sexe", dataIndex: "sexe", width: 70, render: (s) => s ?? "—" },
          {
            title: "Classe",
            dataIndex: "classe_id",
            render: (id: number | null) => (id ? (classesParId.get(id)?.nom ?? "—") : "—"),
          },
          {
            title: "Statut",
            dataIndex: "statut",
            width: 110,
            render: (s: Eleve["statut"]) => <Tag color={STATUT_COULEUR[s]}>{s}</Tag>,
          },
          ...(estAdmin
            ? [
                {
                  title: "",
                  key: "actions",
                  width: 90,
                  render: (_: unknown, eleve: Eleve) => (
                    <Button size="small" onClick={() => ouvrirEdition(eleve)}>
                      Modifier
                    </Button>
                  ),
                },
              ]
            : []),
        ]}
      />

      <Modal
        title={enEdition ? "Modifier l'élève" : "Nouvel élève"}
        open={modalOuvert}
        onCancel={fermerModal}
        onOk={() => form.submit()}
        confirmLoading={mutation.isPending}
        okText="Enregistrer"
        cancelText="Annuler"
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={(v) => mutation.mutate(v)}>
          <Space style={{ display: "flex" }} size="middle">
            <Form.Item
              name="matricule"
              label="Matricule"
              rules={[{ required: true, message: "Requis." }]}
              style={{ flex: 1 }}
            >
              <Input />
            </Form.Item>
            <Form.Item name="sexe" label="Sexe" style={{ width: 120 }}>
              <Select
                allowClear
                options={[
                  { value: "M", label: "M" },
                  { value: "F", label: "F" },
                ]}
              />
            </Form.Item>
          </Space>
          <Space style={{ display: "flex" }} size="middle">
            <Form.Item
              name="nom"
              label="Nom"
              rules={[{ required: true, message: "Requis." }]}
              style={{ flex: 1 }}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="prenom"
              label="Prénom"
              rules={[{ required: true, message: "Requis." }]}
              style={{ flex: 1 }}
            >
              <Input />
            </Form.Item>
          </Space>
          <Form.Item name="classe_id" label="Classe">
            <Select
              allowClear
              placeholder="Aucune"
              options={(classesQuery.data ?? []).map((c) => ({ value: c.id, label: c.nom }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}

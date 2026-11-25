import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App as AntApp,
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
} from "antd";
import { useEffect, useState } from "react";
import { messageErreur } from "../../api/client";
import {
  ajouterParent,
  getParents,
  modifierParent,
  retirerParent,
  type ParentPayload,
} from "../../api/endpoints";
import type { LienParent, ParentTuteur } from "../../api/types";
import { useDroits } from "../../auth/droits";

const LIEN_LABEL: Record<LienParent, { texte: string; couleur: string }> = {
  pere: { texte: "Père", couleur: "blue" },
  mere: { texte: "Mère", couleur: "magenta" },
  tuteur: { texte: "Tuteur", couleur: "geekblue" },
};

export function EleveParentsTab({ eleveId }: { eleveId: number }) {
  const { peut } = useDroits();
  const peutVoir = peut("eleves");
  const peutModifier = peut("eleves", true);
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [modalOuvert, setModalOuvert] = useState(false);
  const [enEdition, setEnEdition] = useState<ParentTuteur | null>(null);
  const [form] = Form.useForm<ParentPayload>();

  const query = useQuery({
    queryKey: ["parents", eleveId],
    queryFn: () => getParents(eleveId),
    enabled: peutVoir,
  });

  useEffect(() => {
    if (!modalOuvert) return;
    if (enEdition) {
      form.setFieldsValue({
        nom: enEdition.nom,
        prenom: enEdition.prenom,
        telephone: enEdition.telephone,
        email: enEdition.email,
        lien: enEdition.lien,
      });
    } else {
      form.resetFields();
    }
  }, [modalOuvert, enEdition, form]);

  const enregistrement = useMutation({
    mutationFn: (v: ParentPayload) =>
      enEdition ? modifierParent(eleveId, enEdition.parent_id, v) : ajouterParent(eleveId, v),
    onSuccess: () => {
      message.success(enEdition ? "Parent modifié." : "Parent ajouté.");
      qc.invalidateQueries({ queryKey: ["parents", eleveId] });
      setModalOuvert(false);
      setEnEdition(null);
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  const retrait = useMutation({
    mutationFn: (parentId: number) => retirerParent(eleveId, parentId),
    onSuccess: () => {
      message.success("Parent retiré.");
      qc.invalidateQueries({ queryKey: ["parents", eleveId] });
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  if (!peutVoir) {
    return (
      <Alert
        type="info"
        showIcon
        message="Accès réservé à l'administration"
        description="La liste des parents et tuteurs est réservée à la direction, au censeur, au surveillant et à la secrétaire."
      />
    );
  }
  if (query.isLoading) return <Skeleton active paragraph={{ rows: 4 }} />;

  return (
    <div>
      {peutModifier && (
        <Button
          type="primary"
          onClick={() => {
            setEnEdition(null);
            setModalOuvert(true);
          }}
          style={{ marginBottom: 16 }}
        >
          Ajouter un parent / tuteur
        </Button>
      )}

      <Table<ParentTuteur>
        rowKey="parent_id"
        size="small"
        dataSource={query.data ?? []}
        pagination={false}
        columns={[
          {
            title: "Lien",
            dataIndex: "lien",
            width: 110,
            render: (l: LienParent | null) =>
              l ? <Tag color={LIEN_LABEL[l].couleur}>{LIEN_LABEL[l].texte}</Tag> : "—",
          },
          {
            title: "Nom complet",
            key: "nom",
            render: (_: unknown, p) => `${p.prenom} ${p.nom}`,
          },
          { title: "Téléphone", dataIndex: "telephone", render: (t: string | null) => t ?? "—" },
          { title: "Email", dataIndex: "email", render: (e: string | null) => e ?? "—" },
          {
            title: "Compte mobile",
            dataIndex: "a_un_compte",
            width: 130,
            render: (a: boolean) => (a ? <Tag color="green">Activé</Tag> : <Tag>Non</Tag>),
          },
          ...(peutModifier
            ? [
                {
                  title: "",
                  key: "actions",
                  width: 170,
                  render: (_: unknown, p: ParentTuteur) => (
                    <Space>
                      <Button
                        size="small"
                        onClick={() => {
                          setEnEdition(p);
                          setModalOuvert(true);
                        }}
                      >
                        Modifier
                      </Button>
                      <Popconfirm
                        title="Retirer ce parent ?"
                        okText="Retirer"
                        cancelText="Annuler"
                        okButtonProps={{ danger: true }}
                        onConfirm={() => retrait.mutate(p.parent_id)}
                      >
                        <Button size="small" danger>
                          Retirer
                        </Button>
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]
            : []),
        ]}
      />

      <Modal
        title={enEdition ? "Modifier le parent / tuteur" : "Ajouter un parent / tuteur"}
        open={modalOuvert}
        onCancel={() => {
          setModalOuvert(false);
          setEnEdition(null);
        }}
        onOk={() => form.submit()}
        confirmLoading={enregistrement.isPending}
        okText="Enregistrer"
        cancelText="Annuler"
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(v) => enregistrement.mutate(v)}
          style={{ marginTop: 12 }}
        >
          <Form.Item name="lien" label="Lien avec l'élève">
            <Select
              allowClear
              placeholder="Père / Mère / Tuteur"
              options={[
                { value: "pere", label: "Père" },
                { value: "mere", label: "Mère" },
                { value: "tuteur", label: "Tuteur" },
              ]}
            />
          </Form.Item>
          <div style={{ display: "flex", gap: 16 }}>
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
          </div>
          <div style={{ display: "flex", gap: 16 }}>
            <Form.Item name="telephone" label="Téléphone" style={{ flex: 1 }}>
              <Input />
            </Form.Item>
            <Form.Item
              name="email"
              label="Email"
              rules={[{ type: "email", message: "Email invalide." }]}
              style={{ flex: 1 }}
            >
              <Input />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  );
}

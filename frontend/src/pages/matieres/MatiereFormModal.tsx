import { useMutation, useQueryClient } from "@tanstack/react-query";
import { App as AntApp, Form, Input, Modal, Switch, Typography } from "antd";
import { useEffect } from "react";
import { messageErreur } from "../../api/client";
import { creerMatiere, modifierMatiere } from "../../api/endpoints";
import type { Matiere } from "../../api/types";

interface Props {
  open: boolean;
  matiere: Matiere | null; // null => création
  onClose: () => void;
}

interface Valeurs {
  nom: string;
  code?: string | null;
  note_directe: boolean;
  est_choix_langue: boolean;
}

export function MatiereFormModal({ open, matiere, onClose }: Props) {
  const enEdition = matiere !== null;
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm<Valeurs>();

  useEffect(() => {
    if (!open) return;
    if (matiere) {
      form.setFieldsValue({
        nom: matiere.nom,
        code: matiere.code,
        note_directe: matiere.note_directe,
        est_choix_langue: matiere.est_choix_langue,
      });
    } else {
      form.resetFields();
      form.setFieldsValue({ note_directe: false, est_choix_langue: false });
    }
  }, [open, matiere, form]);

  const mutation = useMutation({
    mutationFn: (v: Valeurs) => {
      const payload = {
        nom: v.nom,
        code: v.code || null,
        note_directe: v.note_directe,
        est_choix_langue: v.est_choix_langue,
      };
      return enEdition ? modifierMatiere(matiere!.id, payload) : creerMatiere(payload);
    },
    onSuccess: () => {
      message.success(enEdition ? "Matière modifiée." : "Matière créée.");
      qc.invalidateQueries({ queryKey: ["matieres"] });
      qc.invalidateQueries({ queryKey: ["matiere"] });
      onClose();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <Modal
      title={enEdition ? "Modifier la matière" : "Nouvelle matière"}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={mutation.isPending}
      okText="Enregistrer"
      cancelText="Annuler"
      destroyOnHidden
    >
      <Form form={form} layout="vertical" onFinish={(v) => mutation.mutate(v)} style={{ marginTop: 12 }}>
        <div style={{ display: "flex", gap: 16 }}>
          <Form.Item
            name="nom"
            label="Nom"
            rules={[{ required: true, message: "Requis." }]}
            style={{ flex: 1 }}
          >
            <Input placeholder="ex : Mathématiques" />
          </Form.Item>
          <Form.Item name="code" label="Code (optionnel)" style={{ width: 140 }}>
            <Input placeholder="ex : MATH" />
          </Form.Item>
        </div>
        <Form.Item
          name="note_directe"
          label="Note directe"
          valuePropName="checked"
          extra="Une seule note par trimestre, sans interros/devoirs (ex : Conduite)."
        >
          <Switch />
        </Form.Item>
        <Form.Item
          name="est_choix_langue"
          label="Choix de langue"
          valuePropName="checked"
          extra="La langue réelle est choisie par élève (LV1, LV2)."
        >
          <Switch />
        </Form.Item>
        {!enEdition && (
          <Typography.Text type="secondary">
            Les coefficients par niveau / série se règlent ensuite sur la fiche de la matière.
          </Typography.Text>
        )}
      </Form>
    </Modal>
  );
}

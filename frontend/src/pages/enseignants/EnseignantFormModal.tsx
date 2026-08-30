import { useMutation, useQueryClient } from "@tanstack/react-query";
import { App as AntApp, Form, Input, Modal, Switch } from "antd";
import { useEffect } from "react";
import { messageErreur } from "../../api/client";
import { creerUtilisateur, modifierUtilisateur } from "../../api/endpoints";
import type { Utilisateur } from "../../api/types";

interface Props {
  open: boolean;
  enseignant: Utilisateur | null; // null => création
  onClose: () => void;
}

interface Valeurs {
  nom: string;
  prenom: string;
  email: string;
  telephone?: string | null;
  mot_de_passe?: string;
  actif: boolean;
}

export function EnseignantFormModal({ open, enseignant, onClose }: Props) {
  const enEdition = enseignant !== null;
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm<Valeurs>();

  useEffect(() => {
    if (!open) return;
    if (enseignant) {
      form.setFieldsValue({
        nom: enseignant.nom,
        prenom: enseignant.prenom,
        email: enseignant.email,
        telephone: enseignant.telephone,
        actif: enseignant.actif,
      });
    } else {
      form.resetFields();
      form.setFieldValue("actif", true);
    }
  }, [open, enseignant, form]);

  const mutation = useMutation({
    mutationFn: (v: Valeurs) => {
      if (enEdition) {
        return modifierUtilisateur(enseignant!.id, {
          nom: v.nom,
          prenom: v.prenom,
          telephone: v.telephone || null,
          actif: v.actif,
        });
      }
      return creerUtilisateur({
        nom: v.nom,
        prenom: v.prenom,
        email: v.email.trim(),
        mot_de_passe: v.mot_de_passe!,
        role: "enseignant",
        telephone: v.telephone || null,
      });
    },
    onSuccess: () => {
      message.success(enEdition ? "Enseignant modifié." : "Enseignant créé.");
      qc.invalidateQueries({ queryKey: ["utilisateurs"] });
      qc.invalidateQueries({ queryKey: ["utilisateur"] });
      onClose();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <Modal
      title={enEdition ? "Modifier l'enseignant" : "Nouvel enseignant"}
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
          <Form.Item name="nom" label="Nom" rules={[{ required: true, message: "Requis." }]} style={{ flex: 1 }}>
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
        <Form.Item
          name="email"
          label="Adresse email"
          rules={[
            { required: true, message: "Requis." },
            { type: "email", message: "Email invalide." },
          ]}
          extra={enEdition ? "L'email ne peut pas être modifié." : undefined}
        >
          <Input disabled={enEdition} />
        </Form.Item>
        <div style={{ display: "flex", gap: 16 }}>
          <Form.Item name="telephone" label="Téléphone" style={{ flex: 1 }}>
            <Input />
          </Form.Item>
          {!enEdition && (
            <Form.Item
              name="mot_de_passe"
              label="Mot de passe initial"
              rules={[
                { required: true, message: "Requis." },
                { min: 8, message: "Au moins 8 caractères." },
              ]}
              style={{ flex: 1 }}
            >
              <Input.Password autoComplete="new-password" />
            </Form.Item>
          )}
        </div>
        {enEdition && (
          <Form.Item name="actif" label="Compte actif" valuePropName="checked">
            <Switch />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { App as AntApp, Form, Input, Modal, Select, Switch } from "antd";
import { useEffect } from "react";
import { messageErreur } from "../../api/client";
import { creerUtilisateur, modifierUtilisateur } from "../../api/endpoints";
import type { Role, Utilisateur } from "../../api/types";
import { LIBELLES_ROLES, ROLES_PERSONNEL } from "../../auth/droits";

interface Props {
  open: boolean;
  membre: Utilisateur | null; // null => création
  onClose: () => void;
}

interface Valeurs {
  nom: string;
  prenom: string;
  email: string;
  telephone?: string | null;
  mot_de_passe?: string;
  roles: Role[];
  actif: boolean;
}

const DESCRIPTIONS: Record<string, string> = {
  directeur: "accès à tout, comptes et paramétrage",
  censeur: "pédagogie, emplois du temps, bulletins",
  surveillant: "présences, permissions, discipline",
  comptable: "tranches, contrôle des encaissements, paie",
  secretaire: "inscriptions, encaissement des frais",
  enseignant: "saisie des notes de ses classes",
};

export function PersonnelFormModal({ open, membre, onClose }: Props) {
  const enEdition = membre !== null;
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm<Valeurs>();

  useEffect(() => {
    if (!open) return;
    if (membre) {
      form.setFieldsValue({
        nom: membre.nom,
        prenom: membre.prenom,
        email: membre.email,
        telephone: membre.telephone,
        roles: membre.roles,
        actif: membre.actif,
      });
    } else {
      form.resetFields();
      form.setFieldsValue({ actif: true, roles: ["enseignant"] });
    }
  }, [open, membre, form]);

  const mutation = useMutation({
    mutationFn: (v: Valeurs) => {
      if (enEdition) {
        return modifierUtilisateur(membre!.id, {
          nom: v.nom,
          prenom: v.prenom,
          telephone: v.telephone || null,
          roles: v.roles,
          actif: v.actif,
        });
      }
      return creerUtilisateur({
        nom: v.nom,
        prenom: v.prenom,
        email: v.email.trim(),
        mot_de_passe: v.mot_de_passe!,
        roles: v.roles,
        telephone: v.telephone || null,
      });
    },
    onSuccess: () => {
      message.success(enEdition ? "Compte modifié." : "Compte créé.");
      qc.invalidateQueries({ queryKey: ["utilisateurs"] });
      qc.invalidateQueries({ queryKey: ["utilisateur"] });
      onClose();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <Modal
      title={enEdition ? "Modifier le compte" : "Nouveau membre du personnel"}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={mutation.isPending}
      okText="Enregistrer"
      cancelText="Annuler"
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={(v) => mutation.mutate(v)}
        style={{ marginTop: 12 }}
      >
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <Form.Item
            name="nom"
            label="Nom"
            rules={[{ required: true, message: "Requis." }]}
            style={{ flex: "1 1 180px" }}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="prenom"
            label="Prénom"
            rules={[{ required: true, message: "Requis." }]}
            style={{ flex: "1 1 180px" }}
          >
            <Input />
          </Form.Item>
        </div>
        <Form.Item
          name="roles"
          label="Rôle(s)"
          rules={[
            { required: true, type: "array", min: 1, message: "Choisissez au moins un rôle." },
          ]}
          extra="Une même personne peut cumuler plusieurs rôles : ses droits s'additionnent."
        >
          <Select
            mode="multiple"
            placeholder="Choisir"
            optionLabelProp="label"
            options={ROLES_PERSONNEL.map((r) => ({
              value: r,
              label: LIBELLES_ROLES[r],
              desc: DESCRIPTIONS[r],
            }))}
            optionRender={(o) => (
              <div>
                <div>{o.data.label}</div>
                <div style={{ fontSize: 12, opacity: 0.65 }}>{o.data.desc}</div>
              </div>
            )}
          />
        </Form.Item>
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
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <Form.Item name="telephone" label="Téléphone" style={{ flex: "1 1 180px" }}>
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
              style={{ flex: "1 1 180px" }}
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

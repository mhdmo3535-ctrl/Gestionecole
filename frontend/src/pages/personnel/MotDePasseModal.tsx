import { useMutation } from "@tanstack/react-query";
import { App as AntApp, Form, Input, Modal } from "antd";
import { messageErreur } from "../../api/client";
import { reinitialiserMotDePasse } from "../../api/endpoints";

interface Props {
  open: boolean;
  enseignantId: number | null;
  onClose: () => void;
}

export function MotDePasseModal({ open, enseignantId, onClose }: Props) {
  const { message } = AntApp.useApp();
  const [form] = Form.useForm<{ mdp: string; confirmation: string }>();

  const mutation = useMutation({
    mutationFn: (mdp: string) => reinitialiserMotDePasse(enseignantId!, mdp),
    onSuccess: () => {
      message.success("Mot de passe réinitialisé.");
      form.resetFields();
      onClose();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <Modal
      title="Réinitialiser le mot de passe"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={mutation.isPending}
      okText="Réinitialiser"
      cancelText="Annuler"
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={(v) => mutation.mutate(v.mdp)}
        style={{ marginTop: 12 }}
      >
        <Form.Item
          name="mdp"
          label="Nouveau mot de passe"
          rules={[
            { required: true, message: "Requis." },
            { min: 8, message: "Au moins 8 caractères." },
          ]}
        >
          <Input.Password autoComplete="new-password" />
        </Form.Item>
        <Form.Item
          name="confirmation"
          label="Confirmer"
          dependencies={["mdp"]}
          rules={[
            { required: true, message: "Requis." },
            ({ getFieldValue }) => ({
              validator: (_, value) =>
                !value || value === getFieldValue("mdp")
                  ? Promise.resolve()
                  : Promise.reject(new Error("Les mots de passe ne correspondent pas.")),
            }),
          ]}
        >
          <Input.Password autoComplete="new-password" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

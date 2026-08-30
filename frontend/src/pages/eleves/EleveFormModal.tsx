import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App as AntApp, DatePicker, Form, Input, Modal, Select } from "antd";
import dayjs from "dayjs";
import { useEffect } from "react";
import { messageErreur } from "../../api/client";
import { creerEleve, getClasses, modifierEleve } from "../../api/endpoints";
import type { Eleve } from "../../api/types";

interface Props {
  open: boolean;
  eleve: Eleve | null; // null => création
  onClose: () => void;
  onCree?: (eleve: Eleve) => void;
}

interface Valeurs {
  matricule: string;
  nom: string;
  prenom: string;
  sexe?: "M" | "F" | null;
  date_naissance?: dayjs.Dayjs | null;
  classe_id?: number | null;
  statut?: "actif" | "archive" | "redoublant";
}

export function EleveFormModal({ open, eleve, onClose, onCree }: Props) {
  const enEdition = eleve !== null;
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm<Valeurs>();

  const classesQuery = useQuery({ queryKey: ["classes"], queryFn: () => getClasses() });

  useEffect(() => {
    if (!open) return;
    if (eleve) {
      form.setFieldsValue({
        matricule: eleve.matricule,
        nom: eleve.nom,
        prenom: eleve.prenom,
        sexe: eleve.sexe,
        date_naissance: eleve.date_naissance ? dayjs(eleve.date_naissance) : null,
        classe_id: eleve.classe_id,
        statut: eleve.statut,
      });
    } else {
      form.resetFields();
    }
  }, [open, eleve, form]);

  const mutation = useMutation({
    mutationFn: (v: Valeurs) => {
      const payload = {
        matricule: v.matricule,
        nom: v.nom,
        prenom: v.prenom,
        sexe: v.sexe ?? null,
        date_naissance: v.date_naissance ? v.date_naissance.format("YYYY-MM-DD") : null,
        classe_id: v.classe_id ?? null,
        ...(enEdition ? { statut: v.statut } : {}),
      };
      return enEdition ? modifierEleve(eleve!.id, payload) : creerEleve(payload);
    },
    onSuccess: (res) => {
      message.success(enEdition ? "Élève modifié." : "Élève créé.");
      qc.invalidateQueries({ queryKey: ["eleves"] });
      qc.invalidateQueries({ queryKey: ["eleve"] });
      qc.invalidateQueries({ queryKey: ["classes"] });
      if (!enEdition) onCree?.(res);
      onClose();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <Modal
      title={enEdition ? "Modifier l'élève" : "Nouvel élève"}
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
            name="matricule"
            label="Matricule"
            rules={[{ required: true, message: "Requis." }]}
            style={{ flex: 1 }}
          >
            <Input />
          </Form.Item>
          <Form.Item name="sexe" label="Sexe" style={{ width: 110 }}>
            <Select
              allowClear
              options={[
                { value: "M", label: "M" },
                { value: "F", label: "F" },
              ]}
            />
          </Form.Item>
        </div>
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
          <Form.Item name="date_naissance" label="Date de naissance" style={{ flex: 1 }}>
            <DatePicker style={{ width: "100%" }} format="DD/MM/YYYY" />
          </Form.Item>
          <Form.Item name="classe_id" label="Classe" style={{ flex: 1 }}>
            <Select
              allowClear
              placeholder="Aucune"
              loading={classesQuery.isLoading}
              options={(classesQuery.data ?? []).map((c) => ({ value: c.id, label: c.nom }))}
            />
          </Form.Item>
        </div>
        {enEdition && (
          <Form.Item name="statut" label="Statut">
            <Select
              options={[
                { value: "actif", label: "Actif" },
                { value: "redoublant", label: "Redoublant" },
                { value: "archive", label: "Archivé" },
              ]}
            />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}

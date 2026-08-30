import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, App as AntApp, Button, Form, Input, Select, Skeleton, Typography } from "antd";
import dayjs from "dayjs";
import { useEffect } from "react";
import { messageErreur } from "../../api/client";
import { enregistrerInfosMedicales, getInfosMedicales } from "../../api/endpoints";
import type { InfosMedicales } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";

const GROUPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

type Valeurs = Pick<
  InfosMedicales,
  "groupe_sanguin" | "allergies" | "contacts_urgence" | "remarques"
>;

export function EleveMedicalTab({ eleveId }: { eleveId: number }) {
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm<Valeurs>();

  const query = useQuery({
    queryKey: ["infos-medicales", eleveId],
    queryFn: () => getInfosMedicales(eleveId),
    enabled: estAdmin,
  });

  useEffect(() => {
    if (query.data) {
      form.setFieldsValue({
        groupe_sanguin: query.data.groupe_sanguin,
        allergies: query.data.allergies,
        contacts_urgence: query.data.contacts_urgence,
        remarques: query.data.remarques,
      });
    }
  }, [query.data, form]);

  const mutation = useMutation({
    mutationFn: (v: Valeurs) =>
      enregistrerInfosMedicales(eleveId, {
        groupe_sanguin: v.groupe_sanguin || null,
        allergies: v.allergies || null,
        contacts_urgence: v.contacts_urgence || null,
        remarques: v.remarques || null,
      }),
    onSuccess: () => {
      message.success("Informations médicales enregistrées.");
      qc.invalidateQueries({ queryKey: ["infos-medicales", eleveId] });
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  if (!estAdmin) {
    return (
      <Alert
        type="info"
        showIcon
        message="Accès réservé à l'administration"
        description="Les informations médicales ne sont consultables que par l'administration de l'école."
      />
    );
  }

  if (query.isLoading) return <Skeleton active paragraph={{ rows: 6 }} />;

  return (
    <Form form={form} layout="vertical" onFinish={(v) => mutation.mutate(v)} style={{ maxWidth: 640 }}>
      <Form.Item name="groupe_sanguin" label="Groupe sanguin" style={{ maxWidth: 200 }}>
        <Select
          allowClear
          placeholder="—"
          options={GROUPES.map((g) => ({ value: g, label: g }))}
        />
      </Form.Item>
      <Form.Item name="allergies" label="Allergies">
        <Input.TextArea rows={2} placeholder="ex : arachides, pénicilline…" />
      </Form.Item>
      <Form.Item name="contacts_urgence" label="Contacts d'urgence">
        <Input.TextArea rows={3} placeholder="Nom, lien, téléphone" />
      </Form.Item>
      <Form.Item name="remarques" label="Remarques médicales">
        <Input.TextArea rows={3} placeholder="Asthme, traitement en cours, port de lunettes…" />
      </Form.Item>
      <Button type="primary" htmlType="submit" loading={mutation.isPending}>
        Enregistrer
      </Button>
      {query.data?.updated_at && (
        <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
          Dernière mise à jour le {dayjs(query.data.updated_at).format("DD/MM/YYYY à HH:mm")}.
        </Typography.Paragraph>
      )}
    </Form>
  );
}

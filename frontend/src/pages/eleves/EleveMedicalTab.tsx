import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { EditOutlined } from "@ant-design/icons";
import {
  Alert,
  App as AntApp,
  Button,
  Descriptions,
  Form,
  Input,
  Select,
  Skeleton,
  Space,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { useEffect, useState } from "react";
import { messageErreur } from "../../api/client";
import { enregistrerInfosMedicales, getInfosMedicales } from "../../api/endpoints";
import type { InfosMedicales } from "../../api/types";
import { useDroits } from "../../auth/droits";

const GROUPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

type Valeurs = Pick<
  InfosMedicales,
  "groupe_sanguin" | "allergies" | "contacts_urgence" | "remarques"
>;

export function EleveMedicalTab({ eleveId }: { eleveId: number }) {
  const { peut } = useDroits();
  const peutVoir = peut("medical");
  const peutModifier = peut("medical", true);
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm<Valeurs>();
  const [enEdition, setEnEdition] = useState(false);

  const query = useQuery({
    queryKey: ["infos-medicales", eleveId],
    queryFn: () => getInfosMedicales(eleveId),
    enabled: peutVoir,
  });

  // Le formulaire n'est monté qu'en mode édition : on le remplit à l'ouverture.
  useEffect(() => {
    if (enEdition && query.data) {
      form.setFieldsValue({
        groupe_sanguin: query.data.groupe_sanguin,
        allergies: query.data.allergies,
        contacts_urgence: query.data.contacts_urgence,
        remarques: query.data.remarques,
      });
    }
  }, [enEdition, query.data, form]);

  const annuler = () => {
    form.resetFields();
    setEnEdition(false);
  };

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
      setEnEdition(false);
      qc.invalidateQueries({ queryKey: ["infos-medicales", eleveId] });
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  if (!peutVoir) {
    return (
      <Alert
        type="info"
        showIcon
        message="Accès réservé à l'administration"
        description="Les informations médicales sont réservées à la direction, à la secrétaire et au surveillant général."
      />
    );
  }

  if (query.isLoading) return <Skeleton active paragraph={{ rows: 6 }} />;

  const miseAJour = query.data?.updated_at && (
    <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
      Dernière mise à jour le {dayjs(query.data.updated_at).format("DD/MM/YYYY à HH:mm")}.
    </Typography.Paragraph>
  );

  const texte = (v: string | null | undefined) =>
    v ? (
      <span style={{ whiteSpace: "pre-wrap" }}>{v}</span>
    ) : (
      <Typography.Text type="secondary">Non renseigné</Typography.Text>
    );

  if (!enEdition) {
    return (
      <div style={{ maxWidth: 640 }}>
        <Descriptions size="small" column={1} bordered styles={{ label: { width: 220 } }}>
          <Descriptions.Item label="Groupe sanguin">{texte(query.data?.groupe_sanguin)}</Descriptions.Item>
          <Descriptions.Item label="Allergies">{texte(query.data?.allergies)}</Descriptions.Item>
          <Descriptions.Item label="Contacts d'urgence">{texte(query.data?.contacts_urgence)}</Descriptions.Item>
          <Descriptions.Item label="Remarques médicales">{texte(query.data?.remarques)}</Descriptions.Item>
        </Descriptions>
        {peutModifier && (
          <Button icon={<EditOutlined />} onClick={() => setEnEdition(true)} style={{ marginTop: 16 }}>
            Modifier
          </Button>
        )}
        {miseAJour}
      </div>
    );
  }

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
      <Space>
        <Button type="primary" htmlType="submit" loading={mutation.isPending}>
          Enregistrer
        </Button>
        <Button onClick={annuler} disabled={mutation.isPending}>
          Annuler
        </Button>
      </Space>
      {miseAJour}
    </Form>
  );
}

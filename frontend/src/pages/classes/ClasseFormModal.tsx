import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App as AntApp, Form, Input, Modal, Select, Typography } from "antd";
import { useEffect, useMemo } from "react";
import { messageErreur } from "../../api/client";
import {
  creerClasse,
  getAnneesScolaires,
  getNiveaux,
  getSeries,
  getUtilisateurs,
  modifierClasse,
} from "../../api/endpoints";
import type { Classe } from "../../api/types";

interface Props {
  open: boolean;
  classe: Classe | null; // null => création
  onClose: () => void;
}

interface Valeurs {
  nom: string;
  niveau_id: number;
  serie_id?: number | null;
  annee_scolaire_id: number;
  professeur_principal_id?: number | null;
}

export function ClasseFormModal({ open, classe, onClose }: Props) {
  const enEdition = classe !== null;
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm<Valeurs>();

  const niveauxQuery = useQuery({ queryKey: ["niveaux"], queryFn: getNiveaux });
  const seriesQuery = useQuery({ queryKey: ["series"], queryFn: getSeries });
  const anneesQuery = useQuery({ queryKey: ["annees-scolaires"], queryFn: getAnneesScolaires });
  const enseignantsQuery = useQuery({
    queryKey: ["utilisateurs", "enseignant", "actifs"],
    queryFn: () => getUtilisateurs({ role: "enseignant", actif: true }),
    enabled: open,
  });

  const niveauId = Form.useWatch("niveau_id", form);
  const niveauChoisi = useMemo(
    () => niveauxQuery.data?.find((n) => n.id === niveauId),
    [niveauxQuery.data, niveauId],
  );
  const estCollege = niveauChoisi?.cycle === "college";

  useEffect(() => {
    if (!open) return;
    if (classe) {
      form.setFieldsValue({
        nom: classe.nom,
        niveau_id: classe.niveau_id,
        serie_id: classe.serie_id,
        annee_scolaire_id: classe.annee_scolaire_id,
        professeur_principal_id: classe.professeur_principal_id,
      });
    } else {
      const active = anneesQuery.data?.find((a) => a.active);
      form.resetFields();
      if (active) form.setFieldValue("annee_scolaire_id", active.id);
    }
  }, [open, classe, form, anneesQuery.data]);

  useEffect(() => {
    if (estCollege) form.setFieldValue("serie_id", null);
  }, [estCollege, form]);

  const mutation = useMutation({
    mutationFn: (v: Valeurs) => {
      const payload = {
        nom: v.nom,
        niveau_id: v.niveau_id,
        serie_id: estCollege ? null : (v.serie_id ?? null),
        annee_scolaire_id: v.annee_scolaire_id,
        professeur_principal_id: v.professeur_principal_id ?? null,
      };
      return enEdition ? modifierClasse(classe!.id, payload) : creerClasse(payload);
    },
    onSuccess: () => {
      message.success(enEdition ? "Classe modifiée." : "Classe créée.");
      qc.invalidateQueries({ queryKey: ["classes"] });
      qc.invalidateQueries({ queryKey: ["classe"] });
      onClose();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <Modal
      title={enEdition ? "Modifier la classe" : "Nouvelle classe"}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={mutation.isPending}
      okText="Enregistrer"
      cancelText="Annuler"
      destroyOnHidden
    >
      <Form form={form} layout="vertical" onFinish={(v) => mutation.mutate(v)} style={{ marginTop: 12 }}>
        <Form.Item name="nom" label="Nom de la classe" rules={[{ required: true, message: "Requis." }]}>
          <Input placeholder="ex : 3e A, Terminale D" />
        </Form.Item>
        <Form.Item
          name="niveau_id"
          label="Niveau"
          rules={[{ required: true, message: "Requis." }]}
        >
          <Select
            loading={niveauxQuery.isLoading}
            options={(niveauxQuery.data ?? []).map((n) => ({
              value: n.id,
              label: `${n.nom} — ${n.cycle === "college" ? "collège" : "lycée"}`,
            }))}
          />
        </Form.Item>
        <Form.Item
          name="serie_id"
          label="Série"
          extra={estCollege ? "Le collège n'a pas de série." : undefined}
        >
          <Select
            allowClear
            disabled={estCollege || !niveauChoisi}
            placeholder={estCollege ? "—" : "Choisir une série"}
            loading={seriesQuery.isLoading}
            options={(seriesQuery.data ?? []).map((s) => ({ value: s.id, label: s.nom }))}
          />
        </Form.Item>
        <Form.Item
          name="annee_scolaire_id"
          label="Année scolaire"
          rules={[{ required: true, message: "Requis." }]}
        >
          <Select
            loading={anneesQuery.isLoading}
            options={(anneesQuery.data ?? []).map((a) => ({
              value: a.id,
              label: a.active ? `${a.libelle} (active)` : a.libelle,
            }))}
          />
        </Form.Item>
        <Form.Item
          name="professeur_principal_id"
          label="Professeur principal"
          extra="Il saisit la note de conduite des élèves de la classe."
        >
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Choisir un enseignant"
            loading={enseignantsQuery.isLoading}
            options={(enseignantsQuery.data ?? []).map((u) => ({
              value: u.id,
              label: `${u.prenom} ${u.nom}`,
            }))}
          />
        </Form.Item>
        {!enEdition && (
          <Typography.Text type="secondary">
            Les élèves se rattachent à la classe depuis leur fiche.
          </Typography.Text>
        )}
      </Form>
    </Modal>
  );
}

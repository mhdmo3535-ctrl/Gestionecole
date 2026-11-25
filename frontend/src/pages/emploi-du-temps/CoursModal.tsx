import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  App as AntApp,
  Button,
  Form,
  Modal,
  Popconfirm,
  Select,
  TimePicker,
  Typography,
} from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useEffect, useMemo } from "react";
import { messageErreur } from "../../api/client";
import {
  ajouterCreneau,
  getAffectationsDeLaClasse,
  getMatieres,
  getUtilisateurs,
  modifierCreneau,
  supprimerCreneau,
} from "../../api/endpoints";
import type { Creneau, Jour } from "../../api/types";
import { JOURS } from "./temps";

interface Props {
  open: boolean;
  classeId: number;
  cours: Creneau | null; // null => nouveau cours
  /** Pré-remplissage d'un nouveau cours (jour cliqué). */
  jourParDefaut?: Jour;
  /** Pré-remplissage de l'horaire (case vide cliquée), en minutes depuis minuit. */
  horaireParDefaut?: [number, number];
  onClose: () => void;
}

interface Valeurs {
  jour: Jour;
  horaire: [Dayjs, Dayjs];
  matiere_id: number;
  enseignant_id: number;
}

const heure = (h: string) => dayjs(`2000-01-01T${h}`);

export function CoursModal({
  open,
  classeId,
  cours,
  jourParDefaut,
  horaireParDefaut,
  onClose,
}: Props) {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm<Valeurs>();
  const enEdition = cours !== null;

  const affectationsQuery = useQuery({
    queryKey: ["classe", classeId, "affectations"],
    queryFn: () => getAffectationsDeLaClasse(classeId),
    enabled: open,
  });
  const matieresQuery = useQuery({ queryKey: ["matieres"], queryFn: getMatieres, enabled: open });
  const enseignantsQuery = useQuery({
    queryKey: ["utilisateurs", "enseignant", "actifs"],
    queryFn: () => getUtilisateurs({ role: "enseignant", actif: true }),
    enabled: open,
  });
  const affectations = useMemo(() => affectationsQuery.data ?? [], [affectationsQuery.data]);

  // toutes les matières enseignables (la conduite est une note, pas un cours) :
  // d'abord celles qui ont déjà un professeur dans la classe, puis les autres (ex : TD)
  const matieres = useMemo(() => {
    const avecProf = new Set(affectations.map((a) => a.matiere_id));
    const enseignables = (matieresQuery.data ?? []).filter((m) => !m.note_directe);
    const option = (m: { id: number; nom: string; evaluee: boolean }) => ({
      value: m.id,
      label: m.evaluee ? m.nom : `${m.nom} (sans note)`,
    });
    return [
      {
        label: "Avec un professeur dans cette classe",
        options: enseignables.filter((m) => avecProf.has(m.id)).map(option),
      },
      {
        label: "Autres matières",
        options: enseignables.filter((m) => !avecProf.has(m.id)).map(option),
      },
    ].filter((g) => g.options.length > 0);
  }, [affectations, matieresQuery.data]);

  const matiereId = Form.useWatch("matiere_id", form);
  const enseignantId = Form.useWatch("enseignant_id", form);
  const profsAffectes = affectations.filter((a) => a.matiere_id === matiereId);
  // personne n'enseigne encore cette matière ici : on peut choisir n'importe quel enseignant
  const sansProf = !!matiereId && profsAffectes.length === 0;
  const profs = sansProf
    ? (enseignantsQuery.data ?? []).map((u) => ({
        enseignant_id: u.id,
        enseignant_nom: `${u.prenom} ${u.nom}`,
      }))
    : profsAffectes;

  useEffect(() => {
    if (!open) return;
    form.resetFields();
    if (cours) {
      form.setFieldsValue({
        jour: cours.jour,
        horaire: [heure(cours.heure_debut), heure(cours.heure_fin)],
        matiere_id: cours.matiere_id,
        enseignant_id: cours.enseignant_id,
      });
    } else {
      if (jourParDefaut) form.setFieldValue("jour", jourParDefaut);
      if (horaireParDefaut) {
        const [d, f] = horaireParDefaut.map((m) => dayjs("2000-01-01").add(m, "minute"));
        form.setFieldValue("horaire", [d, f]);
      }
    }
  }, [open, cours, jourParDefaut, horaireParDefaut, form]);

  // un seul professeur affecté pour la matière : on le choisit d'office
  useEffect(() => {
    if (
      profsAffectes.length === 1 &&
      form.getFieldValue("enseignant_id") !== profsAffectes[0].enseignant_id
    ) {
      form.setFieldValue("enseignant_id", profsAffectes[0].enseignant_id);
    }
  }, [profsAffectes, form]);

  const invalider = () => {
    qc.invalidateQueries({ queryKey: ["emploi-du-temps"] });
    // une affectation a pu être créée avec le cours
    qc.invalidateQueries({ queryKey: ["classe", classeId, "affectations"] });
    qc.invalidateQueries({ queryKey: ["utilisateur"] });
  };

  const enregistrement = useMutation({
    mutationFn: (v: Valeurs) => {
      const payload = {
        jour: v.jour,
        heure_debut: v.horaire[0].format("HH:mm"),
        heure_fin: v.horaire[1].format("HH:mm"),
        matiere_id: v.matiere_id,
        enseignant_id: v.enseignant_id,
        creer_affectation: sansProf,
      };
      return enEdition
        ? modifierCreneau(cours!.id, payload)
        : ajouterCreneau({ ...payload, classe_id: classeId });
    },
    onSuccess: () => {
      message.success(enEdition ? "Cours modifié." : "Cours ajouté.");
      invalider();
      onClose();
    },
    onError: (e) => message.error(messageErreur(e), 6),
  });
  const suppression = useMutation({
    mutationFn: () => supprimerCreneau(cours!.id),
    onSuccess: () => {
      message.success("Cours retiré de l'emploi du temps.");
      invalider();
      onClose();
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <Modal
      title={enEdition ? "Modifier le cours" : "Ajouter un cours"}
      open={open}
      onCancel={onClose}
      destroyOnHidden
      footer={[
        enEdition && (
          <Popconfirm
            key="suppr"
            title="Retirer ce cours de l'emploi du temps ?"
            okText="Retirer"
            cancelText="Annuler"
            okButtonProps={{ danger: true }}
            onConfirm={() => suppression.mutate()}
          >
            <Button danger loading={suppression.isPending} style={{ float: "left" }}>
              Retirer
            </Button>
          </Popconfirm>
        ),
        <Button key="annuler" onClick={onClose}>
          Annuler
        </Button>,
        <Button
          key="ok"
          type="primary"
          loading={enregistrement.isPending}
          onClick={() => form.submit()}
        >
          Enregistrer
        </Button>,
      ]}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={(v) => enregistrement.mutate(v)}
        style={{ marginTop: 12 }}
        requiredMark={false}
      >
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <Form.Item
            name="jour"
            label="Jour"
            rules={[{ required: true, message: "Choisissez le jour." }]}
            style={{ flex: "1 1 140px" }}
          >
            <Select options={JOURS.map((j) => ({ value: j.numero, label: j.nom }))} />
          </Form.Item>
          <Form.Item
            name="horaire"
            label="Horaire"
            rules={[{ required: true, message: "Indiquez le début et la fin." }]}
            style={{ flex: "2 1 220px" }}
          >
            <TimePicker.RangePicker
              format="HH:mm"
              minuteStep={5}
              needConfirm={false}
              placeholder={["Début", "Fin"]}
              style={{ width: "100%" }}
            />
          </Form.Item>
        </div>
        <Form.Item
          name="matiere_id"
          label="Matière"
          rules={[{ required: true, message: "Choisissez la matière." }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            loading={affectationsQuery.isLoading || matieresQuery.isLoading}
            options={matieres}
            onChange={() => form.setFieldValue("enseignant_id", undefined)}
          />
        </Form.Item>
        <Form.Item
          name="enseignant_id"
          label="Professeur"
          rules={[{ required: true, message: "Choisissez le professeur." }]}
          extra={
            sansProf && (
              <Typography.Text type="secondary">
                Aucun professeur n'enseigne encore cette matière dans la classe.
                {enseignantId
                  ? " Le professeur choisi y sera affecté en même temps que le cours."
                  : " Choisissez-en un : il y sera affecté en même temps que le cours."}
              </Typography.Text>
            )
          }
        >
          <Select
            showSearch
            optionFilterProp="label"
            disabled={!matiereId}
            placeholder={matiereId ? undefined : "Choisissez d'abord la matière"}
            loading={sansProf && enseignantsQuery.isLoading}
            options={profs.map((p) => ({ value: p.enseignant_id, label: p.enseignant_nom }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

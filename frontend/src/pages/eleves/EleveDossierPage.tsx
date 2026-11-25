import { ArrowLeftOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Card,
  Descriptions,
  Result,
  Skeleton,
  Space,
  Tabs,
  Tag,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getClasse, getEleve } from "../../api/endpoints";
import type { Eleve } from "../../api/types";
import { EleveFormModal } from "./EleveFormModal";
import { EleveMedicalTab } from "./EleveMedicalTab";
import { EleveParentsTab } from "./EleveParentsTab";
import { ElevePaiementsTab } from "./ElevePaiementsTab";
import { EleveScolariteTab } from "./EleveScolariteTab";
import { EleveVieScolaireTab } from "./EleveVieScolaireTab";
import { useDroits } from "../../auth/droits";

const STATUT_LIBELLE: Record<Eleve["statut"], { texte: string; couleur: string }> = {
  actif: { texte: "Actif", couleur: "green" },
  redoublant: { texte: "Redoublant", couleur: "gold" },
  archive: { texte: "Archivé", couleur: "default" },
};

export function EleveDossierPage() {
  const { id } = useParams();
  const eleveId = Number(id);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { peut } = useDroits();
  const peutModifier = peut("eleves", true);
  const [editionOuverte, setEditionOuverte] = useState(false);

  const eleveQuery = useQuery({
    queryKey: ["eleve", eleveId],
    queryFn: () => getEleve(eleveId),
    enabled: Number.isFinite(eleveId),
  });
  const eleve = eleveQuery.data;

  const classeQuery = useQuery({
    queryKey: ["classe", eleve?.classe_id],
    queryFn: () => getClasse(eleve!.classe_id!),
    enabled: !!eleve?.classe_id,
  });

  if (eleveQuery.isLoading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    );
  }

  if (eleveQuery.isError || !eleve) {
    return (
      <Card>
        <Result
          status="404"
          title="Élève introuvable"
          extra={
            <Button type="primary" onClick={() => navigate("/eleves")}>
              Retour à la liste
            </Button>
          }
        />
      </Card>
    );
  }

  const statut = STATUT_LIBELLE[eleve.statut];
  const classeTexte = eleve.classe_id
    ? (classeQuery.data?.nom ?? "…")
    : "Non affecté à une classe";

  return (
    <Space orientation="vertical" size="middle" style={{ display: "flex" }}>
      <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => navigate("/eleves")} style={{ paddingInline: 0 }}>
        Élèves
      </Button>

      <Card
        title={
          <Space size="middle" wrap>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {eleve.prenom} {eleve.nom}
            </Typography.Title>
            <Tag>{eleve.matricule}</Tag>
            <Tag color={statut.couleur}>{statut.texte}</Tag>
            <Typography.Text type="secondary">{classeTexte}</Typography.Text>
          </Space>
        }
        extra={
          peutModifier && <Button onClick={() => setEditionOuverte(true)}>Modifier</Button>
        }
      >
        <Tabs
          defaultActiveKey={searchParams.get("onglet") ?? "identite"}
          items={[
            {
              key: "identite",
              label: "Identité",
              children: (
                <Descriptions
                  bordered
                  column={1}
                  size="middle"
                  styles={{ label: { width: 220 } }}
                  items={[
                    { key: "matricule", label: "Matricule", children: eleve.matricule },
                    { key: "nom", label: "Nom", children: eleve.nom },
                    { key: "prenom", label: "Prénom", children: eleve.prenom },
                    {
                      key: "naissance",
                      label: "Date de naissance",
                      children: eleve.date_naissance
                        ? dayjs(eleve.date_naissance).format("DD/MM/YYYY")
                        : "—",
                    },
                    {
                      key: "sexe",
                      label: "Sexe",
                      children:
                        eleve.sexe === "M" ? "Masculin" : eleve.sexe === "F" ? "Féminin" : "—",
                    },
                    {
                      key: "statut",
                      label: "Statut",
                      children: <Tag color={statut.couleur}>{statut.texte}</Tag>,
                    },
                    { key: "classe", label: "Classe", children: classeTexte },
                  ]}
                />
              ),
            },
            {
              key: "scolarite",
              label: "Scolarité",
              children: <EleveScolariteTab eleve={eleve} />,
            },
            {
              key: "medical",
              label: "Informations médicales",
              children: <EleveMedicalTab eleveId={eleve.id} />,
            },
            {
              key: "parents",
              label: "Parents / tuteurs",
              children: <EleveParentsTab eleveId={eleve.id} />,
            },
            {
              key: "vie-scolaire",
              label: "Vie scolaire",
              children: <EleveVieScolaireTab eleveId={eleve.id} />,
            },
            {
              key: "paiements",
              label: "Paiements",
              children: <ElevePaiementsTab eleveId={eleve.id} />,
            },
          ]}
        />
      </Card>

      <EleveFormModal
        open={editionOuverte}
        eleve={eleve}
        onClose={() => setEditionOuverte(false)}
      />
    </Space>
  );
}

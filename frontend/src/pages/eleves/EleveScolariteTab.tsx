import { useQuery } from "@tanstack/react-query";
import { Alert, Card, Descriptions, Divider, Empty, Select, Skeleton, Typography } from "antd";
import { useEffect, useState } from "react";
import { getClasse, getTrimestres } from "../../api/endpoints";
import type { Eleve } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { BulletinEleveVue } from "../bulletins/BulletinEleveVue";
import { ProgressionChart } from "./ProgressionChart";

export function EleveScolariteTab({ eleve }: { eleve: Eleve }) {
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  const [trimestreId, setTrimestreId] = useState<number | undefined>();

  const classeQuery = useQuery({
    queryKey: ["classe", eleve.classe_id],
    queryFn: () => getClasse(eleve.classe_id!),
    enabled: !!eleve.classe_id,
  });
  const trimestresQuery = useQuery({
    queryKey: ["trimestres", "active"],
    queryFn: () => getTrimestres(),
  });

  useEffect(() => {
    if (!trimestreId && trimestresQuery.data?.length) {
      setTrimestreId(trimestresQuery.data[0].id);
    }
  }, [trimestresQuery.data, trimestreId]);

  return (
    <div>
      <Typography.Title level={5} style={{ marginTop: 0 }}>
        Classe actuelle
      </Typography.Title>
      {!eleve.classe_id ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Cet élève n'est rattaché à aucune classe."
        />
      ) : classeQuery.isLoading ? (
        <Skeleton active paragraph={{ rows: 2 }} />
      ) : classeQuery.data ? (
        <Descriptions size="small" column={1} bordered styles={{ label: { width: 220 } }}>
          <Descriptions.Item label="Classe">{classeQuery.data.nom}</Descriptions.Item>
          <Descriptions.Item label="Niveau">{classeQuery.data.niveau_nom}</Descriptions.Item>
          <Descriptions.Item label="Série">{classeQuery.data.serie_nom ?? "—"}</Descriptions.Item>
          <Descriptions.Item label="Année scolaire">
            {classeQuery.data.annee_libelle}
          </Descriptions.Item>
        </Descriptions>
      ) : null}

      <Divider />

      <Typography.Title level={5}>Progression</Typography.Title>
      {!estAdmin ? (
        <Alert type="info" showIcon message="La progression est consultable par l'administration." />
      ) : !eleve.classe_id ? (
        <Typography.Text type="secondary">
          Rattachez l'élève à une classe pour suivre sa progression.
        </Typography.Text>
      ) : (
        <>
          <Typography.Paragraph type="secondary">
            Moyenne générale par trimestre (le trait rouge marque la barre des 10).
          </Typography.Paragraph>
          <ProgressionChart eleveId={eleve.id} />
        </>
      )}

      <Divider />

      <Typography.Title level={5}>Bulletins</Typography.Title>
      {!estAdmin ? (
        <Alert
          type="info"
          showIcon
          message="Les bulletins sont consultables par l'administration."
        />
      ) : !eleve.classe_id ? (
        <Typography.Text type="secondary">
          Rattachez l'élève à une classe pour générer ses bulletins.
        </Typography.Text>
      ) : (
        <>
          <Select
            style={{ width: 200, marginBottom: 16 }}
            placeholder="Trimestre"
            value={trimestreId}
            onChange={setTrimestreId}
            loading={trimestresQuery.isLoading}
            options={(trimestresQuery.data ?? []).map((t) => ({
              value: t.id,
              label: `Trimestre ${t.numero}`,
            }))}
          />
          {trimestreId && (
            <Card size="small">
              <BulletinEleveVue eleveId={eleve.id} trimestreId={trimestreId} />
            </Card>
          )}
        </>
      )}

      <Divider />

      <Typography.Title level={5}>Historique des classes</Typography.Title>
      <Typography.Paragraph type="secondary">
        L'historique année par année se remplira lors des passages de classe en fin d'année scolaire.
      </Typography.Paragraph>
    </div>
  );
}

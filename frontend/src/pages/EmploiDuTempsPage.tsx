import { PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Col, Empty, Row, Segmented, Select, Space, Table, Typography } from "antd";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getClasses, getEmploiDuTemps, getUtilisateurs } from "../api/endpoints";
import type { Creneau, Jour } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useDroits } from "../auth/droits";
import { CoursModal } from "./emploi-du-temps/CoursModal";
import { TableauEdt } from "./emploi-du-temps/TableauEdt";
import { formatDuree } from "./emploi-du-temps/temps";

type Vue = "classe" | "professeur";

/** Volume horaire hebdomadaire, regroupé par matière (vue classe) ou par classe (vue professeur). */
function Volumes({ creneaux, vue }: { creneaux: Creneau[]; vue: Vue }) {
  const lignes = useMemo(() => {
    const acc = new Map<string, number>();
    creneaux.forEach((c) => {
      const cle = vue === "classe" ? c.matiere_nom : `${c.classe_nom} · ${c.matiere_nom}`;
      acc.set(cle, (acc.get(cle) ?? 0) + c.duree_minutes);
    });
    return [...acc]
      .map(([libelle, minutes]) => ({ libelle, minutes }))
      .sort((a, b) => b.minutes - a.minutes || a.libelle.localeCompare(b.libelle));
  }, [creneaux, vue]);
  const total = lignes.reduce((s, l) => s + l.minutes, 0);

  return (
    <Table
      rowKey="libelle"
      size="small"
      pagination={false}
      dataSource={lignes}
      locale={{ emptyText: "Aucun cours" }}
      columns={[
        { title: vue === "classe" ? "Matière" : "Classe · matière", dataIndex: "libelle" },
        {
          title: "Par semaine",
          dataIndex: "minutes",
          align: "right",
          width: 110,
          render: (m: number) => (
            <span style={{ fontVariantNumeric: "tabular-nums" }}>{formatDuree(m)}</span>
          ),
        },
      ]}
      summary={() =>
        lignes.length > 0 && (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0}>
              <Typography.Text strong>Total</Typography.Text>
            </Table.Summary.Cell>
            <Table.Summary.Cell index={1} align="right">
              <Typography.Text strong style={{ fontVariantNumeric: "tabular-nums" }}>
                {formatDuree(total)}
              </Typography.Text>
            </Table.Summary.Cell>
          </Table.Summary.Row>
        )
      }
    />
  );
}

export function EmploiDuTempsPage() {
  const { utilisateur } = useAuth();
  const { peut, estEnseignant } = useDroits();
  const voitTout = peut("pedagogie");
  const peutModifier = peut("pedagogie", true);
  const [params, setParams] = useSearchParams();

  // un enseignant sans rôle pédagogique ne voit que son propre emploi du temps
  const vue: Vue = !voitTout
    ? "professeur"
    : params.get("vue") === "professeur"
      ? "professeur"
      : "classe";
  const classesQuery = useQuery({
    queryKey: ["classes"],
    queryFn: () => getClasses(),
    enabled: voitTout,
  });
  // sans choix explicite, la première classe est affichée
  const idChoisi =
    Number(params.get("id")) || (vue === "classe" ? classesQuery.data?.[0]?.id : undefined);
  const id = !voitTout ? utilisateur?.id : idChoisi;
  const profsQuery = useQuery({
    queryKey: ["utilisateurs", "enseignant", "actifs"],
    queryFn: () => getUtilisateurs({ role: "enseignant", actif: true }),
    enabled: voitTout && vue === "professeur",
  });

  const choisir = (v: Vue, nouvelId?: number) =>
    setParams(nouvelId ? { vue: v, id: String(nouvelId) } : { vue: v }, { replace: true });

  const edtQuery = useQuery({
    queryKey: ["emploi-du-temps", vue, id],
    queryFn: () => getEmploiDuTemps(vue === "classe" ? { classe_id: id } : { enseignant_id: id }),
    enabled: !!id,
  });
  const creneaux = edtQuery.data ?? [];

  const [modal, setModal] = useState<{
    cours: Creneau | null;
    jour?: Jour;
    horaire?: [number, number];
  } | null>(null);
  const editable = peutModifier && vue === "classe" && !!id;

  const options =
    vue === "classe"
      ? (classesQuery.data ?? []).map((c) => ({ value: c.id, label: c.nom }))
      : (profsQuery.data ?? []).map((u) => ({ value: u.id, label: `${u.prenom} ${u.nom}` }));

  return (
    <Space orientation="vertical" size="middle" style={{ display: "flex" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <Typography.Title level={3} style={{ margin: 0 }}>
          {voitTout ? "Emploi du temps" : "Mon emploi du temps"}
        </Typography.Title>
        {voitTout && (
          <Space wrap>
            <Segmented
              value={vue}
              onChange={(v) => choisir(v as Vue)}
              options={[
                { label: "Par classe", value: "classe" },
                { label: "Par professeur", value: "professeur" },
              ]}
            />
            <Select
              showSearch
              optionFilterProp="label"
              style={{ width: 220 }}
              placeholder={vue === "classe" ? "Choisir une classe" : "Choisir un professeur"}
              value={idChoisi}
              onChange={(v) => choisir(vue, v)}
              loading={vue === "classe" ? classesQuery.isLoading : profsQuery.isLoading}
              options={options}
            />
            {editable && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setModal({ cours: null })}
              >
                Ajouter un cours
              </Button>
            )}
          </Space>
        )}
      </div>

      {!id ? (
        <Card>
          <Empty
            description={
              voitTout
                ? `Choisissez ${vue === "classe" ? "une classe" : "un professeur"} pour afficher son emploi du temps.`
                : estEnseignant
                  ? "Aucun cours."
                  : "Accès réservé."
            }
          />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          <Col xs={24} xxl={18}>
            <Card loading={edtQuery.isLoading} styles={{ body: { padding: 12 } }}>
              <TableauEdt
                creneaux={creneaux}
                sousTitre={(c) => (vue === "classe" ? c.enseignant_nom : c.classe_nom)}
                onCours={editable ? (c) => setModal({ cours: c }) : undefined}
                onCaseVide={
                  editable
                    ? (jour, debut, fin) => setModal({ cours: null, jour, horaire: [debut, fin] })
                    : undefined
                }
              />
              {editable && creneaux.length === 0 && !edtQuery.isLoading && (
                <Typography.Paragraph type="secondary" style={{ margin: "12px 4px 0" }}>
                  Aucun cours pour l'instant. Cliquez sur une case du tableau ou sur « Ajouter un
                  cours ».
                </Typography.Paragraph>
              )}
            </Card>
          </Col>
          <Col xs={24} xxl={6}>
            <Card title="Volume horaire" styles={{ body: { paddingTop: 8 } }}>
              <Volumes creneaux={creneaux} vue={vue} />
            </Card>
          </Col>
        </Row>
      )}

      {editable && modal && (
        <CoursModal
          open
          classeId={id!}
          cours={modal.cours}
          jourParDefaut={modal.jour}
          horaireParDefaut={modal.horaire}
          onClose={() => setModal(null)}
        />
      )}
    </Space>
  );
}

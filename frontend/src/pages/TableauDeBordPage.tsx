import { ExclamationCircleOutlined, InfoCircleOutlined, RightOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Card,
  Col,
  Empty,
  List,
  Progress,
  Result,
  Row,
  Segmented,
  Select,
  Skeleton,
  Space,
  Table,
  Typography,
  theme,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { getTableauDeBord, getTrimestres } from "../api/endpoints";
import type { TableauDeBord, TdbLigne } from "../api/types";
import { fcfa } from "./paiements/format";

const nombre = new Intl.NumberFormat("fr-FR");
const note = (v: number) =>
  v.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pct = (v: number) => `${Math.round(v * 100)} %`;
const jour = (d: string) => dayjs(d).format("DD/MM");

/** Tuile de chiffre clé : un libellé, une valeur, une ligne de contexte. */
function Tuile({
  libelle,
  valeur,
  unite,
  contexte,
  jauge,
}: {
  libelle: string;
  valeur: ReactNode;
  unite?: string;
  contexte?: ReactNode;
  jauge?: number | null;
}) {
  const { token } = theme.useToken();
  return (
    <Card style={{ height: "100%" }} styles={{ body: { padding: 20 } }}>
      <Typography.Text type="secondary">{libelle}</Typography.Text>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 6 }}>
        <span style={{ fontSize: 30, fontWeight: 600, lineHeight: 1.15, color: token.colorText }}>
          {valeur}
        </span>
        {unite && <Typography.Text type="secondary">{unite}</Typography.Text>}
      </div>
      {jauge !== undefined && jauge !== null && (
        <Progress
          percent={Math.round(jauge * 100)}
          showInfo={false}
          size="small"
          strokeColor={token.colorPrimary}
          style={{ margin: "6px 0 0" }}
        />
      )}
      {contexte && (
        <Typography.Text type="secondary" style={{ display: "block", marginTop: 6, fontSize: 13 }}>
          {contexte}
        </Typography.Text>
      )}
    </Card>
  );
}

/** Ligne de jauge : la barre et le pourcentage, alignés d'une ligne à l'autre. */
function Jauge({ valeur }: { valeur: number | null }) {
  const { token } = theme.useToken();
  if (valeur === null) return <Typography.Text type="secondary">—</Typography.Text>;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 140 }}>
      <Progress
        percent={Math.round(valeur * 100)}
        showInfo={false}
        size="small"
        strokeColor={token.colorPrimary}
        style={{ margin: 0, flex: 1 }}
      />
      <span style={{ width: 42, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
        {pct(valeur)}
      </span>
    </div>
  );
}

function colonnes(t: TableauDeBord, parNiveau: boolean): ColumnsType<TdbLigne> {
  const nombres = { fontVariantNumeric: "tabular-nums" } as const;
  const cols: ColumnsType<TdbLigne> = [
    {
      title: parNiveau ? "Niveau" : "Classe",
      dataIndex: "libelle",
      width: 120,
      render: (v: string) => (
        <Typography.Text strong style={{ whiteSpace: "nowrap" }}>
          {v}
        </Typography.Text>
      ),
    },
    {
      title: "Effectif",
      dataIndex: "effectif",
      width: 90,
      align: "right",
      render: (v) => <span style={nombres}>{v}</span>,
    },
  ];
  if (t.scolarite) {
    cols.push(
      {
        title: "Moyenne",
        dataIndex: "moyenne",
        width: 100,
        align: "right",
        render: (v: number | null) =>
          v === null ? (
            <Typography.Text type="secondary">—</Typography.Text>
          ) : (
            <span style={nombres}>{note(v)}</span>
          ),
      },
      {
        title: "Élèves à 10 ou plus",
        dataIndex: "taux_reussite",
        width: 200,
        render: (v: number | null) => <Jauge valeur={v} />,
      },
    );
  }
  if (t.vie_scolaire) {
    cols.push({
      title: "Présence",
      dataIndex: "taux_presence",
      width: 200,
      render: (v: number | null) => <Jauge valeur={v} />,
    });
  }
  if (t.finances) {
    cols.push({
      title: "Frais encaissés",
      dataIndex: "taux_recouvrement",
      width: 200,
      render: (v: number | null) => <Jauge valeur={v} />,
    });
  }
  return cols;
}

export function TableauDeBordPage() {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const [trimestreId, setTrimestreId] = useState<number | undefined>();
  const [vue, setVue] = useState<"classes" | "niveaux">("classes");

  const query = useQuery({
    queryKey: ["tableau-de-bord", trimestreId ?? "courant"],
    queryFn: () => getTableauDeBord(trimestreId),
  });
  const t = query.data;
  const trimestresQuery = useQuery({
    queryKey: ["trimestres", "active"],
    queryFn: () => getTrimestres(),
    enabled: !!t && (!!t.scolarite || !!t.vie_scolaire),
  });

  if (query.isLoading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 8 }} />
      </Card>
    );
  }
  if (query.isError || !t) {
    return (
      <Card>
        <Result status="warning" title="Le tableau de bord n'a pas pu être chargé." />
      </Card>
    );
  }

  const e = t.effectifs;
  const periode = t.periode_presence;
  const lignes = vue === "classes" ? t.classes : t.niveaux;

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
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>
            Tableau de bord
          </Typography.Title>
          <Typography.Text type="secondary">
            {t.trimestre
              ? `Année ${t.trimestre.annee_libelle} · Trimestre ${t.trimestre.numero}`
              : "Aucune année scolaire active"}
          </Typography.Text>
        </div>
        {(t.scolarite || t.vie_scolaire) && t.trimestre && (
          <Select
            style={{ width: 170 }}
            value={t.trimestre.id}
            onChange={setTrimestreId}
            loading={trimestresQuery.isLoading}
            options={(trimestresQuery.data ?? []).map((tr) => ({
              value: tr.id,
              label: `Trimestre ${tr.numero}`,
            }))}
          />
        )}
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} xl={6}>
          <Tuile
            libelle="Élèves inscrits"
            valeur={nombre.format(e.eleves_actifs)}
            contexte={`${e.filles} filles · ${e.garcons} garçons · ${e.classes} classe${e.classes > 1 ? "s" : ""}`}
          />
        </Col>
        {t.scolarite && (
          <Col xs={24} sm={12} xl={6}>
            <Tuile
              libelle={`Moyenne générale${t.trimestre ? ` (T${t.trimestre.numero})` : ""}`}
              valeur={t.scolarite.moyenne_ecole === null ? "—" : note(t.scolarite.moyenne_ecole)}
              unite={t.scolarite.moyenne_ecole === null ? undefined : "/ 20"}
              contexte={
                t.scolarite.taux_reussite === null
                  ? "Aucune note saisie pour ce trimestre"
                  : `${pct(t.scolarite.taux_reussite)} des élèves à 10 ou plus`
              }
            />
          </Col>
        )}
        {t.vie_scolaire && (
          <Col xs={24} sm={12} xl={6}>
            <Tuile
              libelle="Taux de présence"
              valeur={
                t.vie_scolaire.taux_presence === null ? "—" : pct(t.vie_scolaire.taux_presence)
              }
              contexte={
                periode
                  ? `${t.vie_scolaire.jours_absence} jour(s) d'absence · ${t.vie_scolaire.retards} retard(s), du ${jour(periode.debut)} au ${jour(periode.fin)}`
                  : "Le trimestre n'a pas encore commencé"
              }
            />
          </Col>
        )}
        {t.finances && (
          <Col xs={24} sm={12} xl={6}>
            <Tuile
              libelle={`Frais de scolarité ${t.finances.annee_libelle}`}
              valeur={
                t.finances.taux_recouvrement === null ? "—" : pct(t.finances.taux_recouvrement)
              }
              unite="encaissés"
              jauge={t.finances.taux_recouvrement}
              contexte={`${fcfa(t.finances.encaisse)} sur ${fcfa(t.finances.attendu)} · ce mois : ${fcfa(t.finances.encaisse_mois)}`}
            />
          </Col>
        )}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <Card
            title={vue === "classes" ? "Vue par classe" : "Vue par niveau"}
            extra={
              <Segmented
                size="small"
                value={vue}
                onChange={(v) => setVue(v as "classes" | "niveaux")}
                options={[
                  { label: "Classes", value: "classes" },
                  { label: "Niveaux", value: "niveaux" },
                ]}
              />
            }
            styles={{ body: { paddingTop: 8 } }}
          >
            <Table<TdbLigne>
              rowKey={(l) => (l.classe_id ? `c${l.classe_id}` : `n${l.niveau_nom}`)}
              size="middle"
              pagination={false}
              dataSource={lignes}
              columns={colonnes(t, vue === "niveaux")}
              scroll={{ x: 640 }}
              locale={{ emptyText: <Empty description="Aucune classe pour l'année active." /> }}
              onRow={(l) =>
                l.classe_id
                  ? {
                      onClick: () => navigate(`/classes/${l.classe_id}`),
                      style: { cursor: "pointer" },
                    }
                  : {}
              }
            />
            {periode && t.vie_scolaire && (
              <Typography.Text
                type="secondary"
                style={{ display: "block", marginTop: 12, fontSize: 12 }}
              >
                Présence calculée sur {periode.jours_ouvres} jours de classe (lundi au samedi), du{" "}
                {dayjs(periode.debut).format("DD/MM/YYYY")} au{" "}
                {dayjs(periode.fin).format("DD/MM/YYYY")}.
              </Typography.Text>
            )}
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="À traiter" style={{ height: "100%" }} styles={{ body: { paddingTop: 4 } }}>
            {t.alertes.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Rien à signaler." />
            ) : (
              <List
                dataSource={t.alertes}
                renderItem={(a) => (
                  <List.Item
                    actions={
                      a.lien
                        ? [
                            <Button
                              key="voir"
                              type="text"
                              size="small"
                              icon={<RightOutlined />}
                              aria-label="Voir"
                              onClick={() => navigate(a.lien!)}
                            />,
                          ]
                        : undefined
                    }
                  >
                    <Space align="start" size={10}>
                      {a.niveau === "attention" ? (
                        <ExclamationCircleOutlined
                          style={{ color: token.colorWarning, fontSize: 16, marginTop: 3 }}
                        />
                      ) : (
                        <InfoCircleOutlined style={{ fontSize: 16, marginTop: 3, opacity: 0.6 }} />
                      )}
                      <span>
                        <Typography.Text strong>{a.nombre}</Typography.Text> {a.libelle}
                      </span>
                    </Space>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

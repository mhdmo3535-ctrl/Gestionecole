import { CheckCircleOutlined, ClockCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  App as AntApp,
  Button,
  Card,
  Empty,
  Input,
  Modal,
  Segmented,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { messageErreur } from "../api/client";
import { getAutorisationsEcole, traiterPermission } from "../api/endpoints";
import type { PermissionEcole, StatutPermission } from "../api/types";
import { useDroits } from "../auth/droits";

type Filtre = StatutPermission | "toutes";

const STATUTS: Record<
  StatutPermission,
  { texte: string; couleur: string; icone: React.ReactNode }
> = {
  en_attente: { texte: "En attente", couleur: "gold", icone: <ClockCircleOutlined /> },
  approuve: { texte: "Acceptée", couleur: "green", icone: <CheckCircleOutlined /> },
  rejete: { texte: "Refusée", couleur: "red", icone: <CloseCircleOutlined /> },
};

const date = (d: string) => dayjs(d).format("DD/MM/YYYY");

function periode(p: PermissionEcole): string {
  const jours = dayjs(p.date_fin).diff(dayjs(p.date_debut), "day") + 1;
  return p.date_debut === p.date_fin
    ? `le ${date(p.date_debut)}`
    : `du ${date(p.date_debut)} au ${date(p.date_fin)} (${jours} jours)`;
}

export function AutorisationsPage() {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  const { peut } = useDroits();
  const peutTraiter = peut("vie_scolaire", true);
  const [filtre, setFiltre] = useState<Filtre>("en_attente");
  const [refus, setRefus] = useState<PermissionEcole | null>(null);
  const [motifRefus, setMotifRefus] = useState("");

  const query = useQuery({ queryKey: ["autorisations"], queryFn: getAutorisationsEcole });
  const toutes = useMemo(() => query.data ?? [], [query.data]);
  const compte = (s: StatutPermission) => toutes.filter((p) => p.statut === s).length;
  const lignes = filtre === "toutes" ? toutes : toutes.filter((p) => p.statut === filtre);

  const traitement = useMutation({
    mutationFn: (v: { p: PermissionEcole; statut: StatutPermission; commentaire?: string }) =>
      traiterPermission(v.p.eleve_id, v.p.id, {
        statut: v.statut,
        commentaire_traitement: v.commentaire || null,
      }),
    onSuccess: (_, v) => {
      message.success(
        v.statut === "approuve"
          ? `Autorisation accordée à ${v.p.eleve_nom}.`
          : v.statut === "rejete"
            ? `Demande de ${v.p.eleve_nom} refusée.`
            : "Demande remise en attente.",
      );
      qc.invalidateQueries({ queryKey: ["autorisations"] });
      qc.invalidateQueries({ queryKey: ["tableau-de-bord"] });
      qc.invalidateQueries({ queryKey: ["eleve", v.p.eleve_id] });
      setRefus(null);
      setMotifRefus("");
    },
    onError: (e) => message.error(messageErreur(e)),
  });

  return (
    <Card
      title="Autorisations d'absence"
      extra={
        <Typography.Text type="secondary">
          Les demandes se créent depuis l'onglet « Vie scolaire » de chaque élève.
        </Typography.Text>
      }
    >
      <Segmented<Filtre>
        value={filtre}
        onChange={setFiltre}
        style={{ marginBottom: 16 }}
        options={[
          { label: `En attente (${compte("en_attente")})`, value: "en_attente" },
          { label: `Acceptées (${compte("approuve")})`, value: "approuve" },
          { label: `Refusées (${compte("rejete")})`, value: "rejete" },
          { label: "Toutes", value: "toutes" },
        ]}
      />

      <Table<PermissionEcole>
        rowKey="id"
        loading={query.isLoading}
        dataSource={lignes}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        scroll={{ x: 900 }}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                filtre === "en_attente" ? "Aucune demande en attente." : "Aucune demande."
              }
            />
          ),
        }}
        columns={[
          {
            title: "Élève",
            key: "eleve",
            render: (_, p) => (
              <Space orientation="vertical" size={0}>
                <Link to={`/eleves/${p.eleve_id}?onglet=vie-scolaire`}>{p.eleve_nom}</Link>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {p.matricule}
                  {p.classe_nom ? ` · ${p.classe_nom}` : ""}
                </Typography.Text>
              </Space>
            ),
          },
          { title: "Absence", key: "periode", render: (_, p) => periode(p) },
          { title: "Motif", dataIndex: "motif", ellipsis: true },
          {
            title: "Demandée le",
            onHeaderCell: () => ({ style: { whiteSpace: "nowrap" } }),
            dataIndex: "demande_le",
            width: 130,
            render: (d: string) => date(d),
          },
          {
            title: "Décision",
            key: "statut",
            width: 220,
            render: (_, p) => {
              const s = STATUTS[p.statut];
              return (
                <Space orientation="vertical" size={2}>
                  <Tag color={s.couleur} icon={s.icone} style={{ marginInlineEnd: 0 }}>
                    {s.texte}
                  </Tag>
                  {p.statut !== "en_attente" && (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {p.traite_par_nom ?? "—"}
                      {p.traite_le ? `, le ${date(p.traite_le)}` : ""}
                    </Typography.Text>
                  )}
                  {p.commentaire_traitement && (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }} italic>
                      « {p.commentaire_traitement} »
                    </Typography.Text>
                  )}
                </Space>
              );
            },
          },
          ...(peutTraiter
            ? [
                {
                  title: "",
                  key: "actions",
                  width: 200,
                  render: (_: unknown, p: PermissionEcole) =>
                    p.statut === "en_attente" ? (
                      <Space>
                        <Button
                          type="primary"
                          size="small"
                          loading={traitement.isPending && traitement.variables?.p.id === p.id}
                          onClick={() => traitement.mutate({ p, statut: "approuve" })}
                        >
                          Accepter
                        </Button>
                        <Button size="small" danger onClick={() => setRefus(p)}>
                          Refuser
                        </Button>
                      </Space>
                    ) : (
                      <Button
                        size="small"
                        type="link"
                        style={{ paddingInline: 0 }}
                        onClick={() => traitement.mutate({ p, statut: "en_attente" })}
                      >
                        Remettre en attente
                      </Button>
                    ),
                },
              ]
            : []),
        ]}
      />

      <Modal
        title="Refuser la demande"
        open={refus !== null}
        onCancel={() => {
          setRefus(null);
          setMotifRefus("");
        }}
        okText="Refuser"
        okButtonProps={{ danger: true }}
        cancelText="Annuler"
        confirmLoading={traitement.isPending}
        onOk={() =>
          refus && traitement.mutate({ p: refus, statut: "rejete", commentaire: motifRefus })
        }
        destroyOnHidden
      >
        {refus && (
          <Typography.Paragraph>
            Demande de <Typography.Text strong>{refus.eleve_nom}</Typography.Text>, {periode(refus)}{" "}
            : « {refus.motif} »
          </Typography.Paragraph>
        )}
        <Input.TextArea
          rows={3}
          placeholder="Raison du refus (facultatif, visible dans le dossier de l'élève)"
          value={motifRefus}
          onChange={(e) => setMotifRefus(e.target.value)}
        />
      </Modal>
    </Card>
  );
}

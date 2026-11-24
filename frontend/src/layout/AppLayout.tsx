import {
  BookOutlined,
  IdcardOutlined,
  LogoutOutlined,
  ProfileOutlined,
  ReadOutlined,
  SolutionOutlined,
  TeamOutlined,
  WalletOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Avatar, Dropdown, Layout, Menu, Segmented, Skeleton, theme, Typography } from "antd";
import { useMemo, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { getAnneesScolaires, getMonEcole } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { useModeTheme } from "../ModeThemeProvider";
import { COULEURS_BENIN, FILET_BENIN, SIDER_TITRE } from "../theme";

function initiales(nom: string): string {
  const mots = nom.trim().split(/\s+/).filter(Boolean);
  const lettres = (mots[0]?.[0] ?? "") + (mots.length > 1 ? mots[mots.length - 1][0] : "");
  return lettres.toUpperCase() || "É";
}

const { Sider, Header, Content } = Layout;

interface Entree {
  cle: string;
  libelle: string;
  icone: React.ReactNode;
  roles?: Array<"admin" | "enseignant">;
}

const ENTREES: Entree[] = [
  { cle: "/eleves", libelle: "Élèves", icone: <IdcardOutlined /> },
  { cle: "/classes", libelle: "Classes", icone: <TeamOutlined /> },
  { cle: "/matieres", libelle: "Matières", icone: <BookOutlined />, roles: ["admin"] },
  { cle: "/enseignants", libelle: "Enseignants", icone: <SolutionOutlined />, roles: ["admin"] },
  { cle: "/notes", libelle: "Saisie des notes", icone: <ReadOutlined />, roles: ["enseignant"] },
  { cle: "/bulletins", libelle: "Bulletins", icone: <ProfileOutlined />, roles: ["admin"] },
  { cle: "/paiements", libelle: "Paiements", icone: <WalletOutlined />, roles: ["admin"] },
];

export function AppLayout() {
  const { utilisateur, deconnexion } = useAuth();
  const { mode, definir } = useModeTheme();
  const { token } = theme.useToken();
  const [siderCache, setSiderCache] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const ecoleQuery = useQuery({ queryKey: ["ecole"], queryFn: getMonEcole, staleTime: 5 * 60_000 });
  const anneesQuery = useQuery({
    queryKey: ["annees-scolaires"],
    queryFn: getAnneesScolaires,
    staleTime: 5 * 60_000,
  });
  const anneeActive = anneesQuery.data?.find((a) => a.active);

  const entrees = useMemo(
    () =>
      ENTREES.filter(
        (e) => !e.roles || (utilisateur && e.roles.includes(utilisateur.role as "admin" | "enseignant")),
      ),
    [utilisateur],
  );

  const cleActive = ENTREES.find((e) => location.pathname.startsWith(e.cle))?.cle ?? "/eleves";

  return (
    <Layout hasSider style={{ minHeight: "100vh" }}>
      <div style={{ height: 4, background: FILET_BENIN, position: "fixed", inset: "0 0 auto 0", zIndex: 1000 }} />
      <Sider
        breakpoint="lg"
        collapsedWidth="0"
        onBreakpoint={setSiderCache}
        style={{
          position: "fixed",
          top: 16,
          left: 12,
          bottom: 12,
          height: "calc(100vh - 28px)",
          borderRadius: token.borderRadiusLG,
          overflow: "auto",
          zIndex: 100,
        }}
      >
        <div style={{ padding: 16 }}>
          <Typography.Title level={4} style={{ margin: 0, color: SIDER_TITRE.titre }}>
            Schoolaris
          </Typography.Title>
          <span style={{ fontSize: 12, color: SIDER_TITRE.sousTitre }}>Gestion scolaire</span>
        </div>
        <Menu
          mode="inline"
          style={{ background: "transparent", borderInlineEnd: "none" }}
          selectedKeys={[cleActive]}
          onClick={({ key }) => navigate(key)}
          items={entrees.map((e) => ({ key: e.cle, icon: e.icone, label: e.libelle }))}
        />
      </Sider>
      <Layout
        style={{
          padding: 12,
          marginLeft: siderCache ? 0 : 212,
          transition: "margin-left 0.2s",
        }}
      >
        <Header
          style={{
            background: token.colorBgContainer,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 20,
            paddingInline: 24,
            borderRadius: token.borderRadiusLG,
            border: `1px solid ${token.colorBorderSecondary}`,
            position: "sticky",
            top: 12,
            zIndex: 50,
          }}
        >
          {ecoleQuery.data ? (
            <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
              <Avatar
                shape="square"
                size={40}
                style={{ flexShrink: 0, background: COULEURS_BENIN.vert, color: "#fff", fontWeight: 700, borderRadius: 10 }}
              >
                {(ecoleQuery.data.sigle || initiales(ecoleQuery.data.nom)).slice(0, 3)}
              </Avatar>
              <div style={{ minWidth: 0, lineHeight: 1.25 }}>
                <div
                  style={{ fontWeight: 600, fontSize: 15, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
                  title={ecoleQuery.data.nom}
                >
                  {ecoleQuery.data.nom}
                </div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {anneeActive ? `Année scolaire ${anneeActive.libelle}` : "Établissement scolaire"}
                </Typography.Text>
              </div>
            </div>
          ) : (
            <Skeleton.Input active size="small" style={{ width: 200 }} />
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 20, flexShrink: 0 }}>
          <Segmented
            size="small"
            value={mode}
            onChange={(v) => definir(v as "clair" | "sombre")}
            options={[
              { label: "Clair", value: "clair" },
              { label: "Sombre", value: "sombre" },
            ]}
          />
          <Dropdown
            menu={{
              items: [
                { key: "deconnexion", icon: <LogoutOutlined />, label: "Se déconnecter" },
              ],
              onClick: ({ key }) => {
                if (key === "deconnexion") deconnexion();
              },
            }}
          >
            <span style={{ cursor: "pointer" }}>
              {utilisateur?.prenom} {utilisateur?.nom}{" "}
              <Typography.Text type="secondary">({utilisateur?.role})</Typography.Text>
            </span>
          </Dropdown>
          </div>
        </Header>
        <Content style={{ marginTop: 12 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

import {
  BookOutlined,
  IdcardOutlined,
  LogoutOutlined,
  ProfileOutlined,
  ReadOutlined,
  SolutionOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { Dropdown, Layout, Menu, Typography } from "antd";
import { useMemo } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

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
  { cle: "/notes", libelle: "Saisie des notes", icone: <ReadOutlined /> },
  { cle: "/bulletins", libelle: "Bulletins", icone: <ProfileOutlined />, roles: ["admin"] },
];

export function AppLayout() {
  const { utilisateur, deconnexion } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const entrees = useMemo(
    () =>
      ENTREES.filter(
        (e) => !e.roles || (utilisateur && e.roles.includes(utilisateur.role as "admin" | "enseignant")),
      ),
    [utilisateur],
  );

  const cleActive = ENTREES.find((e) => location.pathname.startsWith(e.cle))?.cle ?? "/eleves";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider breakpoint="lg" collapsedWidth="0" theme="light">
        <div style={{ padding: 16 }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            Schoolaris
          </Typography.Title>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            Gestion scolaire
          </Typography.Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[cleActive]}
          onClick={({ key }) => navigate(key)}
          items={entrees.map((e) => ({ key: e.cle, icon: e.icone, label: e.libelle }))}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            paddingInline: 24,
            borderBottom: "1px solid #f0f0f0",
          }}
        >
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
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

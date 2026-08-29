import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { messageErreur } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { utilisateur, pret, connexion } = useAuth();
  const navigate = useNavigate();
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  if (pret && utilisateur) return <Navigate to="/eleves" replace />;

  async function onFinish(valeurs: { email: string; motDePasse: string }) {
    setErreur(null);
    setEnCours(true);
    try {
      await connexion(valeurs.email.trim(), valeurs.motDePasse);
      navigate("/eleves", { replace: true });
    } catch (e) {
      setErreur(messageErreur(e, "Connexion impossible."));
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div style={{ display: "grid", placeItems: "center", minHeight: "100vh", background: "#f5f5f5" }}>
      <Card style={{ width: 360 }}>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          Schoolaris
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
          Connexion à l'espace administration / enseignants
        </Typography.Paragraph>
        {erreur && <Alert type="error" message={erreur} style={{ marginBottom: 16 }} showIcon />}
        <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="email"
            label="Adresse email"
            rules={[{ required: true, message: "Saisissez votre email." }]}
          >
            <Input type="email" autoComplete="username" size="large" />
          </Form.Item>
          <Form.Item
            name="motDePasse"
            label="Mot de passe"
            rules={[{ required: true, message: "Saisissez votre mot de passe." }]}
          >
            <Input.Password autoComplete="current-password" size="large" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block size="large" loading={enCours}>
            Se connecter
          </Button>
        </Form>
      </Card>
    </div>
  );
}

import { Alert, Button, Card, Form, Input, theme, Typography } from "antd";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { messageErreur } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import photoClasse from "../assets/connexion-classe.webp";
import { COULEURS_BENIN, FILET_BENIN } from "../theme";

export function LoginPage() {
  const { utilisateur, pret, connexion } = useAuth();
  const { token } = theme.useToken();
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
    <div className="connexion" style={{ background: token.colorBgLayout }}>
      <div
        className="connexion-photo"
        style={{ backgroundImage: `url(${photoClasse})` }}
        role="img"
        aria-label="Élèves souriants en uniforme dans une salle de classe, drapeau du Bénin au mur"
      >
        <div className="connexion-accroche">
          <div
            style={{
              width: 72,
              height: 5,
              background: FILET_BENIN,
              borderRadius: 3,
              marginBottom: 16,
            }}
          />
          <h2
            style={{
              color: "#fff",
              fontSize: 32,
              lineHeight: 1.2,
              margin: 0,
              fontWeight: 700,
            }}
          >
            Le suivi scolaire de vos élèves, au même endroit.
          </h2>
          <p
            style={{
              color: "rgba(255,255,255,0.85)",
              fontSize: 16,
              margin: "12px 0 0",
            }}
          >
            Dossiers, notes, bulletins, présences et paiements.
          </p>
        </div>
      </div>
      <div className="connexion-formulaire">
        <Card
          style={{ width: "100%", maxWidth: 380, overflow: "hidden" }}
          styles={{ body: { paddingTop: 28 } }}
        >
          <div
            style={{
              position: "absolute",
              inset: "0 0 auto 0",
              height: 5,
              background: FILET_BENIN,
            }}
          />
          <Typography.Title
            level={3}
            style={{ marginTop: 0, color: COULEURS_BENIN.vert }}
          >
            Schoolaris
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
            Connexion à l'espace administration / enseignants
          </Typography.Paragraph>
          {erreur && (
            <Alert
              type="error"
              message={erreur}
              style={{ marginBottom: 16 }}
              showIcon
            />
          )}
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
              rules={[
                { required: true, message: "Saisissez votre mot de passe." },
              ]}
            >
              <Input.Password autoComplete="current-password" size="large" />
            </Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              block
              size="large"
              loading={enCours}
            >
              Se connecter
            </Button>
          </Form>
        </Card>
      </div>
    </div>
  );
}

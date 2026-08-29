import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { TOKEN_KEY, setUnauthorizedHandler } from "../api/client";
import { getMoi, login as apiLogin } from "../api/endpoints";
import type { Utilisateur } from "../api/types";

interface AuthState {
  utilisateur: Utilisateur | null;
  pret: boolean; // true une fois la session initiale vérifiée
  connexion: (email: string, motDePasse: string) => Promise<void>;
  deconnexion: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [pret, setPret] = useState(false);

  useEffect(() => {
    setUnauthorizedHandler(() => setUtilisateur(null));
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setPret(true);
      return;
    }
    getMoi()
      .then(setUtilisateur)
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setPret(true));
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      utilisateur,
      pret,
      connexion: async (email, motDePasse) => {
        const token = await apiLogin(email, motDePasse);
        localStorage.setItem(TOKEN_KEY, token);
        setUtilisateur(await getMoi());
      },
      deconnexion: () => {
        localStorage.removeItem(TOKEN_KEY);
        setUtilisateur(null);
      },
    }),
    [utilisateur, pret],
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth doit être utilisé dans un AuthProvider.");
  return ctx;
}

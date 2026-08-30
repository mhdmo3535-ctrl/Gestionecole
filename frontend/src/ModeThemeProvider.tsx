import { App as AntApp, ConfigProvider } from "antd";
import frFR from "antd/locale/fr_FR";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { construireTheme, type ModeTheme } from "./theme";

const STOCKAGE = "schoolaris_mode";

interface ModeThemeState {
  mode: ModeTheme;
  definir: (mode: ModeTheme) => void;
  basculer: () => void;
}

const Ctx = createContext<ModeThemeState | null>(null);

function modeInitial(): ModeTheme {
  const enregistre = localStorage.getItem(STOCKAGE);
  if (enregistre === "clair" || enregistre === "sombre") return enregistre;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "sombre" : "clair";
}

export function ModeThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ModeTheme>(modeInitial);

  useEffect(() => {
    localStorage.setItem(STOCKAGE, mode);
    document.documentElement.style.colorScheme = mode === "sombre" ? "dark" : "light";
  }, [mode]);

  const definir = useCallback((m: ModeTheme) => setMode(m), []);
  const basculer = useCallback(
    () => setMode((m) => (m === "sombre" ? "clair" : "sombre")),
    [],
  );

  const value = useMemo(() => ({ mode, definir, basculer }), [mode, definir, basculer]);

  return (
    <Ctx.Provider value={value}>
      <ConfigProvider locale={frFR} theme={construireTheme(mode)}>
        <AntApp>{children}</AntApp>
      </ConfigProvider>
    </Ctx.Provider>
  );
}

export function useModeTheme(): ModeThemeState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useModeTheme doit être utilisé dans un ModeThemeProvider.");
  return ctx;
}

import { theme as antdTheme, type ThemeConfig } from "antd";

export type ModeTheme = "clair" | "sombre";

/** Couleurs du drapeau du Bénin. */
export const COULEURS_BENIN = {
  vert: "#008751",
  jaune: "#FCD116",
  rouge: "#E8112D",
} as const;

/** Dégradé tricolore (vert / jaune / rouge) pour les filets d'accent. */
export const FILET_BENIN = `linear-gradient(90deg, ${COULEURS_BENIN.vert} 0 40%, ${COULEURS_BENIN.jaune} 40% 70%, ${COULEURS_BENIN.rouge} 70% 100%)`;

/** Couleurs du bloc titre dans le menu latéral vert (identiques en clair et sombre). */
export const SIDER_TITRE = {
  titre: "#ffffff",
  sousTitre: "rgba(255,255,255,0.75)",
} as const;

export function construireTheme(mode: ModeTheme): ThemeConfig {
  const sombre = mode === "sombre";
  return {
    algorithm: sombre ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: sombre ? "#1AA06A" : COULEURS_BENIN.vert,
      colorInfo: sombre ? "#1AA06A" : COULEURS_BENIN.vert,
      colorSuccess: sombre ? "#1AA06A" : COULEURS_BENIN.vert,
      colorWarning: sombre ? "#E9B84A" : "#E0A800",
      colorError: sombre ? "#F04A5E" : COULEURS_BENIN.rouge,
      colorLink: sombre ? "#1AA06A" : COULEURS_BENIN.vert,
      colorBgLayout: sombre ? "#101418" : "#dde0e4",
      borderRadius: 10,
      borderRadiusLG: 16,
      fontFamily: 'system-ui, "Segoe UI", Roboto, sans-serif',
    },
    components: {
      Layout: {
        // le menu latéral reste vert dans les deux modes
        siderBg: COULEURS_BENIN.vert,
        headerBg: sombre ? "#1b1f24" : "#ffffff",
      },
      Menu: {
        itemBg: "transparent",
        itemColor: "rgba(255,255,255,0.85)",
        itemHoverColor: "#ffffff",
        itemHoverBg: "rgba(255,255,255,0.12)",
        // onglet actif : pastille blanche pleine, texte + icône en vert => bien tranché
        itemSelectedColor: COULEURS_BENIN.vert,
        itemSelectedBg: "#ffffff",
        itemActiveBg: "rgba(255,255,255,0.18)",
        itemHeight: 44,
        iconSize: 16,
        // titres de rubrique (« Pédagogie », « Finances »…) : discrets, lisibles sur le vert
        groupTitleColor: "rgba(255,255,255,0.6)",
        groupTitleFontSize: 11,
      },
      Button: {
        primaryShadow: "none",
      },
      Table: {
        // survol de ligne bien visible, teinté vert
        rowHoverBg: sombre ? "rgba(26,160,106,0.16)" : "rgba(0,135,81,0.08)",
        headerBg: sombre ? "rgba(255,255,255,0.06)" : "#f0f2f4",
      },
      Descriptions: {
        labelBg: sombre ? "rgba(255,255,255,0.05)" : "#f2f4f6",
      },
    },
  };
}

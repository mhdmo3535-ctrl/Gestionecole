import { useQuery } from "@tanstack/react-query";
import { Alert, Empty, Skeleton, theme } from "antd";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { messageErreur } from "../../api/client";
import { getProgressionEleve } from "../../api/endpoints";
import { COULEURS_BENIN } from "../../theme";

export function ProgressionChart({ eleveId }: { eleveId: number }) {
  const { token } = theme.useToken();
  const query = useQuery({
    queryKey: ["progression", eleveId],
    queryFn: () => getProgressionEleve(eleveId),
  });

  if (query.isLoading) return <Skeleton active paragraph={{ rows: 4 }} />;
  if (query.isError || !query.data) {
    return <Alert type="error" showIcon message={messageErreur(query.error, "Progression indisponible.")} />;
  }

  const data = query.data.points.map((p) => ({
    nom: `Trim. ${p.trimestre_numero}`,
    moyenne: p.moyenne_generale,
  }));
  const nbAvecNote = data.filter((d) => d.moyenne != null).length;

  if (nbAvecNote === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="Aucune moyenne disponible pour le moment."
      />
    );
  }

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={token.colorBorderSecondary} />
          <XAxis dataKey="nom" stroke={token.colorTextSecondary} />
          <YAxis domain={[0, 20]} ticks={[0, 5, 10, 15, 20]} stroke={token.colorTextSecondary} />
          <Tooltip
            contentStyle={{
              background: token.colorBgElevated,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: 8,
            }}
            formatter={(v: number | null) =>
              v == null ? "—" : [String(v).replace(".", ","), "Moyenne"]
            }
          />
          <ReferenceLine y={10} stroke={COULEURS_BENIN.rouge} strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="moyenne"
            stroke={COULEURS_BENIN.vert}
            strokeWidth={2.5}
            dot={{ r: 4, fill: COULEURS_BENIN.vert }}
            activeDot={{ r: 6 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

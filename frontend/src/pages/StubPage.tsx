import { Card, Empty } from "antd";

export function StubPage({ titre }: { titre: string }) {
  return (
    <Card title={titre}>
      <Empty description="Écran à construire dans la prochaine étape." />
    </Card>
  );
}

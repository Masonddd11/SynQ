import { SessionDetailPage } from '@/views/SessionDetail';

export default async function Page({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <SessionDetailPage sessionId={sessionId} />;
}

import type { Metadata } from 'next';
import '@/index.css';
import { Layout } from '@/components/Layout';

export const metadata: Metadata = {
  title: 'Jings Street',
  description:
    'Jings Street — AI-powered swing trading dashboard for backtesting, paper trading, and portfolio analysis.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Layout>{children}</Layout>
      </body>
    </html>
  );
}

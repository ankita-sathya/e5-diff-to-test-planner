import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'E5 Diff-to-Test Planner',
  description: 'Risk-based test selection engine for automotive HMI software',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}

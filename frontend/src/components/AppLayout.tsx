import type { ReactNode } from "react";

import { AppHeader } from "./AppHeader";

interface AppLayoutProps {
  title?: string;
  subtitle?: string;
  shellClassName?: string;
  children: ReactNode;
}

export function AppLayout({
  title,
  subtitle,
  shellClassName = "app-shell",
  children,
}: AppLayoutProps) {
  return (
    <div className="page-body">
      <main className={shellClassName}>
        <AppHeader title={title} subtitle={subtitle} />
        {children}
      </main>
    </div>
  );
}

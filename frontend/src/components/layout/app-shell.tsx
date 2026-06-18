"use client";

import Link from "next/link";
import { Bot, Gauge, MessageSquare } from "lucide-react";
import { BalanceDisplay } from "@/components/wallet/balance-display";
import { ConnectButton } from "@/components/wallet/connect-button";
import { CHAIN_CONFIGS } from "@/lib/constants";

const navItems = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/agents", label: "Agents", icon: Bot },
];

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const chainCount = Object.keys(CHAIN_CONFIGS).length;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex w-full max-w-7xl flex-col md:flex-row">
        <aside className="border-b border-border bg-card px-4 py-4 md:sticky md:top-0 md:h-screen md:w-72 md:border-b-0 md:border-r md:px-5">
          <div className="mb-4 flex items-center justify-between md:mb-8">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              PocketAgent
            </Link>
          </div>
          <div className="mb-4">
            <ConnectButton />
          </div>
          <nav className="grid grid-cols-3 gap-2 md:grid-cols-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
                >
                  <Icon size={16} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="mt-4 rounded-lg border border-border bg-background p-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Network Setup
            </p>
            <p className="mt-2 text-sm font-medium">{chainCount} chains configured</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Expand chain registry in `src/lib/constants.ts`.
            </p>
          </div>
          <BalanceDisplay className="mt-4" compact />
        </aside>
        <main className="flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bot,
  Gauge,
  Menu,
  MessageSquare,
  Sparkles,
  X,
} from "lucide-react";
import { BalanceDisplay } from "@/components/wallet/balance-display";
import { ConnectButton } from "@/components/wallet/connect-button";
import { RpcBanner } from "@/components/ui/rpc-banner";
import { CHAIN_CONFIGS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/lib/api";

const navItems = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/agents", label: "Agents", icon: Bot },
];

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [rpcDown, setRpcDown] = useState(false);
  const [shortcutsVisible, setShortcutsVisible] = useState(false);
  const chainCount = Object.keys(CHAIN_CONFIGS).length;

  // Close sidebar on route change (mobile) — track previous pathname to avoid
  // calling setState on every render, which triggers react-hooks lint warnings.
  const prevPathname = useRef(pathname);
  useEffect(() => {
    if (prevPathname.current !== pathname) {
      prevPathname.current = pathname;
      setSidebarOpen(false);
    }
  }, [pathname]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;

      // Ctrl+K: New chat (unless typing in an input)
      if ((e.metaKey || e.ctrlKey) && e.key === "k" && !isInput) {
        e.preventDefault();
        router.push("/chat");
        return;
      }

      // Ctrl+/: Show shortcuts palette
      if ((e.metaKey || e.ctrlKey) && e.key === "/" && !isInput) {
        e.preventDefault();
        setShortcutsVisible((prev) => !prev);
        return;
      }

      // Escape: Close sidebar or shortcuts
      if (e.key === "Escape") {
        if (sidebarOpen) setSidebarOpen(false);
        if (shortcutsVisible) setShortcutsVisible(false);
        return;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [router, sidebarOpen, shortcutsVisible]);

  // Check API availability on mount + periodic heartbeat every 30s
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`, {
          signal: AbortSignal.timeout(5000),
        });
        setRpcDown(!res.ok);
      } catch {
        setRpcDown(true);
      }
    };
    check();
    const interval = setInterval(check, 30_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {rpcDown && (
        <RpcBanner
          visible={rpcDown}
          onRetry={async () => {
            try {
              const res = await fetch(`${API_BASE_URL}/health`, { signal: AbortSignal.timeout(5000) });
              setRpcDown(!res.ok);
            } catch { setRpcDown(true); }
          }}
          onDismiss={() => setRpcDown(false)}
        />
      )}

      {/* Mobile header with hamburger */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-card px-4 py-3 md:hidden">
        <Link href="/" className="flex items-center gap-2">
          <Sparkles size={18} className="text-primary" />
          <span className="text-sm font-semibold tracking-tight">
            PocketAgent
          </span>
        </Link>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label={sidebarOpen ? "Close menu" : "Open menu"}
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="mx-auto flex w-full max-w-7xl flex-col md:flex-row">
        {/* Sidebar */}
        <aside
          className={cn(
            "border-border bg-card transition-all duration-300 md:sticky md:top-0 md:h-screen md:border-r",
            "fixed inset-y-0 left-0 z-30 w-72 -translate-x-full md:static md:translate-x-0",
            sidebarOpen && "translate-x-0",
          )}
        >
          <div className="flex h-full flex-col overflow-y-auto px-5 pb-6 pt-6">
            <div className="mb-6 flex items-center justify-between">
              <Link href="/" className="flex items-center gap-2">
                <Sparkles size={20} className="text-primary" />
                <span className="text-base font-semibold tracking-tight">
                  PocketAgent
                </span>
              </Link>
            </div>

            <div className="mb-4">
              <ConnectButton />
            </div>

            <nav className="flex flex-col gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    <Icon size={17} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <div className="mt-4 rounded-lg border border-border bg-background p-3.5">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Network
              </p>
              <p className="mt-2 text-sm font-medium">{chainCount} chains</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Pocket Network RPC
              </p>
            </div>

            <BalanceDisplay className="mt-4" compact />
          </div>
        </aside>

        <main className="flex-1 px-4 py-6 md:px-8 md:py-8">
          {children}
        </main>
      </div>

      {/* Shortcuts palette */}
      {shortcutsVisible && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setShortcutsVisible(false)}
        >
          <div
            className="w-80 rounded-xl border border-border bg-card p-6 shadow-xl animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Keyboard Shortcuts</h2>
              <button
                onClick={() => setShortcutsVisible(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>
            <div className="space-y-3">
              {[
                { keys: "Ctrl+K", desc: "New Chat" },
                { keys: "Ctrl+/", desc: "Show Shortcuts" },
                { keys: "Escape", desc: "Close Modals / Sidebar" },
              ].map((shortcut) => (
                <div
                  key={shortcut.keys}
                  className="flex items-center justify-between"
                >
                  <span className="text-sm text-muted-foreground">
                    {shortcut.desc}
                  </span>
                  <kbd className="rounded-md border border-border bg-muted px-2 py-0.5 text-xs font-medium">
                    {shortcut.keys}
                  </kbd>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

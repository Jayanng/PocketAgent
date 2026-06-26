"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAccount } from "wagmi";
import {
  Bot,
  Gauge,
  Menu,
  MessageSquare,
  WalletCards,
  X,
} from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { BalanceDisplay } from "@/components/wallet/balance-display";
import { ConnectButton } from "@/components/wallet/connect-button";
import { RpcBanner } from "@/components/ui/rpc-banner";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
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
  const { isConnected } = useAccount();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [balancesOpen, setBalancesOpen] = useState(false);
  const [rpcDown, setRpcDown] = useState(false);
  const [shortcutsVisible, setShortcutsVisible] = useState(false);
  const chainCount = Object.keys(CHAIN_CONFIGS).length;

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

      // Escape: Close sidebar or shortcuts or modal
      if (e.key === "Escape") {
        if (sidebarOpen) setSidebarOpen(false);
        if (shortcutsVisible) setShortcutsVisible(false);
        if (balancesOpen) setBalancesOpen(false);
        return;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [router, sidebarOpen, shortcutsVisible, balancesOpen]);

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

  useEffect(() => {
    document.body.style.overflow = sidebarOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [sidebarOpen]);

  return (
    <div className="min-h-[100dvh] bg-background text-foreground flex flex-col">
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

      {/* Global Top Header */}
      <header className="safe-top sticky top-0 z-30 w-full border-b border-border/40 bg-card/60 backdrop-blur-xl transition-all">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-2 px-3 sm:px-4 md:h-16 md:px-8">
          <Logo
            size="md"
            textClassName="hidden text-[15px] text-foreground transition-colors group-hover:text-foreground/90 sm:inline"
          />

          {/* Desktop Navigation */}
          <nav className="hidden items-center gap-1.5 md:flex">
            {navItems.map((item) => {
              const isActive = pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3.5 py-2 text-[13px] font-medium transition-all duration-200",
                    isActive
                      ? "bg-primary/10 text-primary border border-primary/20 shadow-sm shadow-primary/5"
                      : "text-muted-foreground border border-transparent hover:bg-muted/40 hover:text-foreground"
                  )}
                >
                  <Icon size={14} />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Desktop Right Side (Wallet details & connect) */}
          <div className="hidden items-center gap-3 md:flex">
            <ThemeToggle />
            {isConnected && (
              <button
                type="button"
                onClick={() => setBalancesOpen(true)}
                className="flex items-center gap-2 rounded-lg border border-border/60 bg-muted/20 px-3.5 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted/40 hover:text-foreground hover:border-border transition-all duration-200 shadow-sm cursor-pointer"
                title="View multi-chain wallet balances"
              >
                <WalletCards size={14} className="text-primary/70" />
                <span>Balances</span>
              </button>
            )}
            <ConnectButton />
          </div>

          <div className="flex items-center gap-2 md:hidden">
            <ThemeToggle />
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="flex rounded-lg border border-border/60 bg-muted/10 p-2 text-muted-foreground hover:bg-muted/40 hover:text-foreground transition-all"
              aria-label={sidebarOpen ? "Close menu" : "Open menu"}
            >
              {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer Navigation */}
      {sidebarOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close mobile navigation"
          />
          <aside className="safe-top safe-bottom fixed inset-y-0 right-0 z-50 flex w-[min(100vw,20rem)] flex-col justify-between border-l border-border/50 bg-card/95 p-5 shadow-2xl backdrop-blur-xl sm:w-72 md:hidden animate-toast-in">
            <div className="space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-border/40">
                <Logo
                  size="sm"
                  textClassName="text-sm text-foreground"
                  onClick={() => setSidebarOpen(false)}
                />
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="rounded-lg border border-border/60 p-1.5 text-muted-foreground hover:text-foreground"
                >
                  <X size={15} />
                </button>
              </div>

              <nav className="flex flex-col gap-1.5">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setSidebarOpen(false)}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-4 py-3 text-[14px] font-medium transition-all",
                        isActive
                          ? "bg-primary/10 text-primary border border-primary/20 shadow-sm"
                          : "text-muted-foreground border border-transparent hover:bg-muted/40 hover:text-foreground"
                      )}
                    >
                      <Icon size={16} />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>

              {isConnected && (
                <button
                  type="button"
                  onClick={() => {
                    setSidebarOpen(false);
                    setBalancesOpen(true);
                  }}
                  className="w-full flex items-center gap-3 rounded-lg border border-border/60 bg-muted/20 px-4 py-3 text-[14px] font-semibold text-muted-foreground hover:bg-muted/40 hover:text-foreground transition-all cursor-pointer"
                >
                  <WalletCards size={16} className="text-primary/70" />
                  <span>Wallet & Agent Balances</span>
                </button>
              )}
            </div>

            <div className="space-y-4 pt-4 border-t border-border/40">
              <div className="flex items-center justify-between rounded-lg border border-border/30 bg-muted/20 p-3">
                <div>
                  <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/60">Appearance</p>
                  <p className="mt-1 text-xs font-semibold text-foreground">Light / Dark mode</p>
                </div>
                <ThemeToggle />
              </div>

              <div className="rounded-lg bg-muted/20 border border-border/30 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/60">Network Status</p>
                <p className="mt-1 text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                  </span>
                  <span>{chainCount} chains active</span>
                </p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">Pocket Network RPC gateway</p>
              </div>

              <div onClick={() => setSidebarOpen(false)}>
                <ConnectButton layout="vertical" />
              </div>
            </div>
          </aside>
        </>
      )}

      {/* Main Page Layout Container */}
      <main
        className={cn(
          "w-full flex-1 min-h-0 app-main-mobile",
          pathname.startsWith("/chat")
            ? "h-[calc(100dvh-3.5rem-4.5rem)] p-0 md:h-[calc(100dvh-4rem)]"
            : "mx-auto max-w-7xl px-3 py-4 sm:px-4 sm:py-6 md:px-8 md:py-8"
        )}
      >
        {children}
      </main>

      <nav
        className="mobile-bottom-nav safe-bottom fixed inset-x-0 bottom-0 z-30 border-t border-border/40 bg-card/95 backdrop-blur-xl md:hidden"
        aria-label="Mobile navigation"
      >
        <div className="mx-auto grid max-w-lg grid-cols-3 gap-1 px-2 pt-2">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex min-h-11 flex-col items-center justify-center gap-0.5 rounded-xl px-2 py-1.5 text-[10px] font-semibold transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted/40 hover:text-foreground",
                )}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Balances Details Modal/Dialog */}
      <Dialog open={balancesOpen} onOpenChange={setBalancesOpen}>
        <DialogContent className="max-w-md bg-card/90 backdrop-blur-xl border border-border/50 shadow-2xl rounded-2xl">
          <DialogHeader
            title="RPC Balances"
            description="Live native balances queried through decentralized Pocket Network gateway."
            onClose={() => setBalancesOpen(false)}
          />
          <div className="p-4 max-h-[70vh] overflow-y-auto">
            <BalanceDisplay className="border-0 bg-transparent p-0" />
          </div>
        </DialogContent>
      </Dialog>

      {/* Keyboard Shortcuts Palette */}
      {shortcutsVisible && (
        <Dialog open={shortcutsVisible} onOpenChange={setShortcutsVisible}>
          <DialogContent className="max-w-xs bg-card/90 backdrop-blur-xl border border-border/50 shadow-2xl rounded-xl">
            <DialogHeader title="Keyboard Shortcuts" onClose={() => setShortcutsVisible(false)} />
            <div className="p-4 space-y-3.5">
              {[
                { keys: "Ctrl+K", desc: "New Chat" },
                { keys: "Ctrl+/", desc: "Show Shortcuts" },
                { keys: "Escape", desc: "Close Modals / Sidebar" },
              ].map((shortcut) => (
                <div key={shortcut.keys} className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{shortcut.desc}</span>
                  <kbd className="rounded border border-border/60 bg-muted/40 px-1.5 py-0.5 font-mono font-medium text-[10px]">
                    {shortcut.keys}
                  </kbd>
                </div>
              ))}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

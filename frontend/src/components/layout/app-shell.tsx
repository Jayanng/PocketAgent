"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Gauge,
  MessageSquare,
  Bot,
  CalendarClock,
} from "lucide-react";
import { SiteHeader } from "@/components/layout/site-header";
import { RpcBanner } from "@/components/ui/rpc-banner";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/lib/api";
import { useAgentStore } from "@/store/agent-store";

const navItems = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/scheduled-tasks", label: "Automations", icon: CalendarClock },
] as const;

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [rpcDown, setRpcDown] = useState(false);
  const [shortcutsVisible, setShortcutsVisible] = useState(false);
  const loadAgents = useAgentStore((state) => state.loadAgents);

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

      // Escape: Close shortcuts palette
      if (e.key === "Escape") {
        if (shortcutsVisible) setShortcutsVisible(false);
        return;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [router, shortcutsVisible]);

  useEffect(() => {
    if (
      pathname.startsWith("/chat") ||
      pathname.startsWith("/agents") ||
      pathname.startsWith("/dashboard") ||
      pathname.startsWith("/scheduled-tasks")
    ) {
      void loadAgents();
    }
  }, [pathname, loadAgents]);

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

  const isChat = pathname.startsWith("/chat");

  // Lock the document scroll on chat — only the message pane scrolls (Claude-style).
  useEffect(() => {
    if (!isChat) return;
    const previous = document.documentElement.style.overflow;
    document.documentElement.style.overflow = "hidden";
    return () => {
      document.documentElement.style.overflow = previous;
    };
  }, [isChat]);

  return (
    <div
      className={cn(
        "bg-background text-foreground flex flex-col",
        isChat ? "h-dvh overflow-hidden" : "min-h-[100dvh]",
      )}
    >
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

      <SiteHeader />

      {/* Main Page Layout Container */}
      <main
        className={cn(
          "w-full min-h-0 flex-1",
          isChat
            ? "flex flex-col overflow-hidden p-0 pb-[calc(4.5rem+env(safe-area-inset-bottom,0px))] md:pb-0"
            : "app-main-mobile mx-auto max-w-7xl px-3 py-4 sm:px-4 sm:py-6 md:px-8 md:py-8",
        )}
      >
        {children}
      </main>

      <nav
        className="mobile-bottom-nav safe-bottom fixed inset-x-0 bottom-0 z-30 border-t border-border/40 bg-card/95 backdrop-blur-xl md:hidden"
        aria-label="Mobile navigation"
      >
        <div className="mx-auto grid max-w-lg grid-cols-4 gap-1 px-2 pt-2">
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

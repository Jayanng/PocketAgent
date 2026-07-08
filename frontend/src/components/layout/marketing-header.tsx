"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowRight, Menu, X } from "lucide-react";

import { Logo } from "@/components/brand/logo";
import { SITE_NAV_ITEMS } from "@/components/layout/nav-items";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { CHAIN_CONFIGS } from "@/lib/constants";
import { cn } from "@/lib/utils";

function navLinkClassName(isActive: boolean, isLanding: boolean, size: "desktop" | "mobile") {
  const base =
    size === "desktop"
      ? "flex items-center gap-2 rounded-lg px-3.5 py-2 text-[13px] font-medium transition-all duration-200"
      : "flex items-center gap-3 rounded-lg px-4 py-3 text-[14px] font-medium transition-all duration-200";

  if (isActive) {
    return cn(
      base,
      "border border-primary/20 bg-primary/10 text-primary shadow-sm shadow-primary/5",
    );
  }

  return cn(
    base,
    "border border-transparent text-muted-foreground",
    isLanding
      ? "hover:border-primary/30 hover:bg-primary/10 hover:text-primary hover:shadow-sm hover:shadow-primary/10"
      : "hover:bg-muted/40 hover:text-foreground",
  );
}

/** Lightweight header for /docs — no RainbowKit/Wagmi bundle. */
export function MarketingHeader() {
  const pathname = usePathname();
  const isLanding = pathname === "/";
  const isDocs = pathname.startsWith("/docs");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [lastPathname, setLastPathname] = useState(pathname);
  const chainCount = Object.keys(CHAIN_CONFIGS).length;

  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setSidebarOpen(false);
  }

  useEffect(() => {
    document.body.style.overflow = sidebarOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [sidebarOpen]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && sidebarOpen) {
        setSidebarOpen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [sidebarOpen]);

  return (
    <>
      <header className="safe-top sticky top-0 z-30 w-full border-b border-border/40 bg-card/60 backdrop-blur-xl transition-all">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-2 px-3 sm:px-4 md:h-16 md:px-8">
          <Logo
            size="md"
            textClassName="hidden text-[15px] text-foreground transition-colors group-hover:text-foreground/90 sm:inline"
          />

          <nav className="hidden items-center gap-1.5 md:flex">
            {SITE_NAV_ITEMS.map((item) => {
              const isActive = pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={navLinkClassName(isActive, isLanding || isDocs, "desktop")}
                >
                  <Icon size={14} />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="hidden items-center gap-3 md:flex">
            <ThemeToggle />
            <Link
              href="/agents"
              className="inline-flex items-center gap-1.5 rounded-lg border border-primary/25 bg-primary/10 px-3.5 py-2 text-xs font-semibold text-primary transition hover:bg-primary/15"
            >
              Open App
              <ArrowRight size={13} />
            </Link>
          </div>

          <div className="flex items-center gap-2 md:hidden">
            <ThemeToggle />
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="flex rounded-lg border border-border/60 bg-muted/10 p-2 text-muted-foreground transition-all hover:bg-muted/40 hover:text-foreground"
              aria-label={sidebarOpen ? "Close menu" : "Open menu"}
            >
              {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
      </header>

      {sidebarOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close mobile navigation"
          />
          <aside className="safe-top safe-bottom fixed inset-y-0 right-0 z-50 flex w-[min(100vw,20rem)] animate-toast-in flex-col justify-between border-l border-border/50 bg-card/95 p-5 shadow-2xl backdrop-blur-xl sm:w-72 md:hidden">
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-border/40 pb-4">
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
                {SITE_NAV_ITEMS.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setSidebarOpen(false)}
                      className={navLinkClassName(isActive, isLanding || isDocs, "mobile")}
                    >
                      <Icon size={16} />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>

            <div className="space-y-4 border-t border-border/40 pt-4">
              <div className="rounded-lg border border-border/30 bg-muted/20 p-3">
                <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/60">
                  Network Status
                </p>
                <p className="mt-1 text-xs font-semibold text-foreground">{chainCount} chains active</p>
              </div>
              <Link
                href="/agents"
                onClick={() => setSidebarOpen(false)}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground"
              >
                Open App
                <ArrowRight size={15} />
              </Link>
            </div>
          </aside>
        </>
      )}
    </>
  );
}
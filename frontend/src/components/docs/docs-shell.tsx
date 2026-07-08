"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { BookOpen, ExternalLink, Menu, Search, X } from "lucide-react";
import { MarketingHeader } from "@/components/layout/marketing-header";
import { useLandingTheme } from "@/hooks/use-landing-theme";
import { DOCS_EXTERNAL_LINKS, DOCS_FLAT_LINKS, DOCS_NAV, DOCS_VERSION } from "@/lib/docs/nav";
import { cn } from "@/lib/utils";

function GradientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 landing-grid-pattern opacity-30" />
      <div className="landing-orb-blue absolute -left-40 -top-40 h-[400px] w-[400px] rounded-full blur-[120px]" />
      <div className="landing-orb-accent absolute -right-40 bottom-0 h-[300px] w-[300px] rounded-full blur-[100px]" />
    </div>
  );
}

function isActivePath(pathname: string, href: string) {
  if (href === "/docs") return pathname === "/docs";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function DocsShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme } = useLandingTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [lastPathname, setLastPathname] = useState(pathname);

  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setMobileOpen(false);
  }

  const filteredLinks = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return null;
    return DOCS_FLAT_LINKS.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.href.toLowerCase().includes(q) ||
        item.description?.toLowerCase().includes(q),
    );
  }, [query]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="mb-4 flex items-center gap-2 px-1">
        <BookOpen size={16} className="text-emerald-400/80" />
        <div>
          <p className="text-[13px] font-semibold">Documentation</p>
          <p className="text-[10px] opacity-50">pokt-agent-mcp v{DOCS_VERSION}</p>
        </div>
      </div>

      <div className="relative mb-4">
        <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-40" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search docs..."
          className="w-full rounded-lg border border-white/10 bg-black/20 py-2 pl-9 pr-3 text-[12px] outline-none transition placeholder:opacity-40 focus:border-white/25"
        />
      </div>

      {filteredLinks ? (
        <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {filteredLinks.length === 0 ? (
            <p className="px-2 py-4 text-[12px] opacity-50">No results for &ldquo;{query}&rdquo;</p>
          ) : (
            filteredLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setQuery("")}
                className={cn(
                  "block rounded-lg px-3 py-2 text-[12px] transition",
                  isActivePath(pathname, item.href)
                    ? "bg-white/10 font-medium opacity-100"
                    : "opacity-60 hover:bg-white/5 hover:opacity-100",
                )}
              >
                <span className="block font-medium">{item.title}</span>
                {item.description && (
                  <span className="mt-0.5 block text-[11px] opacity-60">{item.description}</span>
                )}
              </Link>
            ))
          )}
        </nav>
      ) : (
        <nav className="min-h-0 flex-1 space-y-6 overflow-y-auto pr-1">
          {DOCS_NAV.map((section) => (
            <div key={section.title}>
              <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-widest opacity-45">
                {section.title}
              </p>
              <div className="space-y-0.5">
                {section.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "block rounded-lg px-3 py-1.5 text-[12px] font-medium transition",
                      isActivePath(pathname, item.href)
                        ? "bg-emerald-400/10 text-emerald-300"
                        : "opacity-60 hover:bg-white/5 hover:opacity-100",
                    )}
                  >
                    {item.title}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>
      )}

      <div className="mt-4 space-y-2 border-t border-white/10 pt-4">
        {DOCS_EXTERNAL_LINKS.map((link) => (
          <a
            key={link.href}
            href={link.href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-[12px] font-medium opacity-50 transition hover:opacity-100"
          >
            {link.title}
            <ExternalLink size={11} />
          </a>
        ))}
      </div>
    </div>
  );

  return (
    <div className="landing-page relative min-h-[100dvh]" data-landing-theme={theme}>
      <GradientBackground />
      <MarketingHeader />

      <div className="relative z-10 mx-auto max-w-7xl px-4 pb-24 pt-6 sm:px-6 md:pt-8">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="mb-4 inline-flex items-center gap-2 rounded-lg border border-white/15 bg-black/20 px-3 py-2 text-[13px] font-medium lg:hidden"
        >
          <Menu size={16} />
          Docs menu
        </button>

        <div className="flex gap-10">
          <aside className="hidden w-56 shrink-0 lg:block">
            <div className="sticky top-24 max-h-[calc(100dvh-7rem)] overflow-hidden">{sidebar}</div>
          </aside>

          <main className="min-w-0 flex-1">{children}</main>
        </div>
      </div>

      {mobileOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Close docs menu"
          />
          <aside className="safe-top safe-bottom fixed inset-y-0 left-0 z-50 flex w-[min(100vw,18rem)] flex-col border-r border-white/10 bg-[#0a0f14]/95 p-5 shadow-2xl backdrop-blur-xl lg:hidden">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-[13px] font-semibold">Docs</span>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="rounded-lg border border-white/15 p-1.5 opacity-70"
              >
                <X size={16} />
              </button>
            </div>
            <div className="min-h-0 flex-1">{sidebar}</div>
          </aside>
        </>
      )}
    </div>
  );
}
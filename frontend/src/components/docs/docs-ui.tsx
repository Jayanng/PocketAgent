"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { ArrowLeft, ArrowRight, Check, Copy, Info, AlertTriangle, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DocsNavLink } from "@/lib/docs/nav";

export function DocsPageHeader({
  title,
  description,
  version,
}: {
  title: string;
  description?: string;
  version?: string;
}) {
  return (
    <header className="mb-10 border-b border-white/10 pb-8">
      {version && (
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-emerald-400/80">
          Package v{version}
        </p>
      )}
      <h1 className="text-[clamp(1.75rem,4vw,2.5rem)] font-bold leading-[1.15] tracking-tight">
        {title}
      </h1>
      {description && (
        <p className="mt-3 max-w-2xl text-[15px] leading-relaxed opacity-65">{description}</p>
      )}
    </header>
  );
}

export function DocsProse({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("docs-prose space-y-6 text-[14px] leading-relaxed opacity-85", className)}>
      {children}
    </div>
  );
}

export function DocsH2({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <h2 id={id} className="docs-h2 mt-12 scroll-mt-28 text-xl font-bold tracking-tight first:mt-0">
      {children}
    </h2>
  );
}

export function DocsH3({ children }: { children: ReactNode }) {
  return <h3 className="docs-h3 mt-8 text-[15px] font-semibold">{children}</h3>;
}

export function DocsP({ children }: { children: ReactNode }) {
  return <p className="opacity-80">{children}</p>;
}

export function DocsUl({ children }: { children: ReactNode }) {
  return <ul className="list-disc space-y-2 pl-5 opacity-80">{children}</ul>;
}

export function DocsOl({ children }: { children: ReactNode }) {
  return <ol className="list-decimal space-y-2 pl-5 opacity-80">{children}</ol>;
}

export function DocsLi({ children }: { children: ReactNode }) {
  return <li>{children}</li>;
}

export function DocsInlineCode({ children }: { children: ReactNode }) {
  return (
    <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[12px]">{children}</code>
  );
}

export function DocsLink({
  href,
  children,
  external,
}: {
  href: string;
  children: ReactNode;
  external?: boolean;
}) {
  const className = "underline decoration-white/25 underline-offset-2 transition hover:opacity-100";
  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={className}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="absolute right-3 top-3 rounded-md p-1.5 opacity-50 transition hover:bg-white/10 hover:opacity-100"
      aria-label="Copy to clipboard"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
}

export function CodeBlock({ children }: { children: string }) {
  return (
    <div className="group relative my-4">
      <CopyButton text={children} />
      <pre className="overflow-x-auto rounded-xl border border-white/10 bg-black/35 px-4 py-3.5 font-mono text-[12px] leading-relaxed">
        <code>{children}</code>
      </pre>
    </div>
  );
}

const CALLOUT_STYLES = {
  info: { icon: Info, border: "border-sky-400/30", bg: "bg-sky-400/5", iconColor: "text-sky-400" },
  warning: { icon: AlertTriangle, border: "border-amber-400/30", bg: "bg-amber-400/5", iconColor: "text-amber-400" },
  tip: { icon: Lightbulb, border: "border-emerald-400/30", bg: "bg-emerald-400/5", iconColor: "text-emerald-400" },
} as const;

export function Callout({
  type = "info",
  title,
  children,
}: {
  type?: keyof typeof CALLOUT_STYLES;
  title?: string;
  children: ReactNode;
}) {
  const style = CALLOUT_STYLES[type];
  const Icon = style.icon;
  return (
    <div className={cn("my-6 flex gap-3 rounded-xl border p-4", style.border, style.bg)}>
      <Icon size={18} className={cn("mt-0.5 shrink-0", style.iconColor)} />
      <div className="min-w-0 text-[13px] leading-relaxed">
        {title && <p className="mb-1 font-semibold">{title}</p>}
        <div className="opacity-80">{children}</div>
      </div>
    </div>
  );
}

export function MethodBadge({ method }: { method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" }) {
  const colors = {
    GET: "bg-sky-400/10 text-sky-400",
    POST: "bg-emerald-400/10 text-emerald-400",
    PUT: "bg-amber-400/10 text-amber-400",
    PATCH: "bg-violet-400/10 text-violet-400",
    DELETE: "bg-red-400/10 text-red-400",
  };
  return (
    <span className={cn("rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold", colors[method])}>
      {method}
    </span>
  );
}

export function ApiEndpoint({
  method,
  path,
  auth,
  description,
  children,
}: {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  auth?: "none" | "token";
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="my-6 rounded-xl border border-white/10 bg-white/[0.02] p-5">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <MethodBadge method={method} />
        <code className="font-mono text-[13px]">{path}</code>
        {auth === "token" && (
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide opacity-60">
            X-Agent-Access-Token
          </span>
        )}
      </div>
      <p className="text-[13px] opacity-75">{description}</p>
      {children && <div className="mt-4 space-y-3 border-t border-white/10 pt-4">{children}</div>}
    </div>
  );
}

export function DocsTable({ children }: { children: ReactNode }) {
  return (
    <div className="my-6 overflow-x-auto rounded-xl border border-white/10">
      <table className="w-full min-w-[32rem] text-left text-[13px]">{children}</table>
    </div>
  );
}

export function DocsCardGrid({ children }: { children: ReactNode }) {
  return <div className="my-6 grid gap-4 sm:grid-cols-2">{children}</div>;
}

export function DocsCard({
  title,
  href,
  description,
}: {
  title: string;
  href: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-xl border border-white/10 bg-white/[0.02] p-5 transition hover:border-white/20 hover:bg-white/[0.04]"
    >
      <h3 className="text-[15px] font-semibold group-hover:text-emerald-300">{title}</h3>
      <p className="mt-2 text-[13px] opacity-60">{description}</p>
    </Link>
  );
}

export function DocsPager({ prev, next }: { prev: DocsNavLink | null; next: DocsNavLink | null }) {
  if (!prev && !next) return null;
  return (
    <nav className="mt-16 flex flex-col gap-3 border-t border-white/10 pt-8 sm:flex-row sm:justify-between">
      {prev ? (
        <Link
          href={prev.href}
          className="group flex flex-col rounded-xl border border-white/10 p-4 transition hover:border-white/20 hover:bg-white/[0.03] sm:max-w-[48%]"
        >
          <span className="mb-1 flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide opacity-50">
            <ArrowLeft size={12} /> Previous
          </span>
          <span className="text-[14px] font-semibold group-hover:text-emerald-300">{prev.title}</span>
        </Link>
      ) : (
        <div />
      )}
      {next ? (
        <Link
          href={next.href}
          className="group flex flex-col rounded-xl border border-white/10 p-4 text-right transition hover:border-white/20 hover:bg-white/[0.03] sm:max-w-[48%]"
        >
          <span className="mb-1 flex items-center justify-end gap-1 text-[11px] font-medium uppercase tracking-wide opacity-50">
            Next <ArrowRight size={12} />
          </span>
          <span className="text-[14px] font-semibold group-hover:text-emerald-300">{next.title}</span>
        </Link>
      ) : null}
    </nav>
  );
}
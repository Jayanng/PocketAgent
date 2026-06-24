"use client";

import { useMemo, useState } from "react";
import { AlertCircle, ChevronDown, HeartPulse, RefreshCw, Zap } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api, type ChainHealth as ChainHealthType, type ChainHealthEntry } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const REFRESH_MS = 30_000;
const PREVIEW_COUNT = 8;

const PROTOCOL_ORDER = ["evm", "cosmos", "solana", "sui", "near", "tron"] as const;
const PROTOCOL_LABEL: Record<string, string> = {
  evm: "EVM",
  cosmos: "Cosmos",
  solana: "Solana",
  sui: "Sui",
  near: "Near",
  tron: "Tron",
};

const STATUS_LABEL: Record<string, string> = {
  green: "Healthy",
  yellow: "Degraded",
  red: "Down",
  registered: "On registry",
};

export function ChainHealth() {
  const [probeAll, setProbeAll] = useState(false);
  const [selectedProtocol, setSelectedProtocol] = useState<string>("all");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["analytics", "chain-health", probeAll],
    queryFn: () => api.analytics.chainHealth(probeAll),
    refetchInterval: probeAll ? false : REFRESH_MS,
    staleTime: REFRESH_MS,
  });

  const checkAll = () => setProbeAll(true);
  const refresh = () => {
    setProbeAll(false);
    void refetch();
  };

  const toggleSection = (protocol: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(protocol)) next.delete(protocol);
      else next.add(protocol);
      return next;
    });
  };

  // Group chains by protocol, in the fixed display order, with optional selection filter.
  const grouped = useMemo(() => {
    const map = new Map<string, ChainHealthEntry[]>();
    for (const chain of data?.chains ?? []) {
      if (selectedProtocol !== "all" && chain.protocol !== selectedProtocol) {
        continue;
      }
      const list = map.get(chain.protocol) ?? [];
      list.push(chain);
      map.set(chain.protocol, list);
    }
    return PROTOCOL_ORDER.filter((p) => map.has(p)).map((p) => ({
      protocol: p,
      label: PROTOCOL_LABEL[p],
      chains: map.get(p) ?? [],
    }));
  }, [data, selectedProtocol]);

  const summary = data
    ? `${data.healthy} live · ${data.registered} on registry · ${data.total} total`
    : "loading…";

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-6 shadow-sm space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border/30 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
            <HeartPulse size={18} className="text-primary" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground/80 font-mono">Chain Latency Diagnostics</h2>
            <p className="text-[11px] text-muted-foreground">{summary}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <Button
            variant="primary"
            size="sm"
            onClick={checkAll}
            disabled={probeAll && isFetching}
            title="Probe every chain in the registry live via Pocket RPC"
            className="text-xs h-8"
          >
            <Zap size={13} />
            {probeAll && isFetching ? "Probing 52…" : "Check all chains"}
          </Button>
          <Button variant="secondary" size="icon" onClick={refresh} title="Refresh headline chains" className="h-8 w-8">
            <RefreshCw size={13} className={isFetching ? "animate-spin" : undefined} />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2.5 text-sm text-red-500 bg-red-500/5 border border-red-500/10 rounded-lg p-4 font-mono">
          <AlertCircle className="mt-0.5 shrink-0" size={15} />
          <span>{error instanceof Error ? error.message : "Failed to load chain health"}</span>
        </div>
      ) : isLoading && !data ? (
        <p className="text-xs text-muted-foreground font-mono py-6">Probing chains via Pocket RPC…</p>
      ) : data ? (
        <div className="space-y-6">
          {/* Controls Bar: Protocol Filters & Legend */}
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            {/* Protocol Tabs */}
            <div className="flex flex-wrap border border-border/60 rounded-md p-0.5 bg-muted/40 max-w-max">
              <button
                type="button"
                className={cn(
                  "px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded transition-colors",
                  selectedProtocol === "all"
                    ? "bg-card text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                )}
                onClick={() => setSelectedProtocol("all")}
              >
                All Protocols
              </button>
              {PROTOCOL_ORDER.map((p) => (
                <button
                  key={p}
                  type="button"
                  className={cn(
                    "px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded transition-colors",
                    selectedProtocol === p
                      ? "bg-card text-foreground shadow-xs font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                  onClick={() => setSelectedProtocol(p)}
                >
                  {PROTOCOL_LABEL[p]}
                </button>
              ))}
            </div>

            {/* Status Legend */}
            <div className="flex flex-wrap gap-x-4 gap-y-2 text-[10px] font-mono text-muted-foreground">
              <Legend dot="bg-green-500 shadow-[0_0_5px_var(--state-success)] animate-pulse-soft" label="Healthy" />
              <Legend dot="bg-amber-500 shadow-[0_0_5px_oklch(62%_0.14_180)]" label="Degraded" />
              <Legend dot="bg-red-500 shadow-[0_0_5px_var(--state-error)]" label="Down" />
              <Legend dot="bg-slate-400/50" label="Registered" />
            </div>
          </div>

          {/* Grouped Chains List */}
          <div className="space-y-6">
            {grouped.map((section) => {
              const isExpanded = expanded.has(section.protocol);
              const visible = isExpanded ? section.chains : section.chains.slice(0, PREVIEW_COUNT);
              const hiddenCount = section.chains.length - visible.length;
              const liveCount = section.chains.filter(
                (c) => c.status === "green" || c.status === "yellow" || c.status === "red"
              ).length;

              return (
                <div key={section.protocol} className="space-y-3">
                  <div className="flex items-center justify-between border-l-2 border-primary/40 pl-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80 font-mono">
                      {section.label}
                    </h3>
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {section.chains.length} chains{liveCount > 0 ? ` · ${liveCount} live` : ""}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                    {visible.map((c) => (
                      <ChainCard key={c.chain} entry={c} />
                    ))}
                  </div>

                  {hiddenCount > 0 && (
                    <button
                      type="button"
                      onClick={() => toggleSection(section.protocol)}
                      className="mt-1 inline-flex items-center gap-1 text-[11px] font-mono font-medium text-primary hover:underline"
                    >
                      <ChevronDown size={11} className={cn("transition-transform duration-200", isExpanded ? "rotate-180" : "")} />
                      {isExpanded ? "Show less" : `See ${hiddenCount} more`}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ChainCard({ entry }: { entry: ChainHealthEntry }) {
  return (
    <div className="rounded-lg border border-border/40 bg-muted/20 p-3.5 space-y-1.5 hover:border-border/80 hover:bg-muted/30 transition-colors">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-xs font-semibold tracking-tight text-foreground/90" title={entry.name}>
          {entry.name}
        </span>
        <span
          className={cn(
            "h-1.5 w-1.5 shrink-0 rounded-full",
            entry.status === "green" && "bg-green-500 shadow-[0_0_5px_var(--state-success)] animate-pulse-soft",
            entry.status === "yellow" && "bg-amber-500 shadow-[0_0_5px_oklch(62%_0.14_180)]",
            entry.status === "red" && "bg-red-500 shadow-[0_0_5px_var(--state-error)]",
            entry.status === "registered" && "bg-slate-400/50"
          )}
          title={STATUS_LABEL[entry.status]}
        />
      </div>

      <div className="flex items-baseline justify-between text-[10px] font-mono text-muted-foreground">
        <span>
          {entry.block_height
            ? `#${entry.block_height.toLocaleString()}`
            : entry.status === "registered"
              ? "configured"
              : "—"}
        </span>
        <span>
          {entry.latency_ms != null
            ? `${entry.latency_ms} ms`
            : entry.status === "registered"
              ? entry.protocol
              : entry.error ?? "unreachable"}
        </span>
      </div>
    </div>
  );
}

function Legend({ dot, label }: { dot: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
      {label}
    </span>
  );
}

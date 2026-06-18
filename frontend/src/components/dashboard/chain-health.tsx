"use client";

import { useMemo, useState } from "react";
import { AlertCircle, ChevronDown, HeartPulse, RefreshCw, Zap } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api, type ChainHealth, type ChainHealthEntry } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

const REFRESH_MS = 30_000;
const PREVIEW_COUNT = 8; // cards shown per section before "see more"

// Fixed display order: the 7 protocol families, biggest first.
const PROTOCOL_ORDER = ["evm", "cosmos", "solana", "sui", "near", "tron"] as const;
const PROTOCOL_LABEL: Record<string, string> = {
  evm: "EVM",
  cosmos: "Cosmos",
  solana: "Solana",
  sui: "Sui",
  near: "Near",
  tron: "Tron",
};

const STATUS_DOT: Record<string, string> = {
  green: "bg-green-500",
  yellow: "bg-amber-500",
  red: "bg-red-500",
  registered: "bg-slate-300",
};

const STATUS_LABEL: Record<string, string> = {
  green: "Healthy",
  yellow: "Degraded",
  red: "Down",
  registered: "On registry",
};

export function ChainHealth() {
  // `probeAll` flips true when the user clicks "Check all chains" — it drives
  // the query key (live=true) for a one-off full 52-chain probe. The refresh
  // button (or any timeframe tick) resets it to the cheap headline poll.
  const [probeAll, setProbeAll] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["analytics", "chain-health", probeAll],
    queryFn: () => api.analytics.chainHealth(probeAll),
    // Auto-refresh the cheap headline poll every 30s; never auto-re-run the
    // expensive full 52-chain probe.
    refetchInterval: probeAll ? false : REFRESH_MS,
    staleTime: REFRESH_MS,
  });

  const checkAll = () => setProbeAll(true);
  // Refresh returns to the headline poll (live=false) and refetches.
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

  // Group chains by protocol, in the fixed display order.
  const grouped = useMemo(() => {
    const map = new Map<string, ChainHealthEntry[]>();
    for (const chain of data?.chains ?? []) {
      const list = map.get(chain.protocol) ?? [];
      list.push(chain);
      map.set(chain.protocol, list);
    }
    return PROTOCOL_ORDER.filter((p) => map.has(p)).map((p) => ({
      protocol: p,
      label: PROTOCOL_LABEL[p],
      chains: map.get(p) ?? [],
    }));
  }, [data]);

  const summary = data
    ? `${data.healthy} live · ${data.registered} on registry · ${data.total} total`
    : "loading…";

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <HeartPulse size={16} className="text-primary" />
          <h2 className="text-sm font-semibold">Chain Health</h2>
          <span className="text-xs text-muted-foreground">{summary}</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="primary"
            size="sm"
            onClick={checkAll}
            disabled={probeAll && isFetching}
            title="Probe every chain in the registry live via Pocket RPC"
          >
            <Zap size={14} />
            {probeAll && isFetching ? "Probing 52…" : "Check all chains"}
          </Button>
          <Button variant="secondary" size="icon" onClick={refresh} title="Refresh headline chains">
            <RefreshCw size={14} className={isFetching ? "animate-spin" : undefined} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex items-start gap-2 text-sm text-red-600">
            <AlertCircle className="mt-0.5 shrink-0" size={14} />
            <span>{error instanceof Error ? error.message : "Failed to load chain health"}</span>
          </div>
        ) : isLoading && !data ? (
          <p className="text-sm text-muted-foreground">Probing chains via Pocket RPC…</p>
        ) : data ? (
          <>
            <div className="mb-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
              <Legend dot="bg-green-500" label="Healthy (live)" />
              <Legend dot="bg-amber-500" label="Degraded" />
              <Legend dot="bg-red-500" label="Down" />
              <Legend dot="bg-slate-300" label="On registry" />
            </div>

            <div className="space-y-5">
              {grouped.map((section) => {
                const isExpanded = expanded.has(section.protocol);
                const visible = isExpanded ? section.chains : section.chains.slice(0, PREVIEW_COUNT);
                const hiddenCount = section.chains.length - visible.length;
                const liveCount = section.chains.filter(
                  (c) => c.status === "green" || c.status === "yellow" || c.status === "red"
                ).length;

                return (
                  <div key={section.protocol}>
                    <div className="mb-2 flex items-baseline justify-between">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        {section.label}
                        <span className="ml-2 font-normal text-muted-foreground/70">
                          {section.chains.length} chains{liveCount > 0 ? ` · ${liveCount} live` : ""}
                        </span>
                      </h3>
                    </div>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                      {visible.map((c) => (
                        <ChainCard key={c.chain} entry={c} />
                      ))}
                    </div>
                    {hiddenCount > 0 && (
                      <button
                        type="button"
                        onClick={() => toggleSection(section.protocol)}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                      >
                        <ChevronDown size={12} className={isExpanded ? "rotate-180 transition-transform" : "transition-transform"} />
                        {isExpanded ? "Show less" : `See ${hiddenCount} more`}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ChainCard({ entry }: { entry: ChainHealthEntry }) {
  return (
    <div className="rounded-md border border-border bg-muted/40 p-3">
      <div className="flex items-center justify-between">
        <span className="truncate text-sm font-medium" title={entry.name}>
          {entry.name}
        </span>
        <span
          className={`h-2 w-2 shrink-0 rounded-full ${STATUS_DOT[entry.status]}`}
          title={STATUS_LABEL[entry.status]}
        />
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {entry.block_height
          ? `#${entry.block_height.toLocaleString()}`
          : entry.status === "registered"
            ? "configured"
            : "—"}
      </p>
      <p className="text-xs text-muted-foreground">
        {entry.latency_ms != null
          ? `${entry.latency_ms} ms`
          : entry.status === "registered"
            ? entry.protocol
            : entry.error ?? "unreachable"}
      </p>
    </div>
  );
}

function Legend({ dot, label }: { dot: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

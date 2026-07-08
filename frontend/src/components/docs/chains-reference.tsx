"use client";

import { useMemo, useState } from "react";
import { CHAIN_CONFIGS, type ChainProtocol } from "@/lib/constants";
import { DocsH2, DocsP, DocsTable } from "@/components/docs/docs-ui";

const PROTOCOLS: ChainProtocol[] = ["evm", "cosmos", "solana", "sui", "near", "tron"];

export function ChainsReference() {
  const [query, setQuery] = useState("");
  const [protocol, setProtocol] = useState<ChainProtocol | "all">("all");

  const chains = useMemo(() => Object.values(CHAIN_CONFIGS), []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return chains.filter((c) => {
      if (protocol !== "all" && c.protocol !== protocol) return false;
      if (!q) return true;
      return (
        c.key.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.symbol.toLowerCase().includes(q) ||
        String(c.chainId).toLowerCase().includes(q)
      );
    });
  }, [chains, query, protocol]);

  const byProtocol = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const c of chains) {
      counts[c.protocol] = (counts[c.protocol] ?? 0) + 1;
    }
    return counts;
  }, [chains]);

  return (
    <div className="space-y-6 text-[14px]">
      <DocsP>
        {chains.length} production networks across {PROTOCOLS.length} protocol families. All RPC traffic
        routes through Pocket Network gateways (<code className="font-mono text-[12px]">*.api.pocket.network</code>).
      </DocsP>

      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {PROTOCOLS.map((p) => (
          <div key={p} className="rounded-xl border border-white/10 p-3 text-center">
            <p className="text-[11px] font-semibold uppercase tracking-wide opacity-50">{p}</p>
            <p className="mt-1 text-xl font-bold">{byProtocol[p] ?? 0}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name, key, symbol, chain ID..."
          className="min-w-[12rem] flex-1 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-[13px] outline-none focus:border-white/25"
        />
        <select
          value={protocol}
          onChange={(e) => setProtocol(e.target.value as ChainProtocol | "all")}
          className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-[13px] outline-none"
        >
          <option value="all">All protocols</option>
          {PROTOCOLS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      <DocsH2 id="table">Chain table ({filtered.length})</DocsH2>
      <DocsTable>
        <thead>
          <tr className="border-b border-white/10 bg-white/[0.02]">
            <th className="px-4 py-3 font-semibold">Key</th>
            <th className="px-4 py-3 font-semibold">Name</th>
            <th className="px-4 py-3 font-semibold">Protocol</th>
            <th className="px-4 py-3 font-semibold">Chain ID</th>
            <th className="px-4 py-3 font-semibold">Symbol</th>
            <th className="px-4 py-3 font-semibold">RPC</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((c) => (
            <tr key={c.key} className="border-b border-white/5">
              <td className="px-4 py-2.5 font-mono text-[12px]">{c.key}</td>
              <td className="px-4 py-2.5 text-[12px]">{c.name}</td>
              <td className="px-4 py-2.5 text-[12px] uppercase opacity-60">{c.protocol}</td>
              <td className="px-4 py-2.5 font-mono text-[11px] opacity-75">{c.chainId}</td>
              <td className="px-4 py-2.5 text-[12px]">{c.symbol}</td>
              <td className="max-w-[10rem] truncate px-4 py-2.5 font-mono text-[10px] opacity-50" title={c.rpcEndpoint}>
                {c.rpcEndpoint.replace("https://", "")}
              </td>
            </tr>
          ))}
        </tbody>
      </DocsTable>
    </div>
  );
}
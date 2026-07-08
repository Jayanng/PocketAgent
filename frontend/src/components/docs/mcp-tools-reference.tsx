"use client";

import { useMemo, useState } from "react";
import { MCP_TOOL_MODULES, MCP_TOOLS, type ToolCapability } from "@/lib/docs/tools";
import { DocsH2, DocsP, DocsTable } from "@/components/docs/docs-ui";

const CAPABILITY_COLORS: Record<ToolCapability, string> = {
  read: "bg-sky-400/10 text-sky-400",
  compare: "bg-violet-400/10 text-violet-400",
  transact: "bg-amber-400/10 text-amber-400",
  analytics: "bg-emerald-400/10 text-emerald-400",
};

export function McpToolsReference() {
  const [query, setQuery] = useState("");
  const [capability, setCapability] = useState<ToolCapability | "all">("all");
  const [module, setModule] = useState<string>("all");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return MCP_TOOLS.filter((tool) => {
      if (capability !== "all" && tool.capability !== capability) return false;
      if (module !== "all" && tool.module !== module) return false;
      if (!q) return true;
      return (
        tool.name.toLowerCase().includes(q) ||
        tool.description.toLowerCase().includes(q) ||
        tool.module.toLowerCase().includes(q)
      );
    });
  }, [query, capability, module]);

  return (
    <div className="space-y-6 text-[14px]">
      <DocsP>
        Tools are grouped by backend module. Read tools need no agent. Transact tools require{" "}
        <code className="font-mono text-[12px]">agent_id</code> and a valid access token when invoked
        through agent-scoped flows.
      </DocsP>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search tools..."
          className="min-w-[12rem] flex-1 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-[13px] outline-none focus:border-white/25"
        />
        <select
          value={capability}
          onChange={(e) => setCapability(e.target.value as ToolCapability | "all")}
          className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-[13px] outline-none"
        >
          <option value="all">All capabilities</option>
          <option value="read">read</option>
          <option value="compare">compare</option>
          <option value="transact">transact</option>
          <option value="analytics">analytics</option>
        </select>
        <select
          value={module}
          onChange={(e) => setModule(e.target.value)}
          className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-[13px] outline-none"
        >
          <option value="all">All modules</option>
          {MCP_TOOL_MODULES.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label} ({m.count})
            </option>
          ))}
        </select>
      </div>

      <DocsH2 id="modules">Module summary</DocsH2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {MCP_TOOL_MODULES.map((m) => (
          <div key={m.id} className="rounded-xl border border-white/10 p-4">
            <p className="font-mono text-[12px] opacity-60">{m.id}</p>
            <p className="mt-1 font-semibold">{m.label}</p>
            <p className="mt-1 text-[12px] opacity-50">{m.count} tools</p>
          </div>
        ))}
      </div>

      <DocsH2 id="catalog">Tool catalog ({filtered.length})</DocsH2>
      <DocsTable>
        <thead>
          <tr className="border-b border-white/10 bg-white/[0.02]">
            <th className="px-4 py-3 font-semibold">Name</th>
            <th className="px-4 py-3 font-semibold">Capability</th>
            <th className="px-4 py-3 font-semibold">Description</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((tool) => (
            <tr key={tool.name} className="border-b border-white/5">
              <td className="px-4 py-2.5 font-mono text-[12px]">{tool.name}</td>
              <td className="px-4 py-2.5">
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${CAPABILITY_COLORS[tool.capability]}`}>
                  {tool.capability}
                </span>
              </td>
              <td className="px-4 py-2.5 text-[12px] opacity-75">{tool.description}</td>
            </tr>
          ))}
        </tbody>
      </DocsTable>
    </div>
  );
}
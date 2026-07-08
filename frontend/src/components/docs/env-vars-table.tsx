"use client";

import { useState } from "react";
import type { EnvVarDef, EnvVarScope } from "@/lib/docs/env-vars";
import { DocsTable } from "@/components/docs/docs-ui";

export function EnvVarsTable({ vars, title }: { vars: EnvVarDef[]; title: string }) {
  const [scope, setScope] = useState<EnvVarScope | "all">("all");

  const filtered =
    scope === "all" ? vars : vars.filter((v) => v.scope === scope);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-bold tracking-tight">{title}</h2>
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value as EnvVarScope | "all")}
          className="rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 text-[12px] outline-none"
        >
          <option value="all">All scopes</option>
          <option value="backend">backend</option>
          <option value="frontend">frontend</option>
          <option value="mcp">mcp</option>
        </select>
      </div>
      <DocsTable>
        <thead>
          <tr className="border-b border-white/10 bg-white/[0.02]">
            <th className="px-4 py-3 font-semibold">Variable</th>
            <th className="px-4 py-3 font-semibold">Required</th>
            <th className="px-4 py-3 font-semibold">Default</th>
            <th className="px-4 py-3 font-semibold">Description</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((v) => (
            <tr key={`${v.scope}-${v.name}`} className="border-b border-white/5">
              <td className="px-4 py-2.5 font-mono text-[11px]">{v.name}</td>
              <td className="px-4 py-2.5 text-[12px]">{v.required ? "Yes" : "No"}</td>
              <td className="px-4 py-2.5 font-mono text-[10px] opacity-60">{v.defaultValue ?? "—"}</td>
              <td className="px-4 py-2.5 text-[12px] opacity-75">{v.description}</td>
            </tr>
          ))}
        </tbody>
      </DocsTable>
    </div>
  );
}
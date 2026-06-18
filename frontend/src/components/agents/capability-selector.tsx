"use client";

import { BarChart3, GitCompareArrows, Search, SendHorizontal } from "lucide-react";

import { cn } from "@/lib/utils";

export type CapabilityKey = "read" | "compare" | "transact" | "analytics";

export const CAPABILITIES: Array<{
  key: CapabilityKey;
  name: string;
  description: string;
  icon: typeof Search;
}> = [
  { key: "read", name: "Read Balances", description: "View balances across chains", icon: Search },
  { key: "compare", name: "Compare Chains", description: "Compare gas, speed, costs", icon: GitCompareArrows },
  { key: "transact", name: "Send Transactions", description: "Execute transfers with a cap", icon: SendHorizontal },
  { key: "analytics", name: "Track Analytics", description: "Monitor relay costs and usage", icon: BarChart3 },
];

type CapabilitySelectorProps = {
  value: string[];
  onChange: (value: string[]) => void;
};

export function CapabilitySelector({ value, onChange }: CapabilitySelectorProps) {
  const selected = new Set(value);

  const toggle = (key: CapabilityKey) => {
    const next = new Set(selected);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    onChange(Array.from(next));
  };

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {CAPABILITIES.map((capability) => {
        const Icon = capability.icon;
        const checked = selected.has(capability.key);
        return (
          <button
            key={capability.key}
            type="button"
            onClick={() => toggle(capability.key)}
            aria-pressed={checked}
            className={cn(
              "flex min-h-20 items-start gap-3 rounded-md border px-3 py-3 text-left transition-colors",
              checked
                ? "border-primary bg-primary/10 text-foreground"
                : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <span className={cn("mt-0.5 rounded-md border p-1.5", checked ? "border-primary text-primary" : "border-border")}>
              <Icon size={16} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold">{capability.name}</span>
              <span className="mt-1 block text-xs leading-5 text-muted-foreground">{capability.description}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

"use client";

import { BarChart3, Circle, GitCompareArrows, Search, SendHorizontal } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ChainIcon } from "@/components/chains/chain-icon";
import type { Agent } from "@/lib/api";
import { cn } from "@/lib/utils";

const capabilityIcons = {
  read: Search,
  compare: GitCompareArrows,
  transact: SendHorizontal,
  analytics: BarChart3,
};

type AgentCardProps = {
  agent: Agent;
  selected?: boolean;
  onSelect: () => void;
};

export function AgentCard({ agent, selected = false, onSelect }: AgentCardProps) {
  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      className={cn(
        "cursor-pointer p-4 transition-colors hover:bg-muted/60",
        selected && "border-primary bg-primary/5"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold">{agent.name}</h2>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
            {agent.description || "No description provided."}
          </p>
        </div>
        <span
          className={cn(
            "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-1 text-xs font-medium",
            agent.is_active ? "border-green-200 bg-green-50 text-green-700" : "border-border bg-muted text-muted-foreground"
          )}
        >
          <Circle size={8} fill="currentColor" />
          {agent.is_active ? "Active" : "Inactive"}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {agent.chains.slice(0, 5).map((chain) => (
          <ChainIcon key={chain} chain={chain} />
        ))}
        {agent.chains.length > 5 && <Badge>+{agent.chains.length - 5}</Badge>}
      </div>

      <div className="mt-3 flex items-center gap-2 text-muted-foreground">
        {agent.capabilities.map((capability) => {
          const Icon = capabilityIcons[capability as keyof typeof capabilityIcons];
          return Icon ? (
            <span key={capability} title={capability} aria-label={capability}>
              <Icon size={15} />
            </span>
          ) : null;
        })}
      </div>
    </Card>
  );
}

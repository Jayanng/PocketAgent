"use client";

import Link from "next/link";
import { Copy, ExternalLink, Trash2, Wallet } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ChainIcon } from "@/components/chains/chain-icon";
import type { Agent, AgentBalancesResponse, Conversation } from "@/lib/api";
import { CHAIN_CONFIGS } from "@/lib/constants";
import { useAgentStore } from "@/store/agent-store";

type AgentDetailProps = {
  agent: Agent | null;
  conversations: Conversation[];
  balances: AgentBalancesResponse["balances"];
  isLoadingBalances: boolean;
};

export function AgentDetail({ agent, conversations, balances, isLoadingBalances }: AgentDetailProps) {
  const [fundingAddress, setFundingAddress] = useState<{ agentId: string; address: string } | null>(null);
  const [copiedAddress, setCopiedAddress] = useState<string | null>(null);
  const { deleteAgent, fundAgent, loadBalances } = useAgentStore();

  useEffect(() => {
    if (agent?.id && agent.is_active) {
      void loadBalances(agent.id);
    }
  }, [agent?.id, agent?.is_active, loadBalances]);

  if (!agent) {
    return (
      <Card className="flex min-h-[24rem] items-center justify-center p-6 text-center">
        <div>
          <Wallet className="mx-auto text-muted-foreground" size={28} />
          <h2 className="mt-3 text-base font-semibold">No agent selected</h2>
          <p className="mt-1 text-sm text-muted-foreground">Select an agent to view wallet, limits, chains, and conversations.</p>
        </div>
      </Card>
    );
  }

  const walletAddress = fundingAddress?.agentId === agent.id ? fundingAddress.address : agent.wallet_address ?? "";

  const copyWallet = async () => {
    if (!walletAddress) return;
    await navigator.clipboard.writeText(walletAddress);
    setCopiedAddress(walletAddress);
  };

  const confirmDelete = async () => {
    if (!window.confirm(`Delete ${agent.name}? The agent will be marked inactive.`)) return;
    await deleteAgent(agent.id);
  };

  return (
    <Card className="p-4">
      <div className="flex flex-col gap-3 border-b border-border pb-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold">{agent.name}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{agent.description || "No description provided."}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="pa-button" href={`/chat?agent=${encodeURIComponent(agent.id)}`}>
            <ExternalLink size={15} />
            Chat with Agent
          </Link>
          <Button
            variant="secondary"
            onClick={async () => setFundingAddress({ agentId: agent.id, address: await fundAgent(agent.id) })}
          >
            Fund Agent
          </Button>
          <Button variant="ghost" size="icon" onClick={confirmDelete} title="Delete agent">
            <Trash2 size={16} />
          </Button>
        </div>
      </div>

      <div className="grid gap-3 py-4 md:grid-cols-3">
        <div className="rounded-md border border-border bg-background p-3">
          <p className="text-xs font-medium uppercase text-muted-foreground">Spending Cap</p>
          <p className="mt-2 text-sm font-semibold">{agent.spending_cap ?? 0} ETH</p>
        </div>
        <div className="rounded-md border border-border bg-background p-3">
          <p className="text-xs font-medium uppercase text-muted-foreground">Total Spent</p>
          <p className="mt-2 text-sm font-semibold">{agent.total_spent ?? 0} ETH</p>
        </div>
        <div className="rounded-md border border-border bg-background p-3">
          <p className="text-xs font-medium uppercase text-muted-foreground">Status</p>
          <p className="mt-2 text-sm font-semibold">{agent.is_active ? "Active" : "Inactive"}</p>
        </div>
      </div>

      <div className="rounded-md border border-border bg-background p-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase text-muted-foreground">Wallet Address</p>
            <code className="mt-2 block break-all text-xs">{walletAddress || "No wallet address available"}</code>
          </div>
          <Button variant="secondary" size="sm" onClick={copyWallet} disabled={!walletAddress}>
            <Copy size={14} />
            {copiedAddress === walletAddress ? "Copied" : "Copy"}
          </Button>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <section>
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Chain Balances</h3>
            <Button variant="secondary" size="sm" onClick={() => void loadBalances(agent.id)} disabled={isLoadingBalances}>
              {isLoadingBalances ? "Loading..." : "Load"}
            </Button>
          </div>
          <div className="mt-2 space-y-2">
            {agent.chains.map((chain) => {
              const config = CHAIN_CONFIGS[chain as keyof typeof CHAIN_CONFIGS];
              const balance = balances[chain];
              return (
                <div key={chain} className="flex items-center justify-between rounded-md border border-border bg-background px-3 py-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <ChainIcon chain={chain} />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{config?.name ?? chain}</p>
                      <p className="text-xs text-muted-foreground">{config?.symbol ?? chain}</p>
                    </div>
                  </div>
                  {balance?.error ? (
                    <Badge className="max-w-40 truncate border-red-200 bg-red-50 text-red-700">{balance.error}</Badge>
                  ) : balance ? (
                    <div className="text-right">
                      <p className="text-sm font-semibold">{balance.formatted ?? balance.amount_decimal ?? balance.amount ?? "0"}</p>
                      {balance.usd_value != null && <p className="text-xs text-muted-foreground">${balance.usd_value}</p>}
                    </div>
                  ) : (
                    <Badge>Not loaded</Badge>
                  )}
                </div>
              );
            })}
            {!agent.chains.length && <p className="text-sm text-muted-foreground">No chains enabled.</p>}
          </div>
        </section>

        <section>
          <h3 className="text-sm font-semibold">Recent Conversations</h3>
          <div className="mt-2 space-y-2">
            {conversations.slice(0, 5).map((conversation) => (
              <div key={conversation.id} className="rounded-md border border-border bg-background px-3 py-2">
                <p className="truncate text-sm font-medium">{conversation.title || "Untitled conversation"}</p>
                {conversation.created_at && <p className="mt-1 text-xs text-muted-foreground">{new Date(conversation.created_at).toLocaleString()}</p>}
              </div>
            ))}
            {!conversations.length && <p className="text-sm text-muted-foreground">No conversations yet.</p>}
          </div>
        </section>
      </div>
    </Card>
  );
}

"use client";

import Link from "next/link";
import { Copy, ExternalLink, Trash2, Wallet } from "lucide-react";
import { useEffect, useState } from "react";

import { AgentEditor } from "@/components/agents/agent-editor";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ChainIcon } from "@/components/chains/chain-icon";
import { FundAgentDialog } from "@/components/agents/fund-agent-dialog";
import { canUseProtectedAgentRoutes, isAgentAuthDisabled } from "@/lib/agent-auth";
import { getAgentAccessToken } from "@/lib/api";
import type { Agent, AgentBalancesResponse, Conversation } from "@/lib/api";
import { CHAIN_CONFIGS } from "@/lib/constants";
import { useAgentStore } from "@/store/agent-store";

type AgentDetailProps = {
  agent: Agent | null;
  conversations: Conversation[];
  balances: AgentBalancesResponse["balances"];
  isLoadingBalances: boolean;
};

const PROTOCOL_LABELS: Record<string, string> = {
  evm: "EVM",
  solana: "Solana",
  tron: "Tron",
  sui: "Sui",
};

export function AgentDetail({ agent, conversations, balances, isLoadingBalances }: AgentDetailProps) {
  const [fundingOpen, setFundingOpen] = useState(false);
  const [copiedAddress, setCopiedAddress] = useState<string | null>(null);
  const [tokenDraft, setTokenDraft] = useState("");
  const { deleteAgent, importAgentAccessToken, isLoading, loadBalances } = useAgentStore();

  const hasActiveToken = agent ? Boolean(getAgentAccessToken(agent.id)) : false;
  const canUseProtectedRoutes = canUseProtectedAgentRoutes(agent?.id);
  const hasWalletData = Boolean(
    agent?.wallet_address || Object.keys(agent?.wallet_addresses ?? {}).length > 0
  );
  const hasProtectedDetails = canUseProtectedRoutes && hasWalletData;

  useEffect(() => {
    if (hasProtectedDetails && agent?.id) {
      void loadBalances(agent.id);
    }
  }, [agent?.id, hasProtectedDetails, loadBalances]);

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

  const walletAddresses = agent.wallet_addresses ?? {};
  const evmAddress = walletAddresses.evm ?? agent.wallet_address ?? "";
  const protocolWallets = [
    { key: "evm", label: PROTOCOL_LABELS.evm, address: evmAddress },
    { key: "solana", label: PROTOCOL_LABELS.solana, address: walletAddresses.solana ?? "" },
    { key: "tron", label: PROTOCOL_LABELS.tron, address: walletAddresses.tron ?? "" },
    { key: "sui", label: PROTOCOL_LABELS.sui, address: walletAddresses.sui ?? "" },
  ].filter((entry) => entry.address);

  const spentByChain = agent.total_spent_by_chain ?? {};
  const spentEntries = Object.entries(spentByChain).filter(([, value]) => Number(value) > 0);

  const copyWallet = async (address: string) => {
    if (!address) return;
    await navigator.clipboard.writeText(address);
    setCopiedAddress(address);
  };

  const confirmDelete = async () => {
    if (!window.confirm(`Delete ${agent.name}? This removes it from the active agent list.`)) return;
    await deleteAgent(agent.id);
  };

  const importToken = async () => {
    const imported = await importAgentAccessToken(agent.id, tokenDraft);
    if (imported) {
      setTokenDraft("");
    }
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
          <AgentEditor agent={agent} />
          <Button
            variant="secondary"
            onClick={() => setFundingOpen(true)}
            disabled={!hasProtectedDetails}
            title={hasProtectedDetails ? "Fund agent" : "Import the agent access token to load wallet addresses"}
          >
            Fund Agent
          </Button>
          <Button variant="ghost" size="icon" onClick={confirmDelete} title="Delete agent">
            <Trash2 size={16} />
          </Button>
        </div>
      </div>

      {!canUseProtectedRoutes && !isAgentAuthDisabled() && (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-900">
          <p className="text-sm font-semibold">Access token required</p>
          <p className="mt-1 text-sm">
            {hasActiveToken
              ? "The stored token could not load this agent's protected wallet details. Paste a valid token to continue."
              : "Paste the token shown when this agent was created to view wallet addresses and use protected actions."}
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <Input
              value={tokenDraft}
              onChange={(event) => setTokenDraft(event.target.value)}
              placeholder="Agent access token"
              type="password"
            />
            <Button onClick={() => void importToken()} disabled={isLoading || !tokenDraft.trim()}>
              {isLoading ? "Verifying..." : "Save Token"}
            </Button>
          </div>
        </div>
      )}

      <div className="grid gap-3 py-4 md:grid-cols-2">
        <div className="rounded-md border border-border bg-background p-3">
          <p className="text-xs font-medium uppercase text-muted-foreground">Per-Chain Spending Cap</p>
          <p className="mt-2 text-sm font-semibold">{agent.spending_cap ?? 0} native units</p>
        </div>
        <div className="rounded-md border border-border bg-background p-3">
          <p className="text-xs font-medium uppercase text-muted-foreground">Spent by Chain</p>
          {spentEntries.length ? (
            <div className="mt-2 space-y-1">
              {spentEntries.slice(0, 3).map(([chain, value]) => {
                const config = CHAIN_CONFIGS[chain as keyof typeof CHAIN_CONFIGS];
                return (
                  <p key={chain} className="text-sm font-semibold">
                    {Number(value).toFixed(6)} {config?.symbol ?? chain}
                  </p>
                );
              })}
              {spentEntries.length > 3 && (
                <p className="text-xs text-muted-foreground">+{spentEntries.length - 3} more</p>
              )}
            </div>
          ) : (
            <p className="mt-2 text-sm font-semibold">0 native units</p>
          )}
        </div>
      </div>

      <div className="space-y-3 rounded-md border border-border bg-background p-3">
        <p className="text-xs font-medium uppercase text-muted-foreground">Agent Wallets</p>
        {protocolWallets.length ? (
          protocolWallets.map((wallet) => (
            <div key={wallet.key} className="flex flex-col gap-2 border-t border-border/50 pt-3 first:border-t-0 first:pt-0 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-semibold text-muted-foreground">{wallet.label}</p>
                <code className="mt-1 block break-all text-xs">{wallet.address}</code>
              </div>
              <Button variant="secondary" size="sm" onClick={() => void copyWallet(wallet.address)}>
                <Copy size={14} />
                {copiedAddress === wallet.address ? "Copied" : "Copy"}
              </Button>
            </div>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">
            {hasProtectedDetails ? "No wallet addresses available" : "Import access token to view wallet addresses"}
          </p>
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <section>
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Chain Balances</h3>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void loadBalances(agent.id)}
              disabled={isLoadingBalances || !hasProtectedDetails}
            >
              {isLoadingBalances ? "Loading..." : "Refresh"}
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
              <Link
                key={conversation.id}
                href={`/chat?agent=${encodeURIComponent(agent.id)}`}
                className="block rounded-md border border-border bg-background px-3 py-2 transition-colors hover:bg-muted/30"
              >
                <p className="truncate text-sm font-medium">{conversation.title || "Untitled conversation"}</p>
                {conversation.created_at && (
                  <p className="mt-1 text-xs text-muted-foreground">{new Date(conversation.created_at).toLocaleString()}</p>
                )}
              </Link>
            ))}
            {!conversations.length && <p className="text-sm text-muted-foreground">No conversations yet.</p>}
          </div>
        </section>
      </div>

      {hasProtectedDetails && (
        <FundAgentDialog agent={agent} open={fundingOpen && hasProtectedDetails} onClose={() => setFundingOpen(false)} />
      )}
    </Card>
  );
}
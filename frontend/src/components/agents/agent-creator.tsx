"use client";

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Check, Copy, Plus, Search } from "lucide-react";

import { CapabilitySelector } from "@/components/agents/capability-selector";
import { ChainIcon } from "@/components/chains/chain-icon";
import { TokenDisplayModal } from "@/components/tokens/token-display-modal";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { PROTOCOL_LABEL } from "@/lib/api";

const WRITE_PROTOCOL_ORDER = ["evm", "solana", "tron", "sui"] as const;
import { CHAIN_CONFIGS, type ChainKey } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { useAgentStore } from "@/store/agent-store";

const defaultChains: ChainKey[] = ["ethereum", "polygon", "arbitrum", "base", "optimism", "solana", "sui"];

export function AgentCreator() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [chains, setChains] = useState<string[]>(defaultChains);
  const [capabilities, setCapabilities] = useState<string[]>(["read", "compare"]);
  const [spendingCap, setSpendingCap] = useState("0.1");
  const [chainSearch, setChainSearch] = useState("");
  const [copied, setCopied] = useState(false);
  const {
    createAgent,
    isCreating,
    createdWalletAddress,
    createdWalletAddresses,
    createdAccessToken,
    clearCreatedWalletAddress,
  } = useAgentStore();

  const chainOptions = useMemo(() => Object.values(CHAIN_CONFIGS), []);
  const filteredChainOptions = useMemo(() => {
    const query = chainSearch.trim().toLowerCase();
    if (!query) return chainOptions;
    return chainOptions.filter((chain) => {
      const haystack = [chain.key, chain.name, chain.symbol, chain.protocol].join(" ").toLowerCase();
      return haystack.includes(query);
    });
  }, [chainOptions, chainSearch]);
  const sendEnabled = capabilities.includes("transact");

  const toggleChain = (chain: string) => {
    setChains((current) => current.includes(chain) ? current.filter((item) => item !== chain) : [...current, chain]);
  };

  const reset = () => {
    setName("");
    setDescription("");
    setChains(defaultChains);
    setCapabilities(["read", "compare"]);
    setSpendingCap("0.1");
    setChainSearch("");
    setCopied(false);
    clearCreatedWalletAddress();
  };

  const close = () => {
    setOpen(false);
    reset();
  };

  const handleTokenAcknowledged = () => {
    // User has saved the token via the modal — clear store state and close.
    close();
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await createAgent({
      name: name.trim(),
      description: description.trim(),
      chains,
      capabilities,
      spending_cap: sendEnabled ? Number(spendingCap || 0) : 0,
    });
  };

  const copyWallet = async () => {
    if (!createdWalletAddress) return;
    await navigator.clipboard.writeText(createdWalletAddress);
    setCopied(true);
  };

  const copyAccessToken = async () => {
    if (!createdAccessToken) return;
    await navigator.clipboard.writeText(createdAccessToken);
    setCopied(true);
  };

  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <Plus size={16} />
        Create Agent
      </Button>

      <Dialog open={open} onOpenChange={(nextOpen) => (nextOpen ? setOpen(true) : close())}>
        <DialogContent className="max-w-3xl">
          <DialogHeader
            title="Create Agent"
            description="Configure chain access, capabilities, and transaction limits."
            onClose={close}
          />

            {createdWalletAddress ? (
              <div className="space-y-4 p-4">
                <div className="rounded-md border border-green-200 bg-green-50 p-4 text-green-800">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Check size={16} />
                    Agent created
                  </div>
                  <p className="mt-2 text-sm">Generated wallet addresses:</p>
                  <div className="mt-2 space-y-2">
                    {WRITE_PROTOCOL_ORDER.filter((protocol) => createdWalletAddresses[protocol] || (protocol === "evm" && createdWalletAddress)).map((protocol) => {
                      const address = createdWalletAddresses[protocol] ?? (protocol === "evm" ? createdWalletAddress : "");
                      if (!address) return null;
                      return (
                        <div key={protocol} className="rounded-md border border-green-200 bg-white p-3">
                          <p className="text-xs font-medium uppercase text-muted-foreground">
                            {PROTOCOL_LABEL[protocol as keyof typeof PROTOCOL_LABEL]}
                          </p>
                          <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center">
                            <code className="min-w-0 flex-1 break-all text-xs text-foreground">{address}</code>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={async () => {
                                await navigator.clipboard.writeText(address);
                                setCopied(true);
                              }}
                            >
                              <Copy size={14} />
                              Copy
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {createdAccessToken && (
                    <>
                      <p className="mt-3 text-sm">
                        Agent access token. Save this token somewhere secure; PocketAgent keeps it for this browser tab session.
                      </p>
                      <div className="mt-2 flex flex-col gap-2 rounded-md border border-green-200 bg-white p-3 sm:flex-row sm:items-center">
                        <code className="min-w-0 flex-1 break-all text-xs text-foreground">{createdAccessToken}</code>
                        <Button variant="secondary" size="sm" onClick={copyAccessToken}>
                          <Copy size={14} />
                          Copy
                        </Button>
                      </div>
                    </>
                  )}
                </div>
                <div className="flex justify-end">
                  <Button onClick={close}>Done</Button>
                </div>
              </div>
            ) : (
              <form onSubmit={submit} className="space-y-5 p-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-sm font-medium">Agent Name</span>
                    <Input value={name} onChange={(event) => setName(event.target.value)} required placeholder="Research Agent" />
                  </label>
                  {sendEnabled && (
                    <label className="space-y-2">
                      <span className="text-sm font-medium">Per-Chain Spending Cap</span>
                      <Input
                        type="number"
                        min="0"
                        step="0.001"
                        value={spendingCap}
                        onChange={(event) => setSpendingCap(event.target.value)}
                      />
                    </label>
                  )}
                </div>

                <label className="block space-y-2">
                  <span className="text-sm font-medium">Description</span>
                  <textarea
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    rows={3}
                    className="w-full resize-none rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                    placeholder="What should this agent be used for?"
                  />
                </label>

                <div className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-medium">Chains</span>
                    <span className="text-xs text-muted-foreground">
                      {chains.length} selected
                      {chainSearch.trim() ? ` · ${filteredChainOptions.length} shown` : ""}
                    </span>
                  </div>
                  <div className="relative">
                    <Search
                      size={16}
                      className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                    />
                    <Input
                      value={chainSearch}
                      onChange={(event) => setChainSearch(event.target.value)}
                      placeholder="Search chains by name, symbol, or protocol…"
                      className="pl-9"
                    />
                  </div>
                  <div className="grid max-h-64 gap-2 overflow-y-auto rounded-md border border-border bg-background p-2 sm:grid-cols-2 lg:grid-cols-3">
                    {filteredChainOptions.length === 0 ? (
                      <p className="col-span-full px-2 py-6 text-center text-sm text-muted-foreground">
                        No chains match &ldquo;{chainSearch.trim()}&rdquo;
                      </p>
                    ) : (
                      filteredChainOptions.map((chain) => {
                        const checked = chains.includes(chain.key);
                        return (
                          <label
                            key={chain.key}
                            className={cn(
                              "flex items-center gap-2 rounded-md border px-2 py-2 text-sm",
                              checked ? "border-primary bg-primary/10" : "border-border"
                            )}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleChain(chain.key)}
                              className="h-4 w-4 accent-primary"
                            />
                            <ChainIcon chain={chain.key} className="h-6 w-8" />
                            <span className="min-w-0 truncate">{chain.name}</span>
                          </label>
                        );
                      })
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="text-sm font-medium">Capabilities</span>
                  <CapabilitySelector value={capabilities} onChange={setCapabilities} />
                </div>

                <div className="flex justify-end gap-2 border-t border-border pt-4">
                  <Button variant="secondary" onClick={close}>Cancel</Button>
                  <Button type="submit" disabled={isCreating || !name.trim() || !chains.length || !capabilities.length}>
                    {isCreating ? "Creating..." : "Create Agent"}
                  </Button>
                </div>
              </form>
            )}
        </DialogContent>
      </Dialog>

      {createdAccessToken && (
        <TokenDisplayModal
          open={!!createdAccessToken}
          agentName={name || "Agent"}
          token={createdAccessToken}
          onAcknowledged={handleTokenAcknowledged}
        />
      )}
    </>
  );
}

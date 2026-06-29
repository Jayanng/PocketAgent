"use client";

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Pencil } from "lucide-react";

import { CapabilitySelector } from "@/components/agents/capability-selector";
import { ChainIcon } from "@/components/chains/chain-icon";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { CHAIN_CONFIGS, type ChainKey } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { Agent } from "@/lib/api";
import { useAgentStore } from "@/store/agent-store";

type AgentEditorProps = {
  agent: Agent;
};

export function AgentEditor({ agent }: AgentEditorProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(agent.name);
  const [description, setDescription] = useState(agent.description ?? "");
  const [chains, setChains] = useState<string[]>(agent.chains);
  const [capabilities, setCapabilities] = useState<string[]>(agent.capabilities);
  const [spendingCap, setSpendingCap] = useState(String(agent.spending_cap ?? 0.1));
  const { updateAgent, isUpdating } = useAgentStore();

  const chainOptions = useMemo(() => Object.values(CHAIN_CONFIGS), []);
  const sendEnabled = capabilities.includes("transact");

  const openEditor = () => {
    setName(agent.name);
    setDescription(agent.description ?? "");
    setChains(agent.chains);
    setCapabilities(agent.capabilities);
    setSpendingCap(String(agent.spending_cap ?? 0.1));
    setOpen(true);
  };

  const toggleChain = (chain: string) => {
    setChains((current) =>
      current.includes(chain) ? current.filter((item) => item !== chain) : [...current, chain]
    );
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await updateAgent(agent.id, {
      name: name.trim(),
      description: description.trim(),
      chains,
      capabilities,
      spending_cap: sendEnabled ? Number(spendingCap || 0) : 0,
    });
    setOpen(false);
  };

  return (
    <>
      <Button variant="secondary" onClick={openEditor}>
        <Pencil size={15} />
        Edit
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader
            title="Edit Agent"
            description="Update chain access, capabilities, and transaction limits."
            onClose={() => setOpen(false)}
          />
          <form onSubmit={submit} className="space-y-5 p-4">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium">Agent Name</span>
                <Input value={name} onChange={(e) => setName(e.target.value)} required />
              </label>
              {sendEnabled && (
                <label className="space-y-2">
                  <span className="text-sm font-medium">Per-Chain Spending Cap</span>
                  <Input
                    type="number"
                    min="0"
                    step="0.001"
                    value={spendingCap}
                    onChange={(e) => setSpendingCap(e.target.value)}
                  />
                </label>
              )}
            </div>

            <label className="block space-y-2">
              <span className="text-sm font-medium">Description</span>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full resize-none rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
              />
            </label>

            <div className="space-y-2">
              <span className="text-sm font-medium">Chains</span>
              <div className="grid max-h-64 gap-2 overflow-y-auto rounded-md border border-border bg-background p-2 sm:grid-cols-2 lg:grid-cols-3">
                {chainOptions.map((chain) => {
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
                      <ChainIcon chain={chain.key as ChainKey} className="h-6 w-8" />
                      <span className="truncate">{chain.name}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-sm font-medium">Capabilities</span>
              <CapabilitySelector value={capabilities} onChange={setCapabilities} />
            </div>

            <div className="flex justify-end gap-2 border-t border-border pt-4">
              <Button variant="secondary" type="button" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isUpdating || !name.trim() || !chains.length || !capabilities.length}>
                {isUpdating ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
"use client";

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  INTERVAL_PRESETS,
  TASK_TEMPLATES,
} from "@/components/scheduled-tasks/constants";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
import { api, getAgentAccessToken, type Agent } from "@/lib/api";
import { cn } from "@/lib/utils";

type CreateDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agents: Agent[];
};

export function CreateScheduledTaskDialog({
  open,
  onOpenChange,
  agents,
}: CreateDialogProps) {
  const queryClient = useQueryClient();
  const agentsWithToken = useMemo(
    () => agents.filter((a) => Boolean(getAgentAccessToken(a.id))),
    [agents],
  );

  const [agentId, setAgentId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [intervalSeconds, setIntervalSeconds] = useState(3600);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setAgentId("");
    setPrompt("");
    setIntervalSeconds(3600);
    setError(null);
  };

  const close = () => {
    onOpenChange(false);
    reset();
  };

  const applyTemplate = (templateId: string) => {
    const t = TASK_TEMPLATES.find((x) => x.id === templateId);
    if (!t) return;
    setPrompt(t.prompt);
    setIntervalSeconds(t.interval_seconds);
  };

  const createMutation = useMutation({
    mutationFn: (payload: {
      agent_id: string;
      prompt: string;
      interval_seconds: number;
    }) => api.scheduledTasks.create(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["scheduled-tasks"] });
      close();
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to create scheduled task");
    },
  });

  // Default agent when dialog opens with a usable list
  const effectiveAgentId = agentId || (agentsWithToken[0]?.id ?? "");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const selectedAgentId = effectiveAgentId;
    if (!selectedAgentId) {
      setError("Select an agent.");
      return;
    }
    if (!prompt.trim()) {
      setError("Prompt is required.");
      return;
    }
    if (!INTERVAL_PRESETS.some((p) => p.seconds === intervalSeconds)) {
      setError("Select an interval.");
      return;
    }
    if (!getAgentAccessToken(selectedAgentId)) {
      setError("This agent has no access token in this browser. Import it on the Agents page first.");
      return;
    }
    createMutation.mutate({
      agent_id: selectedAgentId,
      prompt: prompt.trim(),
      interval_seconds: intervalSeconds,
    });
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent className="max-w-lg bg-card">
        <DialogHeader
          title="New Scheduled Task"
          description="Your agent will run this prompt on a recurring interval via Pocket Network."
          onClose={close}
        />
        <form onSubmit={submit} className="space-y-4 p-4">
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Templates</p>
            <div className="flex flex-wrap gap-2">
              {TASK_TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => applyTemplate(t.id)}
                  className="rounded-full border border-border bg-muted/30 px-3 py-1 text-xs font-medium text-foreground hover:bg-muted/60"
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Agent</span>
            <select
              className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm"
              value={agentId || effectiveAgentId}
              onChange={(e) => setAgentId(e.target.value)}
              required
            >
              <option value="" disabled>
                {agentsWithToken.length ? "Select agent…" : "No agents with tokens"}
              </option>
              {agentsWithToken.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            {!agentsWithToken.length && (
              <p className="text-xs text-muted-foreground">
                Create an agent and keep its access token (Agents page) before scheduling.
              </p>
            )}
          </label>

          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Prompt</span>
            <textarea
              className="min-h-24 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              maxLength={2000}
              placeholder="What should the agent do each run?"
              required
            />
          </label>

          <fieldset className="space-y-1.5">
            <legend className="text-sm font-medium">Interval</legend>
            <div className="flex flex-wrap gap-2">
              {INTERVAL_PRESETS.map((p) => (
                <button
                  key={p.seconds}
                  type="button"
                  onClick={() => setIntervalSeconds(p.seconds)}
                  className={cn(
                    "rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors",
                    intervalSeconds === p.seconds
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:bg-muted/40",
                  )}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </fieldset>

          {error && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" onClick={close}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending || !agentsWithToken.length}>
              {createMutation.isPending ? "Creating…" : "Create task"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

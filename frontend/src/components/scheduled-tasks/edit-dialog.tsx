"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { INTERVAL_PRESETS } from "@/components/scheduled-tasks/constants";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
import { api, type ScheduledTask } from "@/lib/api";
import { cn } from "@/lib/utils";

type EditDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: ScheduledTask | null;
  agentName?: string;
};

function EditForm({
  task,
  agentName,
  onClose,
}: {
  task: ScheduledTask;
  agentName?: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState(task.prompt);
  const [intervalSeconds, setIntervalSeconds] = useState(task.interval_seconds);
  const [enabled, setEnabled] = useState(task.enabled === 1);
  const [error, setError] = useState<string | null>(null);


  const updateMutation = useMutation({
    mutationFn: () =>
      api.scheduledTasks.update(task.id, task.agent_id, {
        prompt: prompt.trim(),
        interval_seconds: intervalSeconds,
        enabled,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["scheduled-tasks"] });
      onClose();
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to update task");
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!prompt.trim()) {
      setError("Prompt is required.");
      return;
    }
    updateMutation.mutate();
  };

  return (
    <DialogContent className="max-w-lg bg-card">
      <DialogHeader
        title="Edit Scheduled Task"
        description={agentName ? `Agent: ${agentName}` : undefined}
        onClose={onClose}
      />
      <form onSubmit={submit} className="space-y-4 p-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Prompt</span>
          <textarea
            className="min-h-24 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            maxLength={2000}
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

        <label className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2">
          <span className="text-sm font-medium">Enabled</span>
          <button
            type="button"
            role="switch"
            aria-checked={enabled}
            onClick={() => setEnabled((v) => !v)}
            className={cn(
              "relative h-6 w-11 rounded-full transition-colors",
              enabled ? "bg-primary" : "bg-muted",
            )}
          >
            <span
              className={cn(
                "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
                enabled && "translate-x-5",
              )}
            />
          </button>
        </label>

        {error && (
          <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={updateMutation.isPending}>
            {updateMutation.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </DialogContent>
  );
}

export function EditScheduledTaskDialog({
  open,
  onOpenChange,
  task,
  agentName,
}: EditDialogProps) {
  const close = () => onOpenChange(false);

  if (!task) return null;

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      {/* Remount form when task changes so local state initializes without effects */}
      <EditForm key={task.id} task={task} agentName={agentName} onClose={close} />
    </Dialog>
  );
}

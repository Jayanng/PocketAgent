"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
import { api, type ScheduledTask } from "@/lib/api";
import { truncateText } from "@/lib/format";

type DeleteConfirmProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: ScheduledTask | null;
};

export function DeleteScheduledTaskConfirm({
  open,
  onOpenChange,
  task,
}: DeleteConfirmProps) {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!task) throw new Error("No task selected");
      return api.scheduledTasks.delete(task.id, task.agent_id);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["scheduled-tasks"] });
      onOpenChange(false);
    },
  });

  if (!task) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-card">
        <DialogHeader
          title="Delete automation?"
          description="This cannot be undone."
          onClose={() => onOpenChange(false)}
        />
        <div className="space-y-4 p-4">
          <p className="text-sm text-muted-foreground">
            Delete this automation? This cannot be undone.
          </p>
          <p className="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm" title={task.prompt}>
            {truncateText(task.prompt, 120)}
          </p>
          {deleteMutation.isError && (
            <p className="text-sm text-red-600">
              {(deleteMutation.error as Error)?.message || "Delete failed"}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => onOpenChange(false)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="border-red-600 bg-red-600 text-white hover:bg-red-600/90"
            >
              {deleteMutation.isPending ? "Deleting…" : "Delete"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

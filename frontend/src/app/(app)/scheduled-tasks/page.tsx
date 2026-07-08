"use client";

import { Fragment, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CalendarClock,
  ChevronDown,
  ChevronRight,
  Info,
  Pencil,
  Plus,
  Terminal,
  Trash2,
} from "lucide-react";

import { CreateScheduledTaskDialog } from "@/components/scheduled-tasks/create-dialog";
import { DeleteScheduledTaskConfirm } from "@/components/scheduled-tasks/delete-confirm";
import { EditScheduledTaskDialog } from "@/components/scheduled-tasks/edit-dialog";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import {
  API_BASE_URL,
  api,
  getAgentAccessToken,
  type Agent,
  type ScheduledTask,
  type ScheduledTaskRelayStats,
} from "@/lib/api";
import { buildCreateScheduledTaskCurl } from "@/lib/curl-builder";
import {
  formatIntervalPhrase,
  formatUnixTime,
  truncateText,
} from "@/lib/format";
import { cn } from "@/lib/utils";

const RELAY_TOOLTIP =
  "Every scheduled tick generates Pocket Network relays. This is the real POKT demand your agent is driving.";

async function fetchAllScheduledTasks(agents: Agent[]): Promise<ScheduledTask[]> {
  const withToken = agents.filter((a) => Boolean(getAgentAccessToken(a.id)));
  const results = await Promise.all(
    withToken.map(async (agent) => {
      try {
        return await api.scheduledTasks.list(agent.id);
      } catch {
        return [] as ScheduledTask[];
      }
    }),
  );
  return results.flat().sort((a, b) => b.created_at - a.created_at);
}

function RelayTotal({
  stats,
  isLoading,
}: {
  stats: ScheduledTaskRelayStats | undefined;
  isLoading: boolean;
}) {
  if (isLoading) return <span className="text-muted-foreground">…</span>;
  if (!stats) return <span className="text-muted-foreground">—</span>;
  return <span className="font-medium tabular-nums">{stats.total_relays_last_10_runs}</span>;
}

function RelayBreakdown({ stats }: { stats: ScheduledTaskRelayStats | undefined }) {
  if (!stats?.runs?.length) {
    return (
      <p className="text-xs text-muted-foreground">
        No run history yet. Counts appear after the next scheduled tick.
      </p>
    );
  }
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Last {stats.runs.length} run(s) · avg {stats.avg_relays_per_run} relays/run
        (approximate; agent-scoped window against relay_logs)
      </p>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-muted-foreground">
            <th className="py-1 pr-3 text-left font-medium">Started</th>
            <th className="py-1 pr-3 text-left font-medium">Finished</th>
            <th className="py-1 pr-3 text-left font-medium">Relays</th>
            <th className="py-1 text-left font-medium">OK</th>
          </tr>
        </thead>
        <tbody>
          {stats.runs.map((run) => (
            <tr key={`${run.started_at}-${run.finished_at ?? "x"}`} className="border-t border-border/40">
              <td className="py-1.5 pr-3">{formatUnixTime(run.started_at)}</td>
              <td className="py-1.5 pr-3">{formatUnixTime(run.finished_at)}</td>
              <td className="py-1.5 pr-3 tabular-nums">{run.relay_count}</td>
              <td className="py-1.5">
                {run.success == null ? "—" : run.success ? "yes" : "no"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ScheduledTasksPage() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTask, setEditTask] = useState<ScheduledTask | null>(null);
  const [deleteTask, setDeleteTask] = useState<ScheduledTask | null>(null);
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());
  const [expandedRelays, setExpandedRelays] = useState<Set<string>>(new Set());

  const agentsQuery = useQuery({
    queryKey: ["agents", "list"],
    queryFn: () => api.agents.list(),
    staleTime: 30_000,
  });

  const agents = useMemo(() => agentsQuery.data ?? [], [agentsQuery.data]);
  const agentNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of agents) map.set(a.id, a.name);
    return map;
  }, [agents]);
  const agentIdsKey = useMemo(() => agents.map((a) => a.id).join(","), [agents]);

  const tasksQuery = useQuery({
    queryKey: ["scheduled-tasks", agentIdsKey],
    queryFn: () => fetchAllScheduledTasks(agents),
    enabled: agentsQuery.isSuccess,
    refetchInterval: 15_000,
  });

  const tasks = useMemo(() => tasksQuery.data ?? [], [tasksQuery.data]);

  // Prefetch relay stats for visible tasks (list + 15s refresh)
  const taskIdsKey = useMemo(() => tasks.map((t) => t.id).join(","), [tasks]);
  const allRelayStatsQuery = useQuery({
    queryKey: ["scheduled-tasks", "relay-stats-all", taskIdsKey],
    queryFn: async () => {
      const entries = await Promise.all(
        tasks.map(async (task) => {
          try {
            const stats = await api.scheduledTasks.relayStats(task.id, task.agent_id);
            return [task.id, stats] as const;
          } catch {
            return [task.id, null] as const;
          }
        }),
      );
      return Object.fromEntries(entries) as Record<string, ScheduledTaskRelayStats | null>;
    },
    enabled: tasks.length > 0,
    refetchInterval: 15_000,
  });
  const relayByTask = allRelayStatsQuery.data ?? {};

  const toggleMutation = useMutation({
    mutationFn: ({ task, enabled }: { task: ScheduledTask; enabled: boolean }) =>
      api.scheduledTasks.update(task.id, task.agent_id, { enabled }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["scheduled-tasks"] });
    },
  });

  const toggleExpandResult = (id: string) => {
    setExpandedResults((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const copyCurl = async (task: ScheduledTask) => {
    const curl = buildCreateScheduledTaskCurl(task, API_BASE_URL);
    try {
      await navigator.clipboard.writeText(curl);
      addToast({
        type: "success",
        message: "cURL copied — replace $POCKETAGENT_TOKEN with your agent access token",
      });
    } catch {
      addToast({ type: "error", message: "Could not copy to clipboard" });
    }
  };

  const toggleExpandRelay = (id: string) => {
    setExpandedRelays((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };


  const isLoading = agentsQuery.isLoading || tasksQuery.isLoading;
  const error = agentsQuery.error || tasksQuery.error;

  return (
    <section className="space-y-4 sm:space-y-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between md:items-center">
        <div className="space-y-2">
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
            Scheduled Tasks
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Recurring autonomous actions your agents run on their own via Pocket
            Network relays
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="w-full sm:w-auto">
          <Plus size={16} />
          New Scheduled Task
        </Button>
      </header>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <AlertCircle className="mt-0.5 shrink-0" size={16} />
          <span>{(error as Error).message || "Failed to load scheduled tasks"}</span>
        </div>
      )}

      {isLoading && (
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          Loading scheduled tasks…
        </div>
      )}

      {!isLoading && !tasks.length && (
        <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center sm:p-12">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <CalendarClock size={24} />
          </div>
          <p className="text-base font-semibold">No scheduled tasks yet</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            Scheduled tasks let an agent run a prompt on a timer — portfolio
            checks, gas snapshots, balance monitors — without you opening chat.
            Each run uses Pocket Network relays under your agent&apos;s
            capabilities and spending caps.
          </p>
          <Button className="mt-6" onClick={() => setCreateOpen(true)}>
            <Plus size={16} />
            Create your first scheduled task
          </Button>
        </div>
      )}

      {!isLoading && tasks.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border/60 bg-card shadow-sm">
          <table className="w-full min-w-[880px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
                <th className="w-8 px-2 py-3" />
                <th className="px-3 py-3 font-semibold">Agent</th>
                <th className="px-3 py-3 font-semibold">Prompt</th>
                <th className="px-3 py-3 font-semibold">Interval</th>
                <th className="px-3 py-3 font-semibold">Enabled</th>
                <th className="px-3 py-3 font-semibold">Last Run</th>
                <th className="px-3 py-3 font-semibold">Last Result</th>
                <th className="px-3 py-3 font-semibold">
                  <span
                    className="inline-flex items-center gap-1"
                    title={RELAY_TOOLTIP}
                  >
                    Relays (last 10)
                    <Info
                      size={12}
                      className="text-muted-foreground"
                      aria-hidden
                    />
                  </span>
                </th>
                <th className="px-3 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => {
                const enabled = task.enabled === 1;
                const resultExpanded = expandedResults.has(task.id);
                const relayExpanded = expandedRelays.has(task.id);
                const resultText = task.last_error
                  ? `Error: ${task.last_error}`
                  : task.last_result || "—";
                const stats = relayByTask[task.id] ?? undefined;
                return (
                  <Fragment key={task.id}>
                    <tr className="border-b border-border/60 hover:bg-muted/20">
                      <td className="px-2 py-3">
                        <button
                          type="button"
                          className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                          aria-expanded={relayExpanded}
                          title="Expand relay breakdown"
                          onClick={() => toggleExpandRelay(task.id)}
                        >
                          {relayExpanded ? (
                            <ChevronDown size={16} />
                          ) : (
                            <ChevronRight size={16} />
                          )}
                        </button>
                      </td>
                      <td className="px-3 py-3 font-medium">
                        {agentNameById.get(task.agent_id) ?? task.agent_id.slice(0, 8)}
                      </td>
                      <td className="max-w-[200px] px-3 py-3" title={task.prompt}>
                        <span className="text-muted-foreground">
                          {truncateText(task.prompt, 60)}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-3 py-3">
                        {formatIntervalPhrase(task.interval_seconds)}
                      </td>
                      <td className="px-3 py-3">
                        <button
                          type="button"
                          role="switch"
                          aria-checked={enabled}
                          aria-label={enabled ? "Disable task" : "Enable task"}
                          disabled={toggleMutation.isPending}
                          onClick={() =>
                            toggleMutation.mutate({ task, enabled: !enabled })
                          }
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
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                        {formatUnixTime(task.last_run_at)}
                      </td>
                      <td className="max-w-[180px] px-3 py-3">
                        {resultText === "—" ? (
                          <span className="text-muted-foreground">—</span>
                        ) : (
                          <button
                            type="button"
                            className="text-left text-muted-foreground hover:text-foreground"
                            title={resultText}
                            onClick={() => toggleExpandResult(task.id)}
                          >
                            {resultExpanded
                              ? resultText
                              : truncateText(resultText, 48)}
                            {resultText.length > 48 && (
                              <span className="ml-1 text-xs text-primary">
                                {resultExpanded ? "less" : "more"}
                              </span>
                            )}
                          </button>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <RelayTotal
                          stats={stats ?? undefined}
                          isLoading={allRelayStatsQuery.isLoading}
                        />
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Copy as cURL"
                            onClick={() => void copyCurl(task)}
                          >
                            <Terminal size={15} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Edit"
                            onClick={() => setEditTask(task)}
                          >
                            <Pencil size={15} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Delete"
                            onClick={() => setDeleteTask(task)}
                          >
                            <Trash2 size={15} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                    {relayExpanded && (
                      <tr className="border-b border-border/60 bg-muted/15">
                        <td colSpan={9} className="px-4 py-3">
                          <RelayBreakdown stats={stats ?? undefined} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <CreateScheduledTaskDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        agents={agents}
      />
      <EditScheduledTaskDialog
        open={Boolean(editTask)}
        onOpenChange={(open) => !open && setEditTask(null)}
        task={editTask}
        agentName={editTask ? agentNameById.get(editTask.agent_id) : undefined}
      />
      <DeleteScheduledTaskConfirm
        open={Boolean(deleteTask)}
        onOpenChange={(open) => !open && setDeleteTask(null)}
        task={deleteTask}
      />
    </section>
  );
}

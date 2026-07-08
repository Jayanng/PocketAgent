import type { ScheduledTask } from "@/lib/api";

/**
 * Build a multi-line cURL for recreating a scheduled task via the REST API.
 * Never embeds a real access token — only the placeholder.
 *
 * Uses X-Agent-Access-Token (PocketAgent auth), not Authorization Bearer.
 */
export function buildCreateScheduledTaskCurl(
  task: Pick<ScheduledTask, "agent_id" | "prompt" | "interval_seconds">,
  apiBaseUrl: string,
  tokenPlaceholder = "$POCKETAGENT_TOKEN",
): string {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const url = `${base}/api/scheduled-tasks`;
  const body = JSON.stringify(
    {
      agent_id: task.agent_id,
      prompt: task.prompt,
      interval_seconds: task.interval_seconds,
    },
    null,
    2,
  );
  // Escape single quotes for shell: 'foo'bar' → 'foo'\''bar'
  const bodyForShell = body.replace(/'/g, `'\\''`);

  return [
    `curl -X POST '${url}' \\`,
    `  -H 'X-Agent-Access-Token: ${tokenPlaceholder}' \\`,
    `  -H 'Content-Type: application/json' \\`,
    `  -d '${bodyForShell}'`,
  ].join("\n");
}

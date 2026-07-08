import { DocsPage } from "@/components/docs/docs-page";
import {
  ApiEndpoint,
  Callout,
  CodeBlock,
  DocsH2,
  DocsProse,
  DocsP,
  DocsUl,
} from "@/components/docs/docs-ui";

export default function ApiAutomationsPage() {
  return (
    <DocsPage
      title="Automations API"
      description="Create and manage scheduled agent prompts; inspect per-run Pocket relay usage."
    >
      <DocsProse>
        <DocsP>
          Base path: <code className="font-mono text-[12px]">/api/scheduled-tasks</code>. All
          routes require a valid{" "}
          <code className="font-mono text-[12px]">X-Agent-Access-Token</code> for the task&apos;s
          agent. List requires a query{" "}
          <code className="font-mono text-[12px]">agent_id</code>.
        </DocsP>

        <Callout type="info" title="OpenAPI tag">
          In Swagger UI these appear under the <code className="font-mono text-[12px]">scheduled-tasks</code>{" "}
          tag. The product UI labels them <strong>Automations</strong>.
        </Callout>

        <ApiEndpoint
          method="POST"
          path="/api/scheduled-tasks"
          auth="token"
          description="Create an automation. Returns the full row including id and next_run_at."
        >
          <CodeBlock>{`{
  "agent_id": "uuid",
  "prompt": "string (1–2000 chars)",
  "interval_seconds": 3600
}`}</CodeBlock>
          <DocsP>
            Constraints: <code className="font-mono text-[12px]">interval_seconds</code> ∈ [60,
            604800]. New jobs start with <code className="font-mono text-[12px]">enabled=1</code> and{" "}
            <code className="font-mono text-[12px]">next_run_at = now + interval</code>.
          </DocsP>
        </ApiEndpoint>

        <ApiEndpoint
          method="GET"
          path="/api/scheduled-tasks?agent_id={id}"
          auth="token"
          description="List automations for one agent, newest first. agent_id is required."
        />

        <ApiEndpoint
          method="GET"
          path="/api/scheduled-tasks/{id}"
          auth="token"
          description="Fetch one automation. 404 if missing or token does not own the agent."
        />

        <ApiEndpoint
          method="PATCH"
          path="/api/scheduled-tasks/{id}"
          auth="token"
          description="Partial update: enabled, prompt, and/or interval_seconds."
        >
          <CodeBlock>{`{
  "enabled": false,
  "prompt": "optional new prompt",
  "interval_seconds": 900
}`}</CodeBlock>
          <DocsP>
            Changing <code className="font-mono text-[12px]">interval_seconds</code> resets{" "}
            <code className="font-mono text-[12px]">next_run_at</code> to now + new interval.
          </DocsP>
        </ApiEndpoint>

        <ApiEndpoint
          method="DELETE"
          path="/api/scheduled-tasks/{id}"
          auth="token"
          description="Delete automation (204). Cascades scheduled_task_runs rows when FK is enforced."
        />

        <ApiEndpoint
          method="GET"
          path="/api/scheduled-tasks/{id}/relay-stats"
          auth="token"
          description="Last up to 10 runs with per-run relay_count, success flag, and aggregates."
        >
          <CodeBlock>{`{
  "total_relays_last_10_runs": 2,
  "avg_relays_per_run": 1.0,
  "runs": [
    {
      "started_at": 1710000000,
      "finished_at": 1710000012,
      "relay_count": 1,
      "success": true
    }
  ]
}`}</CodeBlock>
        </ApiEndpoint>

        <DocsH2 id="scheduler">Scheduler behavior</DocsH2>
        <DocsUl>
          <li>Background loop in <code className="font-mono text-[12px]">services/scheduler.py</code></li>
          <li>~30s poll; runs due rows with <code className="font-mono text-[12px]">enabled=1</code></li>
          <li>
            Each run calls <code className="font-mono text-[12px]">AIAgentService.chat(message=prompt, …)</code>
          </li>
          <li>
            Updates <code className="font-mono text-[12px]">last_result</code> /{" "}
            <code className="font-mono text-[12px]">last_error</code>,{" "}
            <code className="font-mono text-[12px]">last_run_at</code>,{" "}
            <code className="font-mono text-[12px]">next_run_at</code>,{" "}
            <code className="font-mono text-[12px]">run_count</code>
          </li>
        </DocsUl>
      </DocsProse>
    </DocsPage>
  );
}

import { DocsPage } from "@/components/docs/docs-page";
import { CodeBlock, DocsH2, DocsLink, DocsProse, DocsP } from "@/components/docs/docs-ui";

export default function ArchitecturePage() {
  return (
    <DocsPage
      title="Architecture"
      description="System layers from MCP clients and the web UI down to Pocket Network RPC."
    >
      <DocsProse>
        <CodeBlock>{`┌──────────────────────┐     ┌──────────────────────────────┐
│  MCP Clients         │     │  Next.js Frontend            │
│  Claude · Cursor     │     │  Chat · Agents · Automations │
└──────────┬───────────┘     └──────────────┬───────────────┘
           │ stdio                          │ REST / SSE
           ▼                                ▼
┌──────────────────────────────────────────────────────────┐
│                    FastAPI Backend                        │
│  /api/agents  /api/chat  /api/analytics                  │
│  /api/scheduled-tasks  /health                           │
│  ai_agent.py · pocket_rpc.py · scheduler.py (jobs loop)  │
└──────────────────────────┬───────────────────────────────┘
                           │ execute_tool() / chat()
                           ▼
┌──────────────────────────────────────────────────────────┐
│  backend/tools/TOOL_REGISTRY  (51 tools)                 │
│  balance · chain · compare · transact · analytics        │
└──────────────────────────┬───────────────────────────────┘
                           │ protocol dispatcher
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Pocket Network Shannon Gateway                          │
│  https://{chain}.api.pocket.network                      │
│  52 chains · EVM · Cosmos · Solana · SUI · NEAR · TRON   │
└──────────────────────────────────────────────────────────┘`}</CodeBlock>

        <DocsH2 id="mcp-adapter">MCP adapter design</DocsH2>
        <DocsP>
          The MCP server is a thin stdio adapter over <code className="font-mono text-[12px]">TOOL_REGISTRY</code>.
          It does not re-route tools — <code className="font-mono text-[12px]">call_tool</code> delegates to the
          same <code className="font-mono text-[12px]">execute_tool</code> path the chat UI uses. This eliminates
          routing drift between surfaces.
        </DocsP>

        <DocsH2 id="rpc">RPC layer</DocsH2>
        <DocsP>
          <code className="font-mono text-[12px]">PocketRPCClient</code> dispatches by protocol family with
          response caching, exponential backoff, and relay logging. All chains use Pocket Network endpoints —
          no centralized provider API keys.
        </DocsP>

        <DocsH2 id="automations">Automations scheduler</DocsH2>
        <DocsP>
          <code className="font-mono text-[12px]">services/scheduler.py</code> runs a background loop
          (~30s poll) that executes due rows from{" "}
          <code className="font-mono text-[12px]">scheduled_tasks</code> via{" "}
          <code className="font-mono text-[12px]">AIAgentService.chat</code>. Run history and approximate
          Pocket relay counts live in <code className="font-mono text-[12px]">scheduled_task_runs</code>.
          See the <DocsLink href="/docs/guides/automations">Automations guide</DocsLink>.
        </DocsP>

        <DocsH2 id="persistence">Persistence</DocsH2>
        <DocsP>
          SQLite stores agents, encrypted wallet material, conversations, messages, relay logs, scheduled
          tasks, and task runs. Agent private keys are AES-256 encrypted at rest; only hashes of access
          tokens are stored.
        </DocsP>

        <DocsH2 id="streaming">Real-time streaming</DocsH2>
        <DocsP>
          Chat uses Server-Sent Events for token deltas, tool calls, and results. Transaction confirmations
          fan out through an in-process pub/sub broker to the chat UI and conversation stream endpoints.
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}
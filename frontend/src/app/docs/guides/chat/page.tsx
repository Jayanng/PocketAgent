import { DocsPage } from "@/components/docs/docs-page";
import { ApiEndpoint, CodeBlock, DocsH2, DocsH3, DocsProse, DocsP, DocsUl } from "@/components/docs/docs-ui";

export default function ChatGuidePage() {
  return (
    <DocsPage
      title="Chat & Streaming"
      description="Send messages to an agent via REST or SSE and understand the event stream."
    >
      <DocsProse>
        <DocsH2 id="non-stream">Synchronous chat</DocsH2>
        <ApiEndpoint
          method="POST"
          path="/api/chat"
          auth="token"
          description="Single JSON response after the full turn completes (LLM + tool calls)."
        >
          <CodeBlock>{`curl -X POST http://127.0.0.1:8000/api/chat \\
  -H "Content-Type: application/json" \\
  -H "X-Agent-Access-Token: pa_..." \\
  -d '{
    "agent_id": "agent-uuid",
    "message": "Compare gas on Arbitrum vs Base",
    "conversation_id": null
  }'`}</CodeBlock>
        </ApiEndpoint>

        <DocsH2 id="stream">SSE streaming (recommended)</DocsH2>
        <ApiEndpoint
          method="POST"
          path="/api/chat/stream"
          auth="token"
          description="Server-Sent Events stream with token deltas, tool calls, and final message."
        />
        <DocsP>Event sequence:</DocsP>
        <DocsUl>
          <li><code className="font-mono text-[12px]">start</code> — turn began</li>
          <li><code className="font-mono text-[12px]">text_delta</code> — incremental assistant text</li>
          <li><code className="font-mono text-[12px]">tool_calls_start</code> / <code className="font-mono text-[12px]">tool_call</code> / <code className="font-mono text-[12px]">tool_result</code> — tool execution</li>
          <li><code className="font-mono text-[12px]">final</code> — completed message with chain_calls metadata</li>
          <li><code className="font-mono text-[12px]">error</code> — failure before close</li>
        </DocsUl>
        <DocsP>
          Keepalive SSE comments (<code className="font-mono text-[12px]">: keepalive</code>) flush every ~15s
          during long tool gathers so proxies do not drop the connection.
        </DocsP>

        <DocsH2 id="conversations">Conversations</DocsH2>
        <DocsUl>
          <li><code className="font-mono text-[12px]">GET /api/conversations?agent_id=...</code> — list threads</li>
          <li><code className="font-mono text-[12px]">GET /api/conversations/{"{id}"}/messages</code> — history</li>
          <li><code className="font-mono text-[12px]">DELETE /api/conversations/{"{id}"}</code> — remove thread</li>
          <li><code className="font-mono text-[12px]">GET /api/conversations/{"{id}"}/stream</code> — live tx confirmations</li>
        </DocsUl>

        <DocsH3>Request body fields</DocsH3>
        <DocsUl>
          <li><code className="font-mono text-[12px]">agent_id</code> (required)</li>
          <li><code className="font-mono text-[12px]">message</code> (required)</li>
          <li><code className="font-mono text-[12px]">conversation_id</code> (optional — omit to start new)</li>
          <li><code className="font-mono text-[12px]">connected_wallet_address</code> (optional — user wallet context)</li>
        </DocsUl>
      </DocsProse>
    </DocsPage>
  );
}
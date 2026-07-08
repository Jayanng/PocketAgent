import { DocsPage } from "@/components/docs/docs-page";
import { DocsH2, DocsH3, DocsLink, DocsProse, DocsP, DocsUl, Callout } from "@/components/docs/docs-ui";

export default function TroubleshootingPage() {
  return (
    <DocsPage title="Troubleshooting" description="Common integration issues and how to resolve them.">
      <DocsProse>
        <DocsH2 id="mcp">MCP server</DocsH2>
        <DocsH3>Tools not appearing in client</DocsH3>
        <DocsUl>
          <li>Restart the MCP client after editing config JSON</li>
          <li>Verify <code className="font-mono text-[12px]">pocketagent-mcp</code> is on PATH: <code className="font-mono text-[12px]">which pocketagent-mcp</code></li>
          <li>Check client logs for stdio spawn errors</li>
        </DocsUl>

        <DocsH3>Write tools fail with auth errors</DocsH3>
        <DocsP>
          Transact tools need a valid <code className="font-mono text-[12px]">agent_id</code> and agent row in
          the SQLite database pointed to by <code className="font-mono text-[12px]">DATABASE_PATH</code>.
          Create agents via the API or UI first.
        </DocsP>

        <DocsH2 id="api">REST API</DocsH2>
        <DocsH3>403 on agent endpoints</DocsH3>
        <DocsP>
          Include <code className="font-mono text-[12px]">X-Agent-Access-Token</code>. If lost, use{" "}
          <DocsLink href="/docs/concepts/authentication">token reissue</DocsLink>.
        </DocsP>

        <DocsH3>404 on API calls from frontend</DocsH3>
        <DocsP>
          Ensure <code className="font-mono text-[12px]">NEXT_PUBLIC_API_URL</code> has no trailing slash.
          A trailing <code className="font-mono text-[12px]">/</code> produces{" "}
          <code className="font-mono text-[12px]">{"//api/..."}</code> paths.
        </DocsP>

        <DocsH3>SSE stream drops mid-response</DocsH3>
        <DocsP>
          Proxies may timeout long tool gathers. The backend emits keepalive comments every ~15s. Ensure your
          reverse proxy does not buffer SSE (<code className="font-mono text-[12px]">X-Accel-Buffering: no</code>).
        </DocsP>

        <DocsH2 id="rpc">RPC / chains</DocsH2>
        <DocsH3>Chain unavailable or slow</DocsH3>
        <DocsP>
          Check <code className="font-mono text-[12px]">/api/analytics/chain-health</code> and the dashboard.
          Pocket Network gateway outages affect all tools for that chain slug.
        </DocsP>

        <DocsH2 id="llm">LLM errors</DocsH2>
        <DocsP>
          503 responses with OpenAI detail usually mean invalid <code className="font-mono text-[12px]">OPENAI_API_KEY</code>,
          wrong <code className="font-mono text-[12px]">OPENAI_BASE_URL</code>, or model unavailable. Verify
          credentials in <code className="font-mono text-[12px]">backend/.env</code>.
        </DocsP>

        <Callout type="tip" title="Still stuck?">
          Open an issue on{" "}
          <a
            href="https://github.com/Jayanng/PocketAgent/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="underline decoration-white/25 underline-offset-2"
          >
            GitHub
          </a>{" "}
          with MCP client logs, API response bodies, and redacted env var names.
        </Callout>
      </DocsProse>
    </DocsPage>
  );
}
import { DocsPage } from "@/components/docs/docs-page";
import { CodeBlock, DocsH2, DocsH3, DocsLink, DocsOl, DocsProse, DocsP, DocsUl } from "@/components/docs/docs-ui";

export default function DeploymentPage() {
  return (
    <DocsPage
      title="Deployment"
      description="Deploy the full platform with Docker or Fly.io; distribute MCP via PyPI."
    >
      <DocsProse>
        <DocsH2 id="mcp-only">MCP-only distribution</DocsH2>
        <DocsP>
          For editor integrations, users install{" "}
          <code className="font-mono text-[12px]">pokt-agent-mcp</code> from PyPI. No separate deployment
          required — the MCP client spawns <code className="font-mono text-[12px]">pocketagent-mcp</code> locally.
        </DocsP>

        <DocsH2 id="docker">Docker</DocsH2>
        <DocsP>The repository includes Dockerfiles for both services:</DocsP>
        <DocsUl>
          <li><code className="font-mono text-[12px]">backend/Dockerfile</code> — FastAPI + uvicorn</li>
          <li><code className="font-mono text-[12px]">frontend/Dockerfile</code> — Next.js production build</li>
        </DocsUl>
        <CodeBlock>{`# Example: build backend image
docker build -t pocketagent-api ./backend

# Run with env file
docker run --env-file backend/.env -p 8000:8000 pocketagent-api`}</CodeBlock>

        <DocsH2 id="fly">Fly.io</DocsH2>
        <DocsP>
          <code className="font-mono text-[12px]">frontend/fly.toml</code> configures the frontend app. Set
          secrets for API URL, WalletConnect project ID, and ensure the backend CORS origin matches your Fly
          hostname.
        </DocsP>

        <DocsH2 id="checklist">Production checklist</DocsH2>
        <DocsOl>
          <li>Configure all required env vars — see <DocsLink href="/docs/reference/configuration">Configuration</DocsLink></li>
          <li>Persist SQLite or migrate to a managed database path on durable volume</li>
          <li>Set <code className="font-mono text-[12px]">NEXT_PUBLIC_API_URL</code> without trailing slash</li>
          <li>Enable HTTPS termination at the edge</li>
          <li>Review <DocsLink href="/docs/security">Security</DocsLink> before exposing write tools</li>
        </DocsOl>

        <DocsH3>Health checks</DocsH3>
        <DocsP>
          Probe <code className="font-mono text-[12px]">GET /health</code> on the backend. Chat SSE endpoints
          should not be used as health checks — they hold connections open.
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}
import { DocsPage } from "@/components/docs/docs-page";
import {
  Callout,
  DocsCard,
  DocsCardGrid,
  DocsH2,
  DocsLink,
  DocsProse,
  DocsP,
  ApiEndpoint,
} from "@/components/docs/docs-ui";

export default function ApiOverviewPage() {
  return (
    <DocsPage
      title="REST API Overview"
      description="FastAPI backend with auto-generated OpenAPI documentation."
    >
      <DocsProse>
        <DocsP>
          Base URL defaults to <code className="font-mono text-[12px]">http://127.0.0.1:8000</code> in local
          development. Set <code className="font-mono text-[12px]">NEXT_PUBLIC_API_URL</code> in the frontend to
          match your deployment.
        </DocsP>

        <Callout type="tip" title="Interactive reference">
          When the backend is running, use Swagger UI at <code className="font-mono text-[12px]">/docs</code>{" "}
          or ReDoc at <code className="font-mono text-[12px]">/redoc</code> for live schema exploration.
        </Callout>

        <ApiEndpoint method="GET" path="/health" auth="none" description="Liveness probe — returns service status." />

        <DocsH2 id="sections">API sections</DocsH2>
        <DocsCardGrid>
          <DocsCard title="Agents" href="/docs/api/agents" description="CRUD, balances, funding, token reissue." />
          <DocsCard title="Chat" href="/docs/api/chat" description="Chat, SSE stream, conversations." />
          <DocsCard title="Analytics" href="/docs/api/analytics" description="Relay stats, chain health, portfolio." />
        </DocsCardGrid>

        <DocsH2 id="auth">Authentication</DocsH2>
        <DocsP>
          Agent-scoped routes require the <code className="font-mono text-[12px]">X-Agent-Access-Token</code>{" "}
          header. See <DocsLink href="/docs/concepts/authentication">Authentication</DocsLink> for issuance
          and reissue flows.
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}
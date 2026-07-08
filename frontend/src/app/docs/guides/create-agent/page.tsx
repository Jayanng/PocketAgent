import { DocsPage } from "@/components/docs/docs-page";
import { ApiEndpoint, CodeBlock, DocsH2, DocsLink, DocsProse, DocsP } from "@/components/docs/docs-ui";

export default function CreateAgentGuidePage() {
  return (
    <DocsPage
      title="Create an Agent"
      description="Create and configure an agent via the web UI or REST API."
    >
      <DocsProse>
        <DocsH2 id="ui">Web UI</DocsH2>
        <DocsP>
          Navigate to <DocsLink href="/agents">/agents</DocsLink>, click Create Agent, set a name,
          select chains and capabilities, and configure the spending cap. Save the access token when
          prompted — it cannot be recovered without reissue.
        </DocsP>

        <DocsH2 id="api">REST API</DocsH2>
        <ApiEndpoint
          method="POST"
          path="/api/agents"
          auth="none"
          description="Create a new agent with multi-chain wallets and return a one-time access token."
        >
          <CodeBlock>{`curl -X POST http://127.0.0.1:8000/api/agents \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Trading Assistant",
    "description": "Multi-chain gas analyst",
    "chains": ["ethereum", "arbitrum", "base"],
    "capabilities": ["read", "compare", "analytics"],
    "spending_cap": 0.05
  }'`}</CodeBlock>
        </ApiEndpoint>

        <DocsP>
          Response includes <code className="font-mono text-[12px]">id</code>,{" "}
          <code className="font-mono text-[12px]">access_token</code>, and{" "}
          <code className="font-mono text-[12px]">wallet_addresses</code> per protocol family.
        </DocsP>

        <DocsH2 id="update">Update configuration</DocsH2>
        <DocsP>
          Use <DocsLink href="/docs/api/agents">PUT /api/agents/{"{id}"}</DocsLink> with the access token
          header to change chains, capabilities, or spending cap. Wallet keys are not rotated on update.
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}
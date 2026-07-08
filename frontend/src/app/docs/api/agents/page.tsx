import { DocsPage } from "@/components/docs/docs-page";
import { ApiEndpoint, CodeBlock, DocsProse } from "@/components/docs/docs-ui";

export default function ApiAgentsPage() {
  return (
    <DocsPage title="Agents API" description="Create, configure, fund, and authenticate agents.">
      <DocsProse>
        <ApiEndpoint method="POST" path="/api/agents" auth="none" description="Create agent. Returns id, access_token (once), wallet_addresses.">
          <CodeBlock>{`{
  "name": "string",
  "description": "string | null",
  "chains": ["ethereum", "base"],
  "capabilities": ["read", "compare", "transact", "analytics"],
  "spending_cap": 0.1
}`}</CodeBlock>
        </ApiEndpoint>

        <ApiEndpoint method="GET" path="/api/agents" auth="none" description="List all agents (summary fields only)." />
        <ApiEndpoint method="GET" path="/api/agents/{id}" auth="token" description="Full agent detail excluding encrypted key material." />
        <ApiEndpoint method="PUT" path="/api/agents/{id}" auth="token" description="Update name, chains, capabilities, or spending_cap." />
        <ApiEndpoint method="DELETE" path="/api/agents/{id}" auth="token" description="Soft-delete — sets is_active=false (204 No Content)." />
        <ApiEndpoint method="GET" path="/api/agents/{id}/balances" auth="token" description="Multi-chain native balances for the agent wallets." />
        <ApiEndpoint method="POST" path="/api/agents/{id}/fund" auth="token" description="Funding instructions and deposit addresses." />
        <ApiEndpoint method="GET" path="/api/agents/{id}/reissue-challenge" auth="none" description="Canonical message for wallet-signature token reissue." />
        <ApiEndpoint method="POST" path="/api/agents/{id}/reissue-token" auth="none" description="Reissue access token with current_token or wallet_signature proof." />
      </DocsProse>
    </DocsPage>
  );
}
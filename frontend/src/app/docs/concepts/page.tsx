import { DocsPage } from "@/components/docs/docs-page";
import { DocsCard, DocsCardGrid, DocsH2, DocsProse, DocsP } from "@/components/docs/docs-ui";

export default function ConceptsPage() {
  return (
    <DocsPage
      title="Platform Overview"
      description="How PocketAgent connects natural language, blockchain tools, and Pocket Network RPC."
    >
      <DocsProse>
        <DocsP>
          PocketAgent follows a single principle: one tool registry, multiple surfaces. The same 51
          blockchain tools power the chat UI, REST API orchestration, and MCP server. An LLM selects
          tools autonomously; the backend enforces caps and signs transactions when needed.
        </DocsP>

        <DocsH2 id="lifecycle">Agent lifecycle</DocsH2>
        <DocsP>
          Create an agent with chains and capabilities → fund its multi-chain wallets → chat via UI or
          API, or schedule Automations for recurring prompts → the agent reads chain state and optionally
          broadcasts writes → monitor relay stats, automation run history, and costs on the dashboard.
        </DocsP>

        <DocsCardGrid>
          <DocsCard title="Architecture" href="/docs/concepts/architecture" description="Frontend, FastAPI, MCP adapter, and RPC gateway layers." />
          <DocsCard title="Agents" href="/docs/concepts/agents" description="Capabilities, spending caps, and encrypted wallets." />
          <DocsCard title="Authentication" href="/docs/concepts/authentication" description="Per-agent tokens, reissue, and wallet proof." />
        </DocsCardGrid>
      </DocsProse>
    </DocsPage>
  );
}
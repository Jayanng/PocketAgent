import { DocsPage } from "@/components/docs/docs-page";
import {
  Callout,
  DocsCard,
  DocsCardGrid,
  DocsInlineCode,
  DocsLink,
  DocsProse,
  DocsP,
} from "@/components/docs/docs-ui";
import { TEST_STATS } from "@/lib/test-stats";
import { DOCS_VERSION } from "@/lib/docs/nav";

export default function DocsOverviewPage() {
  return (
    <DocsPage
      title="PocketAgent Documentation"
      description="Integrate AI agents across 52 blockchains via Pocket Network decentralized RPC — REST API, MCP server, or the full web platform."
      version={DOCS_VERSION}
    >
      <DocsProse>
        <DocsP>
          PocketAgent is a full-stack platform where AI agents orchestrate blockchain operations
          through natural language. Every RPC call routes through Pocket Network&apos;s Shannon gateway —
          no Infura, Alchemy, or centralized API keys required.
        </DocsP>

        <Callout type="tip" title="Choose your integration path">
          <ul className="list-disc space-y-1 pl-4">
            <li>
              <strong>MCP only</strong> — <DocsInlineCode>pip install pokt-agent-mcp</DocsInlineCode> and
              add 51 tools to Claude Desktop, Cursor, or Codex.
            </li>
            <li>
              <strong>REST API</strong> — Build your own UI against the FastAPI backend with OpenAPI docs.
            </li>
            <li>
              <strong>Full platform</strong> — Run the Next.js chat UI, agent dashboard, and analytics locally
              or deploy to production.
            </li>
          </ul>
        </Callout>

        <DocsCardGrid>
          <DocsCard
            title="Quick Start"
            href="/docs/getting-started"
            description="Install pokt-agent-mcp, configure an MCP client, or run the full stack locally."
          />
          <DocsCard
            title="REST API"
            href="/docs/api"
            description="Agent CRUD, SSE chat streaming, conversations, and analytics endpoints."
          />
          <DocsCard
            title="MCP Server"
            href="/docs/mcp"
            description="51 tools, 5 resources, and 4 prompts over stdio transport."
          />
          <DocsCard
            title="Supported Chains"
            href="/docs/reference/chains"
            description="52 production networks across EVM, Cosmos, Solana, SUI, NEAR, and TRON."
          />
        </DocsCardGrid>

        <DocsP>
          The platform ships with {TEST_STATS.total} automated tests ({TEST_STATS.backend} backend,{" "}
          {TEST_STATS.frontend} frontend), per-agent spending caps, encrypted multi-chain wallets, and
          real-time transaction confirmation streaming.
        </DocsP>

        <DocsP>
          New to PocketAgent? Start with{" "}
          <DocsLink href="/docs/getting-started">Quick Start</DocsLink>, then read{" "}
          <DocsLink href="/docs/concepts/agents">how agents work</DocsLink> before calling write tools.
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}
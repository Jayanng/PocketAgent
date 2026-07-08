import { DocsPage } from "@/components/docs/docs-page";
import { CodeBlock, DocsCard, DocsCardGrid, DocsH2, DocsLink, DocsProse, DocsP, Callout } from "@/components/docs/docs-ui";

export default function McpOverviewPage() {
  return (
    <DocsPage
      title="MCP Server"
      description="Standalone stdio MCP server exposing 51 tools, 5 resources, and 4 prompts."
    >
      <DocsProse>
        <DocsP>
          The MCP server is a thin adapter over <code className="font-mono text-[12px]">TOOL_REGISTRY</code>.
          Any MCP-compatible client can list tools, call them, read resources, and use prompts — with the
          same executors as the PocketAgent chat UI.
        </DocsP>

        <CodeBlock>{`pip install pokt-agent-mcp
# MCP client spawns:
pocketagent-mcp`}</CodeBlock>

        <Callout type="info" title="Why MCP?">
          PocketAgent reimplements BlockchainQuery&apos;s 32-tool read surface and adds 19 custom tools —
          compare, guarded writes, non-EVM transfers, analytics, simulation, and portfolio analysis.
        </Callout>

        <DocsH2 id="surfaces">MCP surfaces</DocsH2>
        <DocsCardGrid>
          <DocsCard title="Tools" href="/docs/mcp/tools" description="51 typed blockchain functions." />
          <DocsCard title="Resources" href="/docs/mcp/resources" description="Chain, agent, and cache URIs." />
          <DocsCard title="Prompts" href="/docs/mcp/prompts" description="4 built-in workflow prompts." />
        </DocsCardGrid>

        <DocsP>
          Setup instructions: <DocsLink href="/docs/getting-started/mcp-setup">MCP Client Setup</DocsLink>.
          Extended reference also lives in the repository at{" "}
          <a
            href="https://github.com/Jayanng/PocketAgent/blob/main/docs/mcp-server.md"
            target="_blank"
            rel="noopener noreferrer"
            className="underline decoration-white/25 underline-offset-2"
          >
            docs/mcp-server.md
          </a>
          .
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}
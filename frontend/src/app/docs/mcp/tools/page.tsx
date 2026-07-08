import { DocsPage } from "@/components/docs/docs-page";
import { McpToolsReference } from "@/components/docs/mcp-tools-reference";

export default function McpToolsPage() {
  return (
    <DocsPage
      title="MCP Tools"
      description="Complete reference for all 51 blockchain tools in the pokt-agent-mcp package."
    >
      <McpToolsReference />
    </DocsPage>
  );
}
import { DocsPage } from "@/components/docs/docs-page";
import {
  Callout,
  CodeBlock,
  DocsH2,
  DocsH3,
  DocsLink,
  DocsProse,
  DocsP,
  DocsTable,
} from "@/components/docs/docs-ui";

const MCP_CONFIG = `{
  "mcpServers": {
    "pocketagent": {
      "command": "pocketagent-mcp",
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ENCRYPTION_KEY": "your-32-byte-key",
        "JWT_SECRET": "your-jwt-secret",
        "DATABASE_PATH": "/absolute/path/to/pocketagent.db"
      }
    }
  }
}`;

export default function McpSetupPage() {
  return (
    <DocsPage
      title="MCP Client Setup"
      description="Configure Claude Desktop, Cursor, or Codex to launch the PocketAgent MCP server."
    >
      <DocsProse>
        <DocsH2 id="config">Base configuration</DocsH2>
        <DocsP>
          After <DocsLink href="/docs/getting-started/installation">installing pokt-agent-mcp</DocsLink>,
          add this block to your MCP client config:
        </DocsP>
        <CodeBlock>{MCP_CONFIG}</CodeBlock>

        <Callout type="info" title="DATABASE_PATH">
          When installed via pip, use an absolute path for <code className="font-mono text-[12px]">DATABASE_PATH</code>{" "}
          so agent rows resolve regardless of the MCP client&apos;s working directory.
        </Callout>

        <DocsH2 id="clients">Client-specific paths</DocsH2>
        <DocsTable>
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-4 py-3 font-semibold">Client</th>
              <th className="px-4 py-3 font-semibold">Config file</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5">Claude Desktop (macOS)</td>
              <td className="px-4 py-2.5 font-mono text-[11px]">~/Library/Application Support/Claude/claude_desktop_config.json</td>
            </tr>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5">Claude Desktop (Windows)</td>
              <td className="px-4 py-2.5 font-mono text-[11px]">%APPDATA%\\Claude\\claude_desktop_config.json</td>
            </tr>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5">Cursor</td>
              <td className="px-4 py-2.5 font-mono text-[11px]">.cursor/mcp.json (project) or global MCP settings</td>
            </tr>
            <tr>
              <td className="px-4 py-2.5">Codex / other</td>
              <td className="px-4 py-2.5 font-mono text-[11px]">Equivalent mcpServers JSON in client settings</td>
            </tr>
          </tbody>
        </DocsTable>

        <DocsH2 id="source-alt">Source install alternative</DocsH2>
        <DocsP>If running from the repository without pip:</DocsP>
        <CodeBlock>{`{
  "mcpServers": {
    "pocketagent": {
      "command": "python",
      "args": ["-m", "pocketagent.mcp_server.server"],
      "cwd": "/path/to/PocketAgent/backend",
      "env": { ... }
    }
  }
}`}</CodeBlock>

        <DocsH2 id="write-tools">Write tools and agent context</DocsH2>
        <DocsP>
          Read tools work without an agent. Transact tools (sends, contract writes, token transfers)
          require an <code className="font-mono text-[12px]">agent_id</code> and valid access token in the
          tool arguments. Create agents via the REST API or web UI first — see{" "}
          <DocsLink href="/docs/guides/create-agent">Create an Agent</DocsLink>.
        </DocsP>

        <DocsH3>Module invocation (debugging)</DocsH3>
        <CodeBlock>python -m pocketagent.mcp_server.server</CodeBlock>
        <DocsP>Blocks on stdio until a client connects. Use only for debugging transport issues.</DocsP>
      </DocsProse>
    </DocsPage>
  );
}
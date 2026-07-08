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
import { DOCS_VERSION } from "@/lib/docs/nav";
import { DOCS_SNIPPETS } from "@/lib/docs/snippets";

export default function InstallationPage() {
  return (
    <DocsPage
      title="Installation"
      description="Install the pokt-agent-mcp PyPI package or build from the PocketAgent repository."
      version={DOCS_VERSION}
    >
      <DocsProse>
        <DocsH2 id="requirements">Requirements</DocsH2>
        <DocsP>Python 3.11 or newer. A compatible MCP stdio client (Claude Desktop, Cursor, Codex, etc.).</DocsP>

        <DocsH2 id="pypi">PyPI install (recommended)</DocsH2>
        <CodeBlock>pip install pokt-agent-mcp</CodeBlock>
        <DocsP>
          Published on{" "}
          <a
            href="https://pypi.org/project/pokt-agent-mcp/"
            target="_blank"
            rel="noopener noreferrer"
            className="underline decoration-white/25 underline-offset-2"
          >
            PyPI
          </a>
          . The import namespace remains <code className="font-mono text-[12px]">pocketagent</code>; the
          console script is <code className="font-mono text-[12px]">pocketagent-mcp</code>.
        </DocsP>

        <DocsH3>Optional REST API extras</DocsH3>
        <CodeBlock>{DOCS_SNIPPETS.pipInstallMcpApi}</CodeBlock>
        <DocsP>Includes FastAPI and Uvicorn if you want to run the full backend from the installed package.</DocsP>

        <DocsH2 id="source">Install from source</DocsH2>
        <CodeBlock>{`git clone https://github.com/Jayanng/PocketAgent.git
pip install ./PocketAgent/backend`}</CodeBlock>
        <DocsP>Equivalent to the PyPI package but tracks the latest main branch.</DocsP>

        <DocsH2 id="verify">Verify installation</DocsH2>
        <CodeBlock>{`pocketagent-mcp --help
python -c "from pocketagent.tools import TOOL_REGISTRY; print(len(TOOL_REGISTRY), 'tools')"`}</CodeBlock>
        <DocsP>You should see 51 registered tools.</DocsP>

        <DocsH2 id="package-map">Package mapping</DocsH2>
        <DocsTable>
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-4 py-3 font-semibold">Surface</th>
              <th className="px-4 py-3 font-semibold">Name</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5 opacity-70">PyPI package</td>
              <td className="px-4 py-2.5 font-mono text-[12px]">pokt-agent-mcp</td>
            </tr>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5 opacity-70">Python import</td>
              <td className="px-4 py-2.5 font-mono text-[12px]">pocketagent</td>
            </tr>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5 opacity-70">CLI entry point</td>
              <td className="px-4 py-2.5 font-mono text-[12px]">pocketagent-mcp</td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 opacity-70">MCP server key</td>
              <td className="px-4 py-2.5 font-mono text-[12px]">pocketagent</td>
            </tr>
          </tbody>
        </DocsTable>

        <Callout type="warning" title="Do not run MCP manually in production">
          The stdio server is designed to be spawned by your MCP client. Running it in a terminal
          without a connected client will block until disconnect.
        </Callout>

        <DocsP>
          Next: <DocsLink href="/docs/getting-started/mcp-setup">Configure your MCP client</DocsLink>
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}
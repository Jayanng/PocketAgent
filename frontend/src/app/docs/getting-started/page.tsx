import { DocsPage } from "@/components/docs/docs-page";
import {
  Callout,
  CodeBlock,
  DocsCard,
  DocsCardGrid,
  DocsH2,
  DocsLink,
  DocsOl,
  DocsProse,
  DocsP,
} from "@/components/docs/docs-ui";

export default function GettingStartedPage() {
  return (
    <DocsPage
      title="Quick Start"
      description="Get PocketAgent running in under five minutes — MCP-only or full platform."
    >
      <DocsProse>
        <DocsH2 id="paths">Integration paths</DocsH2>
        <DocsCardGrid>
          <DocsCard
            title="MCP package (recommended for editors)"
            href="/docs/getting-started/installation"
            description="pip install pokt-agent-mcp — drop 51 blockchain tools into your AI client."
          />
          <DocsCard
            title="Full platform"
            href="/docs/getting-started/local-development"
            description="Next.js UI + FastAPI backend — agents, chat, Automations, and analytics."
          />
        </DocsCardGrid>

        <DocsH2 id="mcp-fast">Fastest path: MCP in 2 steps</DocsH2>
        <DocsOl>
          <li>
            Install the package:
            <CodeBlock>pip install pokt-agent-mcp</CodeBlock>
          </li>
          <li>
            Add the server to your MCP client config — see{" "}
            <DocsLink href="/docs/getting-started/mcp-setup">MCP Client Setup</DocsLink> for
            Claude Desktop, Cursor, and Codex paths.
          </li>
        </DocsOl>

        <Callout type="info" title="Console script">
          After install, the <code className="font-mono text-[12px]">pocketagent-mcp</code> command is
          on your PATH. MCP clients spawn it as a stdio subprocess.
        </Callout>

        <DocsH2 id="platform-fast">Full platform in 4 steps</DocsH2>
        <CodeBlock>{`git clone https://github.com/Jayanng/PocketAgent.git
cd PocketAgent
npm install
cd backend && pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY, ENCRYPTION_KEY, JWT_SECRET
cd .. && npm run dev`}</CodeBlock>
        <DocsP>
          Opens the web UI at <code className="font-mono text-[12px]">localhost:3000</code> and the REST
          API at <code className="font-mono text-[12px]">localhost:8000</code>. Interactive OpenAPI docs
          live at <code className="font-mono text-[12px]">/docs</code>.
        </DocsP>

        <DocsH2 id="next">Next steps</DocsH2>
        <DocsOl>
          <li>
            <DocsLink href="/docs/guides/create-agent">Create an agent</DocsLink> with chains and
            capabilities
          </li>
          <li>
            <DocsLink href="/docs/guides/fund-agent">Fund the agent wallet</DocsLink> on your target
            chains
          </li>
          <li>
            <DocsLink href="/docs/guides/chat">Start chatting</DocsLink> via the UI or REST API
          </li>
        </DocsOl>
      </DocsProse>
    </DocsPage>
  );
}
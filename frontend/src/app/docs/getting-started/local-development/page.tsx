import { DocsPage } from "@/components/docs/docs-page";
import {
  Callout,
  CodeBlock,
  DocsH2,
  DocsH3,
  DocsLink,
  DocsOl,
  DocsProse,
  DocsP,
  DocsUl,
} from "@/components/docs/docs-ui";

export default function LocalDevelopmentPage() {
  return (
    <DocsPage
      title="Local Development"
      description="Run the full PocketAgent platform — Next.js frontend and FastAPI backend — on your machine."
    >
      <DocsProse>
        <DocsH2 id="prerequisites">Prerequisites</DocsH2>
        <DocsUl>
          <li>Node.js 20+ and npm</li>
          <li>Python 3.11+</li>
          <li>An OpenAI-compatible API key</li>
          <li>WalletConnect project ID (for RainbowKit wallet connections)</li>
        </DocsUl>

        <DocsH2 id="clone">Clone and install</DocsH2>
        <CodeBlock>{`git clone https://github.com/Jayanng/PocketAgent.git
cd PocketAgent
npm install
cd backend && pip install -r requirements.txt`}</CodeBlock>

        <DocsH2 id="env">Configure environment</DocsH2>
        <DocsH3>Backend</DocsH3>
        <CodeBlock>{`cd backend
cp .env.example .env`}</CodeBlock>
        <DocsP>
          Set at minimum <code className="font-mono text-[12px]">OPENAI_API_KEY</code>,{" "}
          <code className="font-mono text-[12px]">ENCRYPTION_KEY</code>, and{" "}
          <code className="font-mono text-[12px]">JWT_SECRET</code>. See the full reference in{" "}
          <DocsLink href="/docs/reference/configuration">Configuration</DocsLink>.
        </DocsP>

        <DocsH3>Frontend</DocsH3>
        <CodeBlock>{`cd frontend
cp .env.example .env.local`}</CodeBlock>
        <DocsP>
          Set <code className="font-mono text-[12px]">NEXT_PUBLIC_API_URL=http://127.0.0.1:8000</code>{" "}
          (no trailing slash) and your WalletConnect project ID.
        </DocsP>

        <DocsH2 id="run">Start dev servers</DocsH2>
        <CodeBlock>npm run dev</CodeBlock>
        <DocsP>From the repository root. Runs frontend (:3000) and backend (:8000) concurrently.</DocsP>

        <DocsOl>
          <li>
            Web UI — <code className="font-mono text-[12px]">http://localhost:3000</code>
          </li>
          <li>
            REST API — <code className="font-mono text-[12px]">http://127.0.0.1:8000</code>
          </li>
          <li>
            Swagger UI — <code className="font-mono text-[12px]">http://127.0.0.1:8000/docs</code>
          </li>
          <li>
            ReDoc — <code className="font-mono text-[12px]">http://127.0.0.1:8000/redoc</code>
          </li>
        </DocsOl>

        <Callout type="tip" title="Local auth bypass">
          For UI-only development you can set <code className="font-mono text-[12px]">DISABLE_AGENT_AUTH=true</code>{" "}
          in the backend and <code className="font-mono text-[12px]">NEXT_PUBLIC_DISABLE_AGENT_AUTH=true</code>{" "}
          in the frontend. Never use this in production.
        </Callout>

        <DocsH2 id="test">Run tests</DocsH2>
        <CodeBlock>{`cd backend && pytest -q
cd frontend && npm test`}</CodeBlock>
      </DocsProse>
    </DocsPage>
  );
}
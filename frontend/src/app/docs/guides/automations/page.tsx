import { DocsPage } from "@/components/docs/docs-page";
import {
  Callout,
  CodeBlock,
  DocsH2,
  DocsH3,
  DocsLink,
  DocsProse,
  DocsP,
  DocsUl,
} from "@/components/docs/docs-ui";

export default function AutomationsGuidePage() {
  return (
    <DocsPage
      title="Automations"
      description="Schedule recurring prompts so agents run on a timer via Pocket Network relays — without opening chat."
    >
      <DocsProse>
        <DocsP>
          Automations (API name: <code className="font-mono text-[12px]">scheduled-tasks</code>) are
          recurring jobs tied to an agent. On each tick the backend runs the same LLM + tool path as
          chat, against Pocket Network RPC when tools need chain data.
        </DocsP>

        <Callout type="tip" title="Web UI">
          Open <strong>Automations</strong> in the app nav (
          <code className="font-mono text-[12px]">/scheduled-tasks</code>
          ). Create jobs from templates, toggle enable, inspect last result, expand relay breakdown,
          and copy a cURL snippet.
        </Callout>

        <DocsH2 id="prerequisites">Prerequisites</DocsH2>
        <DocsUl>
          <li>
            An agent with a saved <DocsLink href="/docs/concepts/authentication">access token</DocsLink>{" "}
            in the browser (or pass{" "}
            <code className="font-mono text-[12px]">X-Agent-Access-Token</code> for API calls).
          </li>
          <li>
            Capabilities that match the prompt (e.g. <code className="font-mono text-[12px]">read</code>{" "}
            / <code className="font-mono text-[12px]">compare</code> for gas checks).
          </li>
          <li>
            For write prompts: funded wallets,{" "}
            <code className="font-mono text-[12px]">transact</code>, and a safe spending cap.
          </li>
        </DocsUl>

        <DocsH2 id="intervals">Intervals</DocsH2>
        <DocsP>
          <code className="font-mono text-[12px]">interval_seconds</code> must be between{" "}
          <strong>60</strong> (1 minute) and <strong>604800</strong> (7 days). The scheduler polls about
          every 30 seconds and runs any due, enabled job.
        </DocsP>
        <DocsP>UI presets include 5m, 15m, 1h, 6h, 12h, 24h, and weekly.</DocsP>

        <DocsH2 id="templates">Starter templates</DocsH2>
        <DocsUl>
          <li>
            <strong>Daily portfolio report</strong> — full multi-chain summary with USD values (24h)
          </li>
          <li>
            <strong>Hourly gas check</strong> — gas on major EVM L2s (1h)
          </li>
          <li>
            <strong>Balance monitor</strong> — balances across chains (6h)
          </li>
          <li>
            <strong>Weekly rebalance reminder</strong> — allocation concentration checks (7d)
          </li>
        </DocsUl>

        <DocsH2 id="relays">Pocket relays</DocsH2>
        <DocsP>
          Each run records a row in <code className="font-mono text-[12px]">scheduled_task_runs</code>.
          Relay counts estimate how many Pocket RPC calls occurred during that run window (tools that
          hit the chain). Pure LLM replies with no tools may show{" "}
          <code className="font-mono text-[12px]">0</code> relays — that is expected.
        </DocsP>
        <DocsP>
          Fetch breakdowns with{" "}
          <DocsLink href="/docs/api/automations">GET …/relay-stats</DocsLink> or the Relays column in the
          UI.
        </DocsP>

        <DocsH2 id="quick-api">Quick API create</DocsH2>
        <CodeBlock>{`curl -X POST 'http://127.0.0.1:8000/api/scheduled-tasks' \\
  -H 'Content-Type: application/json' \\
  -H 'X-Agent-Access-Token: YOUR_TOKEN' \\
  -d '{
    "agent_id": "agent-uuid",
    "prompt": "Compare gas on Arbitrum vs Base and summarize",
    "interval_seconds": 3600
  }'`}</CodeBlock>

        <DocsH3>Safety notes</DocsH3>
        <DocsUl>
          <li>Start with read-only prompts and short intervals while testing.</li>
          <li>Disable or delete automations before large fund deposits if you are unsure.</li>
          <li>
            Write automations use the same spending caps as chat — review caps before enabling.
          </li>
        </DocsUl>

        <DocsP>
          Full endpoint list: <DocsLink href="/docs/api/automations">Automations API</DocsLink>.
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}

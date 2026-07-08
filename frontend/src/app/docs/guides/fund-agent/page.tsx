import { DocsPage } from "@/components/docs/docs-page";
import { ApiEndpoint, CodeBlock, DocsH2, DocsProse, DocsP, DocsUl } from "@/components/docs/docs-ui";

export default function FundAgentGuidePage() {
  return (
    <DocsPage
      title="Fund an Agent"
      description="Deposit native assets and tokens to an agent's multi-chain wallets."
    >
      <DocsProse>
        <DocsP>
          Agents need native gas on each chain before write tools can broadcast. The dashboard and API
          expose live balances; the fund endpoint returns deposit addresses and guidance.
        </DocsP>

        <DocsH2 id="addresses">Wallet addresses</DocsH2>
        <DocsP>
          After creation, inspect <code className="font-mono text-[12px]">wallet_addresses</code> on the agent
          detail response. EVM chains share one address; Solana, SUI, NEAR, Cosmos, and TRON each have
          protocol-specific addresses.
        </DocsP>

        <ApiEndpoint
          method="GET"
          path="/api/agents/{id}/balances"
          auth="token"
          description="Query native balances across the agent's enabled chains via Pocket Network RPC."
        />

        <ApiEndpoint
          method="POST"
          path="/api/agents/{id}/fund"
          auth="token"
          description="Return funding instructions and addresses for the agent's configured chains."
        >
          <CodeBlock>{`curl -X POST http://127.0.0.1:8000/api/agents/{id}/fund \\
  -H "X-Agent-Access-Token: pa_..."`}</CodeBlock>
        </ApiEndpoint>

        <DocsH2 id="assets">Supported asset types</DocsH2>
        <DocsUl>
          <li>Native gas: ETH, POL, SOL, SUI, NEAR, OSMO, TRX, etc.</li>
          <li>EVM tokens: ERC-20 via <code className="font-mono text-[12px]">send_erc20</code></li>
          <li>Solana: SPL via <code className="font-mono text-[12px]">send_spl_token</code></li>
          <li>Cosmos: CW20 and IBC transfers</li>
          <li>TRON: TRC-20 · NEAR: NEP-141 · SUI: coin types</li>
        </DocsUl>
      </DocsProse>
    </DocsPage>
  );
}
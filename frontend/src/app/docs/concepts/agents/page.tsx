import { DocsPage } from "@/components/docs/docs-page";
import { DocsH2, DocsH3, DocsProse, DocsP, DocsTable, DocsUl, Callout } from "@/components/docs/docs-ui";

export default function AgentsConceptPage() {
  return (
    <DocsPage
      title="Agents"
      description="How PocketAgent agents are configured, funded, and authorized to use blockchain tools."
    >
      <DocsProse>
        <DocsP>
          An agent is an isolated identity with its own multi-chain wallets, capability set, spending caps,
          and access token. The LLM orchestrator only invokes tools the agent is allowed to use.
        </DocsP>

        <DocsH2 id="fields">Core fields</DocsH2>
        <DocsTable>
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-4 py-3 font-semibold">Field</th>
              <th className="px-4 py-3 font-semibold">Description</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5 font-mono text-[12px]">name</td>
              <td className="px-4 py-2.5 opacity-75">Display name</td>
            </tr>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5 font-mono text-[12px]">chains</td>
              <td className="px-4 py-2.5 opacity-75">Subset of 52 supported chain keys the agent may target</td>
            </tr>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5 font-mono text-[12px]">capabilities</td>
              <td className="px-4 py-2.5 opacity-75">Tool capability groups: read, compare, transact, analytics</td>
            </tr>
            <tr className="border-b border-white/5">
              <td className="px-4 py-2.5 font-mono text-[12px]">spending_cap</td>
              <td className="px-4 py-2.5 opacity-75">Per-chain notional spend limit enforced before broadcast</td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 font-mono text-[12px]">wallet_addresses</td>
              <td className="px-4 py-2.5 opacity-75">Derived addresses for EVM, Solana, SUI, NEAR, Cosmos, TRON</td>
            </tr>
          </tbody>
        </DocsTable>

        <DocsH2 id="capabilities">Capability groups</DocsH2>
        <DocsUl>
          <li><strong>read</strong> — Balance queries, blocks, transactions, token metadata. Always available when enabled.</li>
          <li><strong>compare</strong> — Gas comparison, chain recommendation, cost estimation.</li>
          <li><strong>transact</strong> — Sends, token transfers, contract writes, simulation. Gated by caps and balance.</li>
          <li><strong>analytics</strong> — Relay stats, history, and cost breakdown for the agent.</li>
        </DocsUl>

        <DocsH2 id="wallets">Multi-chain wallets</DocsH2>
        <DocsP>
          On creation, the platform generates protocol-specific key material, encrypts it with{" "}
          <code className="font-mono text-[12px]">ENCRYPTION_KEY</code>, and exposes public addresses per chain family.
          Write tools sign with the appropriate encrypted key for the target protocol.
        </DocsP>

        <DocsH3>Soft delete</DocsH3>
        <DocsP>
          Deleting an agent sets <code className="font-mono text-[12px]">is_active=false</code>. Inactive agents
          return HTTP 410 on chat and protected endpoints.
        </DocsP>

        <Callout type="warning" title="Fund before writes">
          Transact tools check wallet balance and spending caps before broadcast. Fund the agent on each
          target chain before asking it to send tokens or contract calls.
        </Callout>
      </DocsProse>
    </DocsPage>
  );
}
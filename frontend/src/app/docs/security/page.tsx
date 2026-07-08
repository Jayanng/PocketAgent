import { DocsPage } from "@/components/docs/docs-page";
import { DocsH2, DocsProse, DocsP, DocsUl, Callout } from "@/components/docs/docs-ui";

export default function SecurityPage() {
  return (
    <DocsPage
      title="Security"
      description="Encryption, spending caps, write-tool gates, and production hardening."
    >
      <DocsProse>
        <DocsH2 id="keys">Key material</DocsH2>
        <DocsUl>
          <li>Agent private keys are AES-256 encrypted with <code className="font-mono text-[12px]">ENCRYPTION_KEY</code> before SQLite storage.</li>
          <li>Access tokens are stored as hashes only — plaintext shown once at creation.</li>
          <li>API responses never include <code className="font-mono text-[12px]">encrypted_private_key</code> or token hashes.</li>
        </DocsUl>

        <DocsH2 id="write-gates">Write-tool gates</DocsH2>
        <DocsUl>
          <li><strong>Capability check</strong> — Agent must have <code className="font-mono text-[12px]">transact</code> enabled.</li>
          <li><strong>Spending cap</strong> — Per-chain notional spend evaluated before broadcast.</li>
          <li><strong>Balance check</strong> — Native gas balance verified on the target chain.</li>
          <li><strong>Simulation</strong> — <code className="font-mono text-[12px]">simulate_transaction</code> dry-runs before optional broadcast.</li>
          <li><strong>Testnet rejection</strong> — Write tools reject testnet/Tenderly URLs in production configs.</li>
        </DocsUl>

        <DocsH2 id="read-tools">Read tools</DocsH2>
        <DocsP>
          Read and compare tools incur only Pocket relay costs. They do not require funded agent wallets unless
          querying agent-scoped analytics.
        </DocsP>

        <Callout type="warning" title="Production checklist">
          <DocsUl>
            <li>Use strong random <code className="font-mono text-[12px]">ENCRYPTION_KEY</code> and <code className="font-mono text-[12px]">JWT_SECRET</code></li>
            <li>Keep <code className="font-mono text-[12px]">DISABLE_AGENT_AUTH=false</code></li>
            <li>Restrict <code className="font-mono text-[12px]">CORS_ORIGINS</code> to your frontend domain</li>
            <li>Use HTTPS and absolute <code className="font-mono text-[12px]">DATABASE_PATH</code> for MCP installs</li>
          </DocsUl>
        </Callout>
      </DocsProse>
    </DocsPage>
  );
}
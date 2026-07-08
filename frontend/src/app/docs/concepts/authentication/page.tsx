import { DocsPage } from "@/components/docs/docs-page";
import { CodeBlock, DocsH2, DocsH3, DocsLink, DocsOl, DocsProse, DocsP, Callout } from "@/components/docs/docs-ui";

export default function AuthenticationPage() {
  return (
    <DocsPage
      title="Authentication"
      description="Per-agent access tokens, the X-Agent-Access-Token header, and wallet-signature reissue."
    >
      <DocsProse>
        <DocsP>
          Most agent-scoped endpoints require a bearer-style header. The server stores only a hash of the
          token — the plaintext is returned once at creation and must be saved by the client.
        </DocsP>

        <DocsH2 id="header">Request header</DocsH2>
        <CodeBlock>X-Agent-Access-Token: pa_xxxxxxxxxxxxxxxx</CodeBlock>

        <DocsH2 id="issuance">Token issuance</DocsH2>
        <DocsOl>
          <li>
            <DocsLink href="/docs/api/agents">POST /api/agents</DocsLink> returns{" "}
            <code className="font-mono text-[12px]">access_token</code> in the response body (one time only).
          </li>
          <li>The frontend stores it in session storage keyed by agent ID and syncs across tabs via BroadcastChannel.</li>
          <li>Subsequent GET/PUT/DELETE/chat calls include the header.</li>
        </DocsOl>

        <DocsH2 id="reissue">Token reissue</DocsH2>
        <DocsP>When a token is lost, reissue with one of two proofs:</DocsP>

        <DocsH3>Current token proof</DocsH3>
        <CodeBlock>{`POST /api/agents/{id}/reissue-token
{
  "proof": {
    "type": "current_token",
    "token": "pa_existing_token"
  }
}`}</CodeBlock>

        <DocsH3>Wallet signature proof</DocsH3>
        <DocsOl>
          <li>GET <code className="font-mono text-[12px]">/api/agents/{"{id}"}/reissue-challenge</code> for a canonical message</li>
          <li>Sign the message with a wallet that matches an agent address on the chosen chain</li>
          <li>POST the signature as <code className="font-mono text-[12px]">wallet_signature</code> proof</li>
        </DocsOl>
        <CodeBlock>{`{
  "proof": {
    "type": "wallet_signature",
    "chain": "ethereum",
    "message": "pocketagent:reissue:...",
    "signature": "0x...",
    "public_key": ""
  }
}`}</CodeBlock>

        <Callout type="warning" title="Production">
          Never set <code className="font-mono text-[12px]">DISABLE_AGENT_AUTH=true</code> outside local
          development. Write tools and agent data require valid tokens in production.
        </Callout>
      </DocsProse>
    </DocsPage>
  );
}
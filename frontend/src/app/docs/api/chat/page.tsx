import { DocsPage } from "@/components/docs/docs-page";
import { ApiEndpoint, CodeBlock, DocsH2, DocsLink, DocsProse, DocsP } from "@/components/docs/docs-ui";

export default function ApiChatPage() {
  return (
    <DocsPage title="Chat API" description="Synchronous chat, SSE streaming, and conversation management.">
      <DocsProse>
        <ApiEndpoint method="POST" path="/api/chat" auth="token" description="Complete a chat turn; returns response, conversation_id, chain_calls, tokens_used.">
          <CodeBlock>{`{
  "agent_id": "uuid",
  "message": "string",
  "conversation_id": "uuid | null",
  "connected_wallet_address": "0x... | null"
}`}</CodeBlock>
        </ApiEndpoint>

        <ApiEndpoint
          method="POST"
          path="/api/chat/stream"
          auth="token"
          description="Same request body as /api/chat. Response is text/event-stream with typed JSON events."
        />

        <DocsH2 id="conversations">Conversations</DocsH2>
        <ApiEndpoint method="GET" path="/api/conversations?agent_id={id}" auth="token" description="List conversation summaries for an agent." />
        <ApiEndpoint method="GET" path="/api/conversations/{id}/messages" auth="token" description="Up to 500 messages with role, content, chain_calls." />
        <ApiEndpoint method="DELETE" path="/api/conversations/{id}" auth="token" description="Delete conversation and messages (204)." />
        <ApiEndpoint
          method="GET"
          path="/api/conversations/{id}/stream"
          auth="token"
          description="SSE stream of transaction confirmations for the conversation. Accepts access_token query param for EventSource clients."
        />

        <DocsP>
          See the <DocsLink href="/docs/guides/chat">Chat guide</DocsLink> for SSE event types and streaming behavior.
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}
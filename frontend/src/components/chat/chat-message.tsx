"use client";

import type { ReactNode } from "react";
import { Bot, User } from "lucide-react";

import { Avatar } from "@/components/ui/avatar";
import type { ChainCall, ChatMessage as APIChatMessage } from "@/lib/api";
import { CHAIN_CONFIGS, chainBadgeSymbol } from "@/lib/constants";
import { cn } from "@/lib/utils";

type ChatMessageProps = {
  message?: APIChatMessage & { id?: string; tokens_used?: number };
  loading?: boolean;
  /** Shown inside an empty assistant bubble while the stream is in flight. */
  streamingHint?: "thinking" | "rpc" | null;
};

const chainNamesFromCalls = (calls: ChainCall[]) => {
  const chains = new Set<string>();
  for (const call of calls) {
    const args = call.args ?? {};
    const chain = call.chain ?? (typeof args.chain === "string" ? args.chain : undefined);
    const chainList = call.chains ?? (Array.isArray(args.chains) ? args.chains : undefined);
    if (chain) chains.add(chain);
    if (chainList) {
      for (const value of chainList) {
        if (typeof value === "string") chains.add(value);
      }
    }
  }
  return Array.from(chains);
};

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*)/g;
  let cursor = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index));
    }
    const token = match[0];
    if (token.startsWith("`")) {
      nodes.push(
        <code key={`${match.index}-code`} className="rounded bg-muted/60 border border-border/30 px-1.5 py-0.5 font-mono text-[0.85em] text-foreground/90">
          {token.slice(1, -1)}
        </code>
      );
    } else {
      nodes.push(
        <strong key={`${match.index}-strong`} className="font-semibold text-foreground">
          {token.slice(2, -2)}
        </strong>
      );
    }
    cursor = match.index + token.length;
  }

  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }
  return nodes;
}

function MarkdownContent({ content }: { content: string }) {
  const blocks = content.split(/\n{2,}/).filter(Boolean);

  return (
    <div className="space-y-4 text-sm leading-relaxed text-foreground/85">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n");
        const isList = lines.every((line) => /^[-*]\s+/.test(line.trim()));
        const isOrderedList = lines.every((line) => /^\d+\.\s+/.test(line.trim()));
        const codeBlock = block.match(/^```(?:\w+)?\n?([\s\S]*?)```$/);
        const heading = block.match(/^(#{1,3})\s+(.+)$/);

        if (codeBlock) {
          return (
            <pre key={blockIndex} className="my-4 overflow-x-auto rounded-xl border border-border/20 bg-muted/30 px-4 py-3.5 font-mono text-xs shadow-sm text-foreground/90 leading-normal">
              <code>{codeBlock[1]}</code>
            </pre>
          );
        }

        if (heading) {
          const HeadingTag = (`h${Math.min(heading[1].length + 2, 5)}`) as "h3" | "h4" | "h5";
          return (
            <HeadingTag key={blockIndex} className="font-bold tracking-tight text-foreground/95 my-5">
              {renderInline(heading[2])}
            </HeadingTag>
          );
        }

        if (isList) {
          return (
            <ul key={blockIndex} className="my-3 list-disc space-y-2 pl-5 text-foreground/85">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex}>{renderInline(line.replace(/^[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }

        if (isOrderedList) {
          return (
            <ol key={blockIndex} className="my-3 list-decimal space-y-2 pl-5 text-foreground/85">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex}>{renderInline(line.replace(/^\d+\.\s+/, ""))}</li>
              ))}
            </ol>
          );
        }

        return (
          <p key={blockIndex} className="whitespace-pre-wrap break-words leading-relaxed text-foreground/85">
            {renderInline(block)}
          </p>
        );
      })}
    </div>
  );
}

function ConfirmationBadge({
  chainCalls,
}: {
  // Reuse the shared ChainCall type (result is `unknown` since tool results
  // vary); we narrow it with a local `as` cast below. The previous inline
  // `{ tool?: string; result?: Record<string, unknown> }` was incompatible
  // with ChainCall.result (`unknown`), causing a tsc error at the call site.
  chainCalls?: ChainCall[];
}) {
  const call = chainCalls?.find((c) => c.tool === "tx_confirmation");
  if (!call || !call.result) return null;
  const result = call.result as {
    status?: string;
    explorer_url?: string;
    tx_hash?: string;
    chain?: string;
  };
  const status = result.status;
  if (!status) return null;
  const palette: Record<string, string> = {
    confirmed: "border-green-500/40 bg-green-500/10 text-green-400",
    reverted: "border-red-500/40 bg-red-500/10 text-red-400",
    pending_timeout: "border-yellow-500/40 bg-yellow-500/10 text-yellow-400",
  };
  const label: Record<string, string> = {
    confirmed: "✅ Confirmed",
    reverted: "❌ Reverted",
    pending_timeout: "⏳ Pending",
  };
  const tone = palette[status] ?? "border-border/40 bg-muted/20 text-muted-foreground/80";
  const text = label[status] ?? status;
  const className = `inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider shadow-sm hover:underline ${tone}`;
  if (result.explorer_url) {
    return (
      <a
        href={result.explorer_url}
        target="_blank"
        rel="noopener noreferrer"
        className={className}
        title={result.tx_hash ?? result.chain ?? ""}
      >
        {text} ↗
      </a>
    );
  }
  return (
    <span
      className={className.replace("hover:underline", "")}
      title={result.tx_hash ?? result.chain ?? ""}
    >
      {text}
    </span>
  );
}

function StreamingHint({ hint }: { hint: "thinking" | "rpc" }) {
  const label = hint === "rpc" ? "Querying Pocket RPC…" : "Thinking…";
  return (
    <div className="flex items-center gap-2 pl-1 text-sm text-muted-foreground" aria-label={label}>
      <div className="flex h-5 items-center gap-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-pulse-soft" />
        <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-pulse-soft [animation-delay:200ms]" />
        <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-pulse-soft [animation-delay:400ms]" />
      </div>
      <span className="font-mono text-[11px]">{label}</span>
    </div>
  );
}

export function ChatMessage({
  message,
  loading = false,
  streamingHint = null,
}: ChatMessageProps) {
  const isUser = message?.role === "user";
  const chains = message ? chainNamesFromCalls(message.chain_calls) : [];

  return (
    <article className={cn("flex gap-4 chat-message-enter py-1", isUser && "flex-row-reverse")}>
      <Avatar
        className={cn(
          "rounded-xl border shadow-md h-8 w-8 flex items-center justify-center transition-all duration-300",
          isUser
            ? "bg-gradient-to-br from-primary/80 to-primary text-white border-transparent"
            : "bg-muted/60 text-primary border-border/30"
        )}
      >
        {isUser ? <User size={14} /> : <Bot size={14} className="animate-pulse-soft" />}
      </Avatar>

      <div className={cn("max-w-[min(46rem,85%)] flex flex-col space-y-1.5", isUser && "items-end")}>
        <div
          className={cn(
            "px-4 py-3 transition-all duration-300",
            isUser
              ? "rounded-2xl rounded-tr-sm border border-primary/20 bg-primary/5 text-foreground shadow-sm shadow-primary/5"
              : "border-transparent bg-transparent text-foreground shadow-none px-0 py-1"
          )}
        >
          {loading ? (
            <StreamingHint hint="thinking" />
          ) : message?.role === "assistant" ? (
            message.content ? (
              <MarkdownContent content={message.content} />
            ) : streamingHint ? (
              <StreamingHint hint={streamingHint} />
            ) : (
              <StreamingHint hint="thinking" />
            )
          ) : (
            <p className="whitespace-pre-wrap break-words text-sm leading-relaxed text-foreground/95">
              {message?.content}
            </p>
          )}
        </div>

        {!isUser && !loading && message && (
          <div className="flex flex-wrap items-center gap-2 pl-0.5 text-[10px] text-muted-foreground/60 transition-opacity">
            {chains.map((chain) => {
              const config = CHAIN_CONFIGS[chain as keyof typeof CHAIN_CONFIGS];
              return (
                <span
                  key={chain}
                  className="inline-flex items-center rounded border border-border/40 bg-muted/20 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-muted-foreground/80 shadow-sm"
                  title={config?.name ?? chain}
                >
                  {chainBadgeSymbol(chain)}
                  <span className="ml-1 shrink-0 rounded bg-green-500/10 px-1 py-0 text-[7px] font-semibold tracking-widest text-green-500/80">
                    MAINNET
                  </span>
                </span>
              );
            })}
            {message.tokens_used ? (
              <span className="font-mono text-[9px] text-muted-foreground/50">
                {message.tokens_used.toLocaleString()} tokens
              </span>
            ) : null}
            <ConfirmationBadge chainCalls={message.chain_calls} />
          </div>
        )}
      </div>
    </article>
  );
}

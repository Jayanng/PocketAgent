"use client";

import type { ReactNode } from "react";
import { Bot, User } from "lucide-react";

import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import type { ChainCall, ChatMessage as APIChatMessage } from "@/lib/api";
import { CHAIN_CONFIGS } from "@/lib/constants";
import { cn } from "@/lib/utils";

type ChatMessageProps = {
  message?: APIChatMessage & { id?: string; tokens_used?: number };
  loading?: boolean;
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
        <code key={`${match.index}-code`} className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]">
          {token.slice(1, -1)}
        </code>
      );
    } else {
      nodes.push(
        <strong key={`${match.index}-strong`} className="font-semibold">
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
    <div className="space-y-3 text-sm leading-6">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n");
        const isList = lines.every((line) => /^[-*]\s+/.test(line.trim()));
        const isOrderedList = lines.every((line) => /^\d+\.\s+/.test(line.trim()));
        const codeBlock = block.match(/^```(?:\w+)?\n?([\s\S]*?)```$/);
        const heading = block.match(/^(#{1,3})\s+(.+)$/);

        if (codeBlock) {
          return (
            <pre key={blockIndex} className="overflow-x-auto rounded-md bg-background px-3 py-2 font-mono text-xs">
              <code>{codeBlock[1]}</code>
            </pre>
          );
        }

        if (heading) {
          const HeadingTag = (`h${Math.min(heading[1].length + 2, 5)}`) as "h3" | "h4" | "h5";
          return (
            <HeadingTag key={blockIndex} className="font-semibold">
              {renderInline(heading[2])}
            </HeadingTag>
          );
        }

        if (isList) {
          return (
            <ul key={blockIndex} className="list-disc space-y-1 pl-5">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex}>{renderInline(line.replace(/^[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }

        if (isOrderedList) {
          return (
            <ol key={blockIndex} className="list-decimal space-y-1 pl-5">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex}>{renderInline(line.replace(/^\d+\.\s+/, ""))}</li>
              ))}
            </ol>
          );
        }

        return (
          <p key={blockIndex} className="whitespace-pre-wrap break-words">
            {renderInline(block)}
          </p>
        );
      })}
    </div>
  );
}

export function ChatMessage({ message, loading = false }: ChatMessageProps) {
  const isUser = message?.role === "user";
  const chains = message ? chainNamesFromCalls(message.chain_calls) : [];

  return (
    <article className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <Avatar className={cn(isUser ? "bg-primary text-primary-foreground" : "bg-muted")}>
        {isUser ? <User size={15} /> : <Bot size={15} />}
      </Avatar>
      <div className={cn("max-w-[min(42rem,85%)] space-y-2", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-lg border px-4 py-3",
            isUser
              ? "border-primary bg-primary text-primary-foreground"
              : "border-border bg-muted text-foreground"
          )}
        >
          {loading ? (
            <div className="flex h-6 items-center gap-1.5" aria-label="Waiting for assistant response">
              <span className="h-2 w-2 rounded-full bg-muted-foreground motion-safe:animate-bounce" />
              <span className="h-2 w-2 rounded-full bg-muted-foreground motion-safe:animate-bounce [animation-delay:120ms]" />
              <span className="h-2 w-2 rounded-full bg-muted-foreground motion-safe:animate-bounce [animation-delay:240ms]" />
            </div>
          ) : message?.role === "assistant" ? (
            <MarkdownContent content={message.content} />
          ) : (
            <p className="whitespace-pre-wrap break-words text-sm leading-6">{message?.content}</p>
          )}
        </div>
        {!isUser && !loading && message && (
          <div className="flex flex-wrap items-center gap-2 pl-1 text-xs text-muted-foreground">
            {chains.map((chain) => {
              const config = CHAIN_CONFIGS[chain as keyof typeof CHAIN_CONFIGS];
              return <Badge key={chain}>{config?.name ?? chain}</Badge>;
            })}
            {message.tokens_used ? <span>{message.tokens_used.toLocaleString()} tokens</span> : null}
          </div>
        )}
      </div>
    </article>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bot, Fuel, Sparkles, User, Wrench } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/utils";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

type VisibleMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "tool"; label: string; chain: string }
  | { id: string; role: "assistant"; text: string };

type ScriptBeat =
  | { kind: "user"; text: string; pauseMs: number }
  | { kind: "tool"; label: string; chain: string; pauseMs: number }
  | { kind: "assistant"; text: string; pauseMs: number }
  | { kind: "hold"; pauseMs: number };

const DEMO_SCRIPT: ScriptBeat[] = [
  {
    kind: "user",
    text: "What's the gas on Ethereum right now?",
    pauseMs: 1400,
  },
  {
    kind: "tool",
    label: "evm_get_gas",
    chain: "ethereum",
    pauseMs: 1600,
  },
  {
    kind: "assistant",
    text: "Ethereum base fee is **12.4 gwei** (~$0.42 transfer). Priority fee is low — good window to route via Pocket RPC.",
    pauseMs: 3200,
  },
  {
    kind: "user",
    text: "Compare fees on Arbitrum and Polygon for a 0.1 ETH transfer.",
    pauseMs: 1400,
  },
  {
    kind: "tool",
    label: "compare_gas",
    chain: "multi",
    pauseMs: 1800,
  },
  {
    kind: "assistant",
    text: "Polygon is cheapest at **$0.003**. Arbitrum: **$0.018**. Ethereum mainnet would cost **~$1.90** for the same transfer.",
    pauseMs: 3600,
  },
  {
    kind: "user",
    text: "Check SOL balance for 7xKXtg2CW87d97TXJSDpbD5yLcB5nHHZv4.",
    pauseMs: 1400,
  },
  {
    kind: "tool",
    label: "solana_get_balance",
    chain: "solana",
    pauseMs: 1600,
  },
  {
    kind: "assistant",
    text: "Wallet holds **14.82 SOL** (~$2,964). Last activity 2h ago via Solana mainnet-beta.",
    pauseMs: 3200,
  },
  { kind: "hold", pauseMs: 2200 },
];

function buildStaticMessages(): VisibleMessage[] {
  const staticMessages: VisibleMessage[] = [];
  for (const beat of DEMO_SCRIPT) {
    if (beat.kind === "user") {
      staticMessages.push({
        id: `user-${staticMessages.length}`,
        role: "user",
        text: beat.text,
      });
    } else if (beat.kind === "tool") {
      staticMessages.push({
        id: `tool-${staticMessages.length}`,
        role: "tool",
        label: beat.label,
        chain: beat.chain,
      });
    } else if (beat.kind === "assistant") {
      staticMessages.push({
        id: `assistant-${staticMessages.length}`,
        role: "assistant",
        text: beat.text,
      });
    }
  }
  return staticMessages.slice(0, 5);
}

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold text-[var(--lp-text)]">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={index}>{part}</span>;
  });
}

function TypingIndicator() {
  return (
    <div className="landing-demo-typing flex items-center gap-1 px-1 py-0.5">
      {[0, 1, 2].map((dot) => (
        <motion.span
          key={dot}
          className="landing-demo-typing-dot h-1.5 w-1.5 rounded-full"
          animate={{ opacity: [0.35, 1, 0.35], y: [0, -2, 0] }}
          transition={{
            duration: 0.9,
            repeat: Infinity,
            delay: dot * 0.15,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

export function HeroDemoChat() {
  const reduceMotion = useReducedMotion();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [animationReady, setAnimationReady] = useState(false);
  const [messages, setMessages] = useState<VisibleMessage[]>([]);
  const [thinking, setThinking] = useState(false);
  const [relayCount, setRelayCount] = useState(0);
  const [cycle, setCycle] = useState(0);

  const staticMessages = useMemo(() => buildStaticMessages(), []);
  const displayMessages = reduceMotion ? staticMessages : messages;
  const displayRelayCount = reduceMotion ? 3 : relayCount;
  const displayThinking = reduceMotion ? false : thinking;

  useEffect(() => {
    const start = () => setAnimationReady(true);
    if (typeof window.requestIdleCallback === "function") {
      const id = window.requestIdleCallback(start, { timeout: 1200 });
      return () => window.cancelIdleCallback(id);
    }
    const id = window.setTimeout(start, 400);
    return () => window.clearTimeout(id);
  }, []);

  const scrollToBottom = useCallback(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: reduceMotion ? "auto" : "smooth" });
  }, [reduceMotion]);

  useEffect(() => {
    scrollToBottom();
  }, [displayMessages, displayThinking, scrollToBottom]);

  useEffect(() => {
    if (!animationReady || reduceMotion) return;

    let cancelled = false;
    let stepIndex = 0;
    let messageCounter = 0;

    const run = async () => {
      setMessages([]);
      setRelayCount(0);
      setThinking(false);
      stepIndex = 0;

      while (!cancelled && stepIndex < DEMO_SCRIPT.length) {
        const beat = DEMO_SCRIPT[stepIndex];
        stepIndex += 1;

        if (beat.kind === "hold") {
          await new Promise((resolve) => window.setTimeout(resolve, beat.pauseMs));
          continue;
        }

        if (beat.kind === "user") {
          const id = `m-${cycle}-${messageCounter++}`;
          setMessages((prev) => [...prev, { id, role: "user", text: beat.text }]);
          await new Promise((resolve) => window.setTimeout(resolve, beat.pauseMs));
          continue;
        }

        setThinking(true);
        await new Promise((resolve) => window.setTimeout(resolve, 520));

        if (beat.kind === "tool") {
          const id = `m-${cycle}-${messageCounter++}`;
          setMessages((prev) => [
            ...prev,
            { id, role: "tool", label: beat.label, chain: beat.chain },
          ]);
          setRelayCount((count) => Math.min(count + 1, 999));
          setThinking(false);
          await new Promise((resolve) => window.setTimeout(resolve, beat.pauseMs));
          continue;
        }

        if (beat.kind === "assistant") {
          const id = `m-${cycle}-${messageCounter++}`;
          setMessages((prev) => [
            ...prev,
            { id, role: "assistant", text: beat.text },
          ]);
          setThinking(false);
          await new Promise((resolve) => window.setTimeout(resolve, beat.pauseMs));
        }
      }

      if (!cancelled) {
        setCycle((value) => value + 1);
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [animationReady, cycle, reduceMotion]);

  return (
    <motion.div
      className="landing-demo-chat relative"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.25, ease: EASE_OUT }}
    >
      <div className="landing-demo-chat-glow pointer-events-none absolute -inset-4 rounded-[1.75rem] opacity-80" />

      <div className="landing-demo-chat-shell relative overflow-hidden rounded-2xl border shadow-xl">
        <div className="landing-demo-chat-header flex items-center justify-between border-b px-4">
          <div className="flex items-center gap-2">
            <span className="landing-dot relative flex h-2 w-2 rounded-full">
              <span className="landing-dot absolute inline-flex h-full w-full animate-ping rounded-full opacity-60" />
            </span>
            <span className="text-[10px] font-mono font-semibold uppercase tracking-[0.14em] text-[var(--lp-text-muted)]">
              Live Demo
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-[var(--lp-text-faint)]">
            <Fuel size={12} className="text-[var(--lp-blue)]" />
            <span>{displayRelayCount}</span>
            <span className="opacity-60">/ 1000 relays</span>
          </div>
        </div>

        <div
          ref={scrollRef}
          className="landing-demo-chat-body space-y-3 px-4 py-4"
        >
          <AnimatePresence initial={false}>
            {displayMessages.map((message) => (
              <motion.div
                key={message.id}
                initial={reduceMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: EASE_OUT }}
                className={cn(
                  "landing-demo-chat-row flex gap-2.5",
                  message.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                {message.role !== "user" && (
                  <div className="landing-demo-chat-avatar mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg">
                    {message.role === "tool" ? (
                      <Wrench size={13} />
                    ) : (
                      <Bot size={13} />
                    )}
                  </div>
                )}

                <div
                  className={cn(
                    "landing-demo-chat-bubble rounded-xl px-3 py-2 text-[13px] leading-relaxed",
                    message.role === "user" && "landing-demo-chat-bubble-user",
                    message.role === "assistant" && "landing-demo-chat-bubble-assistant",
                    message.role === "tool" && "landing-demo-chat-bubble-tool font-mono text-[11px]",
                  )}
                >
                  {message.role === "user" && (
                    <div className="flex min-w-0 items-start gap-2">
                      <p className="min-w-0 break-words">{message.text}</p>
                      <User size={13} className="mt-0.5 shrink-0 opacity-70" />
                    </div>
                  )}
                  {message.role === "assistant" && (
                    <p className="text-[var(--lp-text-muted)]">
                      {renderInline(message.text)}
                    </p>
                  )}
                  {message.role === "tool" && (
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[var(--lp-blue)]">{message.label}</span>
                      <span className="landing-demo-chat-chain rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide">
                        {message.chain}
                      </span>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {displayThinking && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="landing-demo-chat-row flex items-center gap-2.5"
            >
              <div className="landing-demo-chat-avatar flex h-7 w-7 items-center justify-center rounded-lg">
                <Sparkles size={13} />
              </div>
              <div className="landing-demo-chat-bubble-assistant rounded-xl px-3 py-2">
                <TypingIndicator />
              </div>
            </motion.div>
          )}
        </div>

        <div className="landing-demo-chat-footer border-t px-4">
          <p className="text-[10px] font-mono uppercase tracking-[0.16em] text-[var(--lp-text-faint)]">
            Autonomous agent demo — no input required
          </p>
        </div>
      </div>
    </motion.div>
  );
}
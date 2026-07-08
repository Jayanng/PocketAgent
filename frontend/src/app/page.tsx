"use client";

import { useRef, useMemo, useEffect } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useAccount } from "wagmi";
import {
  motion,
  useInView,
  useMotionValue,
  useTransform,
  animate,
  useReducedMotion,
} from "motion/react";
import {
  PlugZap,
  ShieldCheck,
  Globe,
  ArrowRight,
  Wallet,
  MessageSquare,
  Send,
  BarChart3,
  Terminal,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { ProtocolFamiliesBanner } from "@/components/brand/protocol-families-banner";
import { SiteHeader } from "@/components/layout/site-header";
import { useLandingTheme } from "@/hooks/use-landing-theme";
import { TEST_STATS } from "@/lib/test-stats";
import { cn } from "@/lib/utils";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

function HeroDemoChatPlaceholder() {
  return (
    <div className="landing-demo-chat relative" aria-hidden="true">
      <div className="landing-demo-chat-glow pointer-events-none absolute -inset-4 rounded-[1.75rem] opacity-80" />
      <div className="landing-demo-chat-shell relative overflow-hidden rounded-2xl border shadow-xl">
        <div className="landing-demo-chat-header border-b" />
        <div className="landing-demo-chat-body" />
        <div className="landing-demo-chat-footer border-t" />
      </div>
    </div>
  );
}

const HeroDemoChat = dynamic(
  () =>
    import("@/components/brand/hero-demo-chat").then((mod) => mod.HeroDemoChat),
  { ssr: false, loading: () => <HeroDemoChatPlaceholder /> },
);

function GitHubIcon({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

const STATS = [
  { value: "52", label: "Chains Supported", suffix: "" },
  { value: "6", label: "Protocol Families", suffix: "" },
  { value: "51", label: "MCP Tools", suffix: "" },
  { value: String(TEST_STATS.total), label: "Automated Tests", suffix: "" },
];

const FEATURES = [
  {
    title: "Decentralized by Design",
    description:
      "No centralized RPC provider. Every call routes through Pocket Network's decentralized node infrastructure. Censorship resistant by default.",
    icon: ShieldCheck,
    gradient: "var(--gradient-blue-soft)",
  },
  {
    title: "52-Chain Network",
    description:
      "EVM, Solana, Sui, Near, Tron, Cosmos — one unified interface across every major protocol family. Live RPC endpoints for all supported chains.",
    icon: Globe,
    gradient: "var(--gradient-blue-deep)",
  },
];

function CountUp({
  value,
  suffix,
  label,
}: {
  value: string;
  suffix: string;
  label: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const numeric = parseInt(value.replace(/[+\-]/, ""), 10);
  const count = useMotionValue(0);
  const rounded = useTransform(count, (v) => Math.round(v));

  useEffect(() => {
    if (inView && !isNaN(numeric)) {
      animate(count, numeric, { duration: 2, ease: EASE_OUT });
    }
  }, [inView, count, numeric]);

  const displayValue = isNaN(numeric) ? value : null;

  return (
    <div ref={ref} className="text-center">
      <p className="landing-stat-value text-3xl font-bold tracking-tight md:text-4xl">
        {displayValue ?? (
          <>
            <motion.span>{rounded}</motion.span>
            {suffix}
          </>
        )}
        {displayValue && (
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            animate={inView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.6, ease: EASE_OUT }}
          >
            {value}
          </motion.span>
        )}
      </p>
      <p className="landing-stat-label mt-1.5 text-xs font-semibold uppercase tracking-wide">
        {label}
      </p>
    </div>
  );
}

function GradientBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 landing-grid-pattern opacity-40" />
      <div className="landing-orb-blue absolute -left-40 -top-40 h-[500px] w-[500px] rounded-full blur-[120px]" />
      <div className="landing-orb-accent absolute -right-40 bottom-0 h-[400px] w-[400px] rounded-full blur-[100px]" />
      <div className="landing-orb-blue absolute left-1/2 top-1/3 h-[300px] w-[300px] -translate-x-1/2 rounded-full blur-[80px]" />
    </div>
  );
}

function FeatureCardVisual({
  gradient,
  compact = false,
}: {
  gradient: string;
  compact?: boolean;
}) {
  return (
    <div className={cn("landing-card-visual", compact && "landing-card-visual-sm")}>
      <div className="landing-card-visual-glow" style={{ background: gradient }} />
      <div className="landing-card-visual-grid" />
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const { isConnected } = useAccount();
  const reduce = useReducedMotion();
  const { theme } = useLandingTheme();
  const featuresRef = useRef<HTMLElement>(null);
  const featuresInView = useInView(featuresRef, { once: true, margin: "-60px" });
  const statsRef = useRef<HTMLElement>(null);
  const statsInView = useInView(statsRef, { once: true, margin: "-80px" });

  useEffect(() => {
    if (isConnected) {
      router.replace("/dashboard");
    }
  }, [isConnected, router]);

  const containerVariants = useMemo(
    () => ({
      hidden: {},
      visible: { transition: { staggerChildren: 0.1 } },
    }),
    [],
  );

  const itemVariants = useMemo(
    () => ({
      hidden: { opacity: 0, y: 24 },
      visible: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.6, ease: EASE_OUT },
      },
    }),
    [],
  );

  if (isConnected) {
    return (
      <div
        className="landing-page flex min-h-[100dvh] items-center justify-center"
        data-landing-theme={theme}
      >
        <div className="landing-spinner h-8 w-8 animate-spin rounded-full border-2" />
      </div>
    );
  }

  return (
    <div
      className="landing-page relative isolate min-h-[100dvh] overflow-x-clip"
      data-landing-theme={theme}
    >
      <div className="pointer-events-none absolute inset-0 -z-10">
        <GradientBackground />
      </div>
      <SiteHeader />

      <section className="relative z-10 mx-auto flex min-h-[calc(100dvh-3.5rem)] max-w-7xl flex-col px-4 py-8 sm:px-6 md:min-h-[calc(100dvh-4rem)] md:flex-row md:items-center md:px-6 md:py-12">
        <motion.div
          className="flex-1 md:pr-12 lg:pr-16"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.h1
            variants={itemVariants}
            className="landing-heading text-[clamp(2.5rem,6vw,4.5rem)] font-bold leading-[1.02] tracking-tight"
          >
            <span className="mb-1 block">AI Agents for the</span>
            <span className="gradient-text">Multi-Chain</span>
            <br />
            <span className="landing-heading-line">World</span>
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="landing-body mt-6 max-w-lg text-[15px] leading-relaxed md:text-base"
          >
            Deploy autonomous agents that read and compare 52 blockchains
            through a single decentralized interface, with guarded native
            transaction signing across EVM, Solana, SUI, NEAR, Cosmos, and
            TRON. No gatekeepers. No central RPC provider.
          </motion.p>

          <motion.div
            variants={itemVariants}
            className="landing-btn-row mt-8 flex flex-col items-start gap-3 sm:mt-10 sm:flex-row sm:items-center sm:gap-3"
          >
            <Link href="/agents" className="landing-btn">
              Get Started
              <ArrowRight size={16} />
            </Link>
            <a
              href="https://github.com/Jayanng/PocketAgent"
              target="_blank"
              rel="noopener noreferrer"
              className="landing-btn landing-btn-secondary"
            >
              <GitHubIcon size={16} />
              Star on GitHub
            </a>
          </motion.div>
        </motion.div>

        <motion.div
          className="mt-8 shrink-0 md:mt-0 md:ml-auto"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.2, delay: 0.3, ease: EASE_OUT }}
        >
          <HeroDemoChat />
        </motion.div>
      </section>

      <section
        ref={featuresRef}
        className="relative z-10 mx-auto max-w-7xl px-4 pb-20 pt-12 sm:px-6 sm:pb-32 sm:pt-16 md:pt-24"
      >
        <div className="grid gap-5 md:grid-cols-2">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            const delay = i * 0.12;

            return (
              <motion.div
                key={feature.title}
                className="landing-card group relative overflow-hidden rounded-2xl"
                initial={reduce ? false : { opacity: 0, y: 30 }}
                animate={featuresInView ? { opacity: 1, y: 0 } : { opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay, ease: EASE_OUT }}
                whileHover={
                  reduce ? undefined : { y: -2, transition: { duration: 0.2 } }
                }
              >
                <div
                  className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-[0.04]"
                  style={{ background: feature.gradient }}
                />

                <div className="relative flex flex-col p-7 md:p-8">
                  <div className="mb-5 flex items-center gap-4">
                    <div
                      className="inline-flex rounded-xl p-2.5"
                      style={{ background: feature.gradient }}
                    >
                      <Icon size={20} className="text-white" />
                    </div>
                    <h3 className="landing-card-title text-[17px] font-semibold tracking-tight">
                      {feature.title}
                    </h3>
                  </div>

                  <p className="landing-card-desc max-w-md text-sm leading-relaxed">
                    {feature.description}
                  </p>

                  {feature.title === "52-Chain Network" ? (
                    <ProtocolFamiliesBanner />
                  ) : (
                    <FeatureCardVisual gradient={feature.gradient} compact />
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>

      <section ref={statsRef} className="relative z-10 mx-auto max-w-7xl px-4 pb-20 sm:px-6 sm:pb-32">
        <div className="landing-stats-panel rounded-2xl p-5 sm:p-8 md:p-12">
          <div className="grid grid-cols-2 gap-6 sm:gap-10 md:grid-cols-4 md:gap-8">
            {STATS.map((stat) => (
              <CountUp
                key={stat.label}
                value={stat.value}
                suffix={stat.suffix}
                label={stat.label}
              />
            ))}
          </div>

          <motion.div
            className="landing-stats-footer mt-10 border-t pt-6 text-center"
            initial={{ opacity: 0 }}
            animate={statsInView ? { opacity: 1 } : { opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.6 }}
          >
            <p className="text-xs">
              Real-time relay metrics and chain health across every supported network.
              No third-party indexers required.
            </p>
          </motion.div>
        </div>
      </section>

      {/* ─── How It Works ─────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-4 pb-20 sm:px-6 sm:pb-32">
        <motion.div
          className="mx-auto mb-16 max-w-2xl text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <h2 className="landing-section-title text-3xl font-bold tracking-tight md:text-4xl">
            From <span className="landing-section-accent">zero</span> to on-chain in minutes
          </h2>
          <p className="landing-section-desc mt-4 text-[15px]">
            Create an agent, fund its wallet, then talk to it — the agent handles
            chain selection, tool execution, and safety checks automatically.
          </p>
        </motion.div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
          {[
            {
              step: "01",
              icon: Wallet,
              title: "Create Agent",
              desc: "Name it, pick capabilities, set spending caps. Encrypted multi-chain keys are generated automatically.",
            },
            {
              step: "02",
              icon: Send,
              title: "Fund Wallet",
              desc: "Deposit ETH, SOL, USDC, or any supported token. Live balances appear in the dashboard.",
            },
            {
              step: "03",
              icon: MessageSquare,
              title: "Chat",
              desc: "Ask anything naturally. The LLM picks the right tools from 51 options across 52 chains.",
            },
            {
              step: "04",
              icon: ShieldCheck,
              title: "Execute Safely",
              desc: "Spending caps and balance checks gate every transaction. Real-time SSE confirms on-chain.",
            },
            {
              step: "05",
              icon: BarChart3,
              title: "Monitor",
              desc: "Track relay volume, chain health, latency, and costs across all agents in one dashboard.",
            },
          ].map((item, i) => (
            <motion.div
              key={item.step}
              className="landing-card group relative overflow-hidden rounded-2xl p-6 sm:col-span-2 lg:col-span-1"
              initial={reduce ? false : { opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.5, delay: i * 0.1, ease: EASE_OUT }}
            >
              <span className="landing-stat-label mb-4 block text-[11px] font-semibold uppercase tracking-widest">
                Step {item.step}
              </span>
              <div
                className="mb-4 inline-flex rounded-lg p-2"
                style={{ background: "var(--gradient-blue)" }}
              >
                <item.icon size={18} className="text-white" />
              </div>
              <h3 className="landing-card-title mb-2 text-[15px] font-semibold">
                {item.title}
              </h3>
              <p className="landing-card-desc text-[13px] leading-relaxed">
                {item.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ─── Developer Section ────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-4 pb-20 sm:px-6 sm:pb-32">
        <motion.div
          className="mx-auto mb-16 max-w-2xl text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <h2 className="landing-section-title text-3xl font-bold tracking-tight md:text-4xl">
            Built <span className="landing-section-accent">also</span> for developers
          </h2>
          <p className="landing-section-desc mt-4 text-[15px]">
            Integrate PocketAgent into any workflow — REST API, MCP server, or
            chat UI. One-command install, zero configuration.
          </p>
        </motion.div>

        <div className="grid gap-6 lg:grid-cols-2">
          <motion.div
            className="landing-card overflow-hidden rounded-2xl p-6 sm:p-8"
            initial={reduce ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.5, ease: EASE_OUT }}
          >
            <div className="mb-5 inline-flex rounded-xl p-2.5" style={{ background: "var(--gradient-blue)" }}>
              <Terminal size={20} className="text-white" />
            </div>
            <h3 className="landing-card-title mb-3 text-[17px] font-semibold">pip install pokt-agent-mcp</h3>
            <p className="landing-card-desc mb-5 text-[13px] leading-relaxed">
              One command gives you the full PocketAgent MCP server — 51 blockchain
              tools, 5 resources, 4 prompts. Drop it into Claude Desktop, Cursor, or Codex.
            </p>
            <div className="inline-flex items-center gap-2 rounded-full border px-4 py-2 font-mono text-[13px]">
              <span className="text-emerald-400">$</span>
              <span>pip install pokt-agent-mcp</span>
            </div>
          </motion.div>

          <motion.div
            className="landing-card overflow-hidden rounded-2xl p-6 sm:p-8"
            initial={reduce ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.5, delay: 0.1, ease: EASE_OUT }}
          >
            <div className="mb-5 inline-flex rounded-xl p-2.5" style={{ background: "var(--gradient-blue-deep)" }}>
              <PlugZap size={20} className="text-white" />
            </div>
            <h3 className="landing-card-title mb-3 text-[17px] font-semibold">Interactive API docs</h3>
            <p className="landing-card-desc mb-5 text-[13px] leading-relaxed">
              Full OpenAPI spec with Swagger UI and ReDoc. Every agent CRUD endpoint,
              SSE chat stream, and analytics route auto-documented at <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">/docs</code>.
            </p>
            <div className="flex flex-wrap gap-3">
              {[
                { label: "Create agent", method: "POST" },
                { label: "Chat (SSE)", method: "POST" },
                { label: "Balances", method: "GET" },
                { label: "Analytics", method: "GET" },
              ].map((ep) => (
                <span
                  key={ep.label}
                  className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium"
                >
                  <span className="text-emerald-400">{ep.method}</span>
                  <span className="opacity-60">{ep.label}</span>
                </span>
              ))}
            </div>
          </motion.div>
        </div>

        <motion.div
          className="mt-6 grid gap-6 sm:grid-cols-2"
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.5, delay: 0.2, ease: EASE_OUT }}
        >
          <div className="landing-card rounded-2xl p-6 sm:p-8">
            <h3 className="landing-card-title mb-2 text-[15px] font-semibold">Simulate before you send</h3>
            <p className="landing-card-desc text-[13px] leading-relaxed">
              Dry-run any transaction across all 6 protocol families before committing.
              See expected gas, effects, and outcomes — without spending a cent.
            </p>
          </div>
          <div className="landing-card rounded-2xl p-6 sm:p-8">
            <h3 className="landing-card-title mb-2 text-[15px] font-semibold">Real-time confirmation streaming</h3>
            <p className="landing-card-desc text-[13px] leading-relaxed">
              SSE-powered pub/sub fans out transaction status — confirmed, reverted,
              or timed out — directly to the chat UI as it happens on-chain.
            </p>
          </div>
        </motion.div>
      </section>

      {/* ─── CTA ──────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-4 pb-20 sm:px-6 sm:pb-32">
        <motion.div
          className="landing-stats-panel rounded-2xl p-8 text-center sm:p-12 md:p-16"
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <div className="mx-auto mb-6 inline-flex rounded-xl p-2.5" style={{ background: "var(--gradient-blue)" }}>
            <Sparkles size={22} className="text-white" />
          </div>
          <h2 className="landing-section-title mb-4 text-2xl font-bold tracking-tight sm:text-3xl md:text-4xl">
            Start building with <span className="landing-section-accent">Pocket Network</span>
          </h2>
          <p className="landing-section-desc mx-auto mb-8 max-w-lg text-[15px]">
            Open source. Decentralized RPC. 52 chains. One agent. No API keys required.
          </p>
          <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/agents" className="landing-btn">
              Create Your First Agent
              <ArrowRight size={16} />
            </Link>
            <a
              href="https://github.com/Jayanng/PocketAgent"
              target="_blank"
              rel="noopener noreferrer"
              className="landing-btn landing-btn-secondary"
            >
              <GitHubIcon size={16} />
              Star on GitHub
            </a>
          </div>

          <div className="mt-10 border-t pt-6">
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-center text-xs">
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={13} className="text-emerald-400" />
                {TEST_STATS.total} automated tests
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={13} className="text-emerald-400" />
                52 chains · 6 protocols
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={13} className="text-emerald-400" />
                51 MCP tools
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={13} className="text-emerald-400" />
                MIT licensed
              </span>
            </div>
          </div>
        </motion.div>
      </section>

      <footer className="landing-footer safe-bottom relative z-10 border-t px-4 py-6 sm:px-6 sm:py-8">
        <div className="mx-auto flex max-w-7xl items-center justify-center text-center">
          <p className="landing-footer-powered text-[11px]">
            Powered by <span className="landing-brand-accent">Pocket Network</span>
          </p>
        </div>
      </footer>
    </div>
  );
}
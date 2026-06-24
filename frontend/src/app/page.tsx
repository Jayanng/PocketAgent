"use client";

import { useRef, useMemo, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  motion,
  useInView,
  useMotionValue,
  useTransform,
  animate,
  useReducedMotion,
} from "motion/react";
import {
  Layers,
  PlugZap,
  ShieldCheck,
  Globe,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { ConnectButton } from "@/components/wallet/connect-button";

/* ── Design Read ──────────────────────────────────────────────────────
 * B2B web3/developer landing for multi-chain AI agent platform.
 * Audience: technical blockchain developers, crypto-native users.
 * Language: dark-tech / premium crypto - Phantom Wallet, Jito Labs tier.
 * Dials: VARIANCE 7 | MOTION 6 | DENSITY 4
 */

/* ── Motion tokens (const assertion for type safety) ─────────────────── */
const EASE_OUT = [0.16, 1, 0.3, 1] as const;

/* ── Constants ──────────────────────────────────────────────────────── */

const CHAINS = [
  { ticker: "ETH", color: "#627EEA", x: 50, y: 15 },
  { ticker: "SOL", color: "#9945FF", x: 82, y: 28 },
  { ticker: "MATIC", color: "#8247E5", x: 18, y: 42 },
  { ticker: "ATOM", color: "#2E3148", x: 72, y: 62 },
  { ticker: "AVAX", color: "#E84142", x: 30, y: 72 },
  { ticker: "NEAR", color: "#1C1C1C", x: 60, y: 82 },
  { ticker: "BNB", color: "#F0B90B", x: 42, y: 35 },
  { ticker: "BASE", color: "#0052FF", x: 88, y: 50 },
];

const EDGES: Array<[number, number]> = [
  [0, 2], [0, 3], [0, 7], [1, 5], [1, 7],
  [2, 4], [2, 6], [3, 5], [4, 6], [6, 7],
];

const STATS = [
  { value: "52", label: "Chains Supported", suffix: "" },
  { value: "6", label: "Protocol Families", suffix: "" },
  { value: "49", label: "MCP Tools", suffix: "" },
  { value: "100", label: "Uptime", suffix: "%" },
];

const FEATURES = [
  {
    title: "Multi-Chain Intelligence",
    description:
      "Deploy agents that read and compare 52 blockchains through a single Pocket Network RPC interface, with guarded native transaction signing on EVM, Solana, and Tron.",
    icon: Layers,
    span: "large" as const,
    gradient: "var(--gradient-blue)",
    imageSeed: "blockchain-network-nodes",
  },
  {
    title: "MCP Protocol",
    description:
      "Native Model Context Protocol support. Any MCP-compatible client - Claude Desktop, Codex, Cursor - can drive your agents natively.",
    icon: PlugZap,
    span: "small" as const,
    gradient: "var(--gradient-orange)",
    imageSeed: "protocol-layers-abstract",
  },
  {
    title: "Decentralized by Design",
    description:
      "No centralized RPC provider. Every call routes through Pocket Network's decentralized node infrastructure. Censorship resistant by default.",
    icon: ShieldCheck,
    span: "small" as const,
    gradient: "var(--gradient-brand)",
    imageSeed: "distributed-network-dots",
  },
  {
    title: "52-Chain Network",
    description:
      "EVM, Solana, Sui, Near, Tron, Cosmos — one unified interface across every major protocol family. Live RPC endpoints for all supported chains.",
    icon: Globe,
    span: "large" as const,
    gradient: "var(--gradient-blue)",
    imageSeed: "chain-links-connected",
  },
];

/* ── Sub-Components ─────────────────────────────────────────────────── */

function ChainNetwork() {
  const reduce = useReducedMotion();

  return (
    <div className="relative flex h-full w-full items-center justify-center">
      <div className="absolute h-80 w-80 rounded-full bg-blue-500/10 blur-[100px]" />
      <div className="absolute h-60 w-60 translate-x-32 translate-y-16 rounded-full bg-orange-500/8 blur-[80px]" />

      <svg
        viewBox="0 0 100 100"
        className="h-full w-full drop-shadow-lg"
        style={{ filter: "drop-shadow(0 0 12px rgba(30,136,229,0.08))" }}
      >
        {EDGES.map(([i, j], idx) => {
          const from = CHAINS[i];
          const to = CHAINS[j];
          return (
            <motion.line
              key={`${i}-${j}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={from.color}
              strokeWidth={0.15}
              strokeOpacity={0.25}
              initial={reduce ? false : { pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{
                duration: 2,
                delay: idx * 0.08,
                ease: EASE_OUT,
              }}
            />
          );
        })}

        {CHAINS.map((chain, i) => (
          <g key={chain.ticker}>
            <motion.circle
              cx={chain.x}
              cy={chain.y}
              r={4}
              fill={chain.color}
              fillOpacity={0.08}
              animate={
                reduce
                  ? undefined
                  : { scale: [1, 1.3, 1], opacity: [0.08, 0.15, 0.08] }
              }
              transition={{
                duration: 3,
                delay: i * 0.3,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
            <motion.circle
              cx={chain.x}
              cy={chain.y}
              r={1.2}
              fill={chain.color}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{
                type: "spring",
                stiffness: 200,
                damping: 15,
                delay: 0.5 + i * 0.1,
              }}
            />
            <text
              x={chain.x}
              y={chain.y + 3.2}
              textAnchor="middle"
              fill={chain.color}
              fillOpacity={0.5}
              fontSize={2.8}
              fontWeight={600}
              fontFamily="var(--font-inter), system-ui, sans-serif"
              letterSpacing="0.08em"
            >
              {chain.ticker}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

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
      <p className="text-3xl font-bold tracking-tight text-white md:text-4xl">
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
      <p className="mt-1.5 text-xs font-medium tracking-wide text-white/40 uppercase">
        {label}
      </p>
    </div>
  );
}

function Nav() {
  return (
    <motion.header
      className="fixed inset-x-0 top-0 z-50 border-b border-white/[0.04] bg-background/70 backdrop-blur-xl"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: EASE_OUT }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-500/20">
            <Sparkles size={16} className="text-white" />
          </div>
          <span className="text-[15px] font-semibold tracking-tight text-white">
            PocketAgent
          </span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          <Link
            href="/chat"
            className="text-[13px] font-medium text-white/50 transition-colors hover:text-white/90"
          >
            Chat
          </Link>
          <Link
            href="/dashboard"
            className="text-[13px] font-medium text-white/50 transition-colors hover:text-white/90"
          >
            Dashboard
          </Link>
          <Link
            href="/agents"
            className="text-[13px] font-medium text-white/50 transition-colors hover:text-white/90"
          >
            Agents
          </Link>
          <div className="ml-2">
            <ConnectButton />
          </div>
        </nav>

        <div className="md:hidden">
          <ConnectButton />
        </div>
      </div>
    </motion.header>
  );
}

function GradientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden">
      <div className="absolute inset-0 grid-pattern opacity-40" />
      <div className="absolute -left-40 -top-40 h-[500px] w-[500px] rounded-full bg-blue-500/5 blur-[120px]" />
      <div className="absolute -right-40 bottom-0 h-[400px] w-[400px] rounded-full bg-orange-500/4 blur-[100px]" />
      <div className="absolute left-1/2 top-1/3 h-[300px] w-[300px] -translate-x-1/2 rounded-full bg-blue-400/3 blur-[80px]" />
    </div>
  );
}

/* ── Main Page ──────────────────────────────────────────────────────── */

export default function Home() {
  const reduce = useReducedMotion();
  const featuresRef = useRef<HTMLElement>(null);
  const featuresInView = useInView(featuresRef, { once: true, margin: "-60px" });
  const statsRef = useRef<HTMLElement>(null);
  const statsInView = useInView(statsRef, { once: true, margin: "-80px" });

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

  return (
    <div className="relative min-h-[100dvh] text-white">
      <GradientBackground />

      <Nav />

      {/* ── Hero ────────────────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto flex min-h-[100dvh] max-w-7xl flex-col px-6 pt-28 md:flex-row md:items-center md:pt-0">
        <motion.div
          className="flex-1 md:pr-12 lg:pr-16"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div
            variants={itemVariants}
            className="inline-flex items-center gap-2 rounded-full border border-white/8 bg-white/[0.03] px-3.5 py-1.5"
          >
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-green-400" />
            </span>
            <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-white/50">
              Decentralized RPC
            </span>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="mt-8 text-[clamp(2.5rem,6vw,4.5rem)] font-bold leading-[0.95] tracking-tight"
          >
            AI Agents for the{" "}
            <span className="gradient-text">Multi-Chain</span>
            <br />
            World
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="mt-6 max-w-lg text-[15px] leading-relaxed text-white/45 md:text-base"
          >
            Deploy autonomous agents that read and compare 52 blockchains
            through a single decentralized interface, with guarded native
            transaction signing on EVM, Solana, and Tron. No gatekeepers. No
            central RPC provider.
          </motion.p>

          <motion.div
            variants={itemVariants}
            className="mt-10 flex flex-wrap items-center gap-4"
          >
            <Link
              href="/agents"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-600 hover:shadow-blue-500/30 active:translate-y-0.5"
            >
              Get Started
              <ArrowRight size={16} />
            </Link>
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-6 py-3 text-sm font-semibold text-white/70 transition-all hover:border-white/20 hover:bg-white/[0.06] hover:text-white active:translate-y-0.5"
            >
              Try Demo
            </Link>
          </motion.div>
        </motion.div>

        <motion.div
          className="mt-12 flex-1 md:mt-0"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, delay: 0.3, ease: EASE_OUT }}
        >
          <div className="relative mx-auto aspect-square max-w-lg md:ml-auto">
            <div className="glow-blue absolute inset-0 rounded-full" />
            <ChainNetwork />
          </div>
        </motion.div>
      </section>

      {/* ── Features (Asymmetric Bento) ─────────────────────────────── */}
      <section
        ref={featuresRef}
        className="relative z-10 mx-auto max-w-7xl px-6 pb-32 pt-16 md:pt-24"
      >
        <motion.div
          className="mx-auto mb-16 max-w-2xl text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={featuresInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Everything a multi-chain agent needs
          </h2>
          <p className="mt-4 text-[15px] text-white/40">
            Read and compare every major blockchain protocol from a single
            agent interface, with live native transfers for EVM, Solana, and
            Tron.
          </p>
        </motion.div>

        <div className="grid gap-5 md:grid-cols-3">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            const isLarge = feature.span === "large";
            const delay = i * 0.12;

            return (
              <motion.div
                key={feature.title}
                className={`group relative overflow-hidden rounded-2xl border border-white/[0.06] bg-card transition-all hover:border-white/[0.12] ${
                  isLarge ? "md:col-span-2" : "md:col-span-1"
                }`}
                initial={reduce ? false : { opacity: 0, y: 30 }}
                animate={featuresInView ? { opacity: 1, y: 0 } : {}}
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
                    <h3 className="text-[17px] font-semibold tracking-tight text-white">
                      {feature.title}
                    </h3>
                  </div>

                  <p className="max-w-md text-sm leading-relaxed text-white/45">
                    {feature.description}
                  </p>

                  {isLarge && (
                    <div className="relative mt-6 h-32 overflow-hidden rounded-xl border border-white/[0.04] bg-black/20 md:h-40">
                      <Image
                        src={`https://picsum.photos/seed/${feature.imageSeed}/600/300`}
                        alt=""
                        fill
                        className="object-cover opacity-50 transition-opacity group-hover:opacity-70"
                        sizes="(max-width: 768px) 100vw, 66vw"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-card via-card/60 to-transparent" />
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* ── Stats ───────────────────────────────────────────────────── */}
      <section
        ref={statsRef}
        className="relative z-10 mx-auto max-w-7xl px-6 pb-32"
      >
        <div className="rounded-2xl border border-white/[0.06] bg-card p-8 md:p-12">
          <div className="grid grid-cols-2 gap-10 md:grid-cols-4 md:gap-8">
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
            className="mt-10 border-t border-white/[0.06] pt-6 text-center"
            initial={{ opacity: 0 }}
            animate={statsInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.6, duration: 0.6 }}
          >
            <p className="text-xs text-white/30">
              Real-time data via Pocket Network decentralized RPC. No third-party indexers required.
            </p>
          </motion.div>
        </div>
      </section>

      {/* ── Ecosystem / Logo Wall ──────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-6 pb-32">
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <p className="mb-8 text-[11px] font-medium uppercase tracking-[0.18em] text-white/25">
            Powered by Pocket Network
          </p>

          <div className="mx-auto flex max-w-2xl flex-wrap items-center justify-center gap-x-10 gap-y-6">
            {[
              { slug: "ethereum", name: "Ethereum" },
              { slug: "solana", name: "Solana" },
              { slug: "polygon", name: "Polygon" },
              { slug: "cosmos", name: "Cosmos" },
              { slug: "sui", name: "Sui" },
              { slug: "near", name: "NEAR" },
              { slug: "tron", name: "Tron" },
              { slug: "bitcoin", name: "Bitcoin" },
            ].map((chain) => (
              <div
                key={chain.slug}
                className="flex items-center gap-2.5 opacity-30 transition-opacity hover:opacity-50"
              >
                <Image
                  src={`https://cdn.simpleicons.org/${chain.slug}/888888`}
                  alt={chain.name}
                  width={24}
                  height={24}
                  className="h-6 w-6"
                />
                <span className="text-sm font-medium text-white/40">
                  {chain.name}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-white/[0.04] px-6 py-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex items-center gap-2.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-blue-500 to-blue-600">
              <Sparkles size={12} className="text-white" />
            </div>
            <span className="text-xs font-medium text-white/30">
              PocketAgent
            </span>
          </div>

          <div className="flex items-center gap-6">
            <Link
              href="/chat"
              className="text-xs text-white/25 transition-colors hover:text-white/50"
            >
              Chat
            </Link>
            <Link
              href="/dashboard"
              className="text-xs text-white/25 transition-colors hover:text-white/50"
            >
              Dashboard
            </Link>
            <Link
              href="/agents"
              className="text-xs text-white/25 transition-colors hover:text-white/50"
            >
              Agents
            </Link>
          </div>

          <p className="text-[11px] text-white/20">
            Powered by Pocket Network
          </p>
        </div>
      </footer>
    </div>
  );
}

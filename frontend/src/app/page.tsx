"use client";

import { useRef, useMemo, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
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
  Layers,
  PlugZap,
  ShieldCheck,
  Globe,
  ArrowRight,
} from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { ConnectButton } from "@/components/wallet/connect-button";
import { useLandingTheme } from "@/hooks/use-landing-theme";
import { cn } from "@/lib/utils";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

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

const CHAIN_LOGOS = [
  { slug: "ethereum", name: "Ethereum" },
  { slug: "solana", name: "Solana" },
  { slug: "polygon", name: "Polygon" },
  { slug: "cosmos", name: "Cosmos" },
  { slug: "sui", name: "Sui" },
  { slug: "near", name: "NEAR" },
  { slug: "tron", name: "Tron" },
  { slug: "bitcoin", name: "Bitcoin" },
];

function ChainNetwork({ theme }: { theme: "light" | "dark" }) {
  const reduce = useReducedMotion();

  return (
    <div className="relative flex h-full w-full items-center justify-center">
      <div
        className={cn(
          "absolute h-80 w-80 rounded-full blur-[100px]",
          theme === "light" ? "bg-blue-500/8" : "bg-blue-500/10",
        )}
      />
      <div
        className={cn(
          "absolute h-60 w-60 translate-x-32 translate-y-16 rounded-full blur-[80px]",
          theme === "light" ? "bg-amber-400/10" : "bg-orange-500/8",
        )}
      />

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
              transition={{ duration: 2, delay: idx * 0.08, ease: EASE_OUT }}
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

function Nav() {
  const navLinks = (
    <>
      <Link href="/chat" className="landing-nav-link text-[13px] font-medium">
        Chat
      </Link>
      <Link href="/dashboard" className="landing-nav-link text-[13px] font-medium">
        Dashboard
      </Link>
      <Link href="/agents" className="landing-nav-link landing-nav-link-gold text-[13px] font-medium">
        Agents
      </Link>
    </>
  );

  return (
    <motion.header
      className="landing-nav fixed inset-x-0 top-0 z-50 border-b backdrop-blur-xl"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: EASE_OUT }}
    >
      <div className="safe-top mx-auto max-w-7xl px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex flex-col gap-3 md:hidden">
          <div className="flex items-center justify-between gap-2">
            <Logo
              size="md"
              textClassName="landing-logo truncate text-sm"
              accentClassName="landing-logo-accent"
            />
            <div className="flex shrink-0 items-center gap-2">
              <ThemeToggle className="landing-theme-toggle" />
              <ConnectButton tone="landing" />
            </div>
          </div>
          <nav className="flex items-center justify-center gap-1 rounded-full border border-[var(--lp-border)] bg-[var(--lp-surface)] p-1">
            <Link href="/chat" className="landing-nav-link flex-1 rounded-full px-2 py-2 text-center text-xs font-medium">
              Chat
            </Link>
            <Link href="/dashboard" className="landing-nav-link flex-1 rounded-full px-2 py-2 text-center text-xs font-medium">
              Dashboard
            </Link>
            <Link href="/agents" className="landing-nav-link landing-nav-link-gold flex-1 rounded-full px-2 py-2 text-center text-xs font-medium">
              Agents
            </Link>
          </nav>
        </div>

        <div className="hidden items-center justify-between md:flex">
          <Logo
            size="md"
            textClassName="landing-logo text-[15px]"
            accentClassName="landing-logo-accent"
          />
          <nav className="flex items-center gap-6">{navLinks}</nav>
          <div className="flex items-center gap-2">
            <ThemeToggle className="landing-theme-toggle" />
            <ConnectButton tone="landing" />
          </div>
        </div>
      </div>
    </motion.header>
  );
}

function GradientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden">
      <div className="absolute inset-0 grid-pattern opacity-40" />
      <div className="landing-orb-blue absolute -left-40 -top-40 h-[500px] w-[500px] rounded-full blur-[120px]" />
      <div className="landing-orb-accent absolute -right-40 bottom-0 h-[400px] w-[400px] rounded-full blur-[100px]" />
      <div className="landing-orb-blue absolute left-1/2 top-1/3 h-[300px] w-[300px] -translate-x-1/2 rounded-full blur-[80px]" />
    </div>
  );
}

const LANDING_THEME_STYLES = {
  light: {
    backgroundColor: "#ffffff",
    color: "#0f172a",
  },
  dark: {
    backgroundColor: "oklch(12% 0.01 255)",
    color: "oklch(92.5% 0.005 255)",
  },
} as const;

export default function Home() {
  const router = useRouter();
  const { isConnected, isConnecting, isReconnecting } = useAccount();
  const reduce = useReducedMotion();
  const { theme } = useLandingTheme();
  const featuresRef = useRef<HTMLElement>(null);
  const featuresInView = useInView(featuresRef, { once: true, margin: "-60px" });
  const statsRef = useRef<HTMLElement>(null);
  const statsInView = useInView(statsRef, { once: true, margin: "-80px" });

  const chainIconColor = theme === "light" ? "1E88E5" : "888888";

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

  if (isConnected || isConnecting || isReconnecting) {
    return (
      <div
        className="landing-page flex min-h-[100dvh] items-center justify-center"
        data-landing-theme={theme}
        style={LANDING_THEME_STYLES[theme]}
      >
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#1E88E5]/20 border-t-[#1E88E5]" />
      </div>
    );
  }

  return (
    <div
      className="landing-page relative min-h-[100dvh]"
      data-landing-theme={theme}
      style={LANDING_THEME_STYLES[theme]}
    >
      <GradientBackground />
      <Nav />

      <section className="relative z-10 mx-auto flex min-h-[100dvh] max-w-7xl flex-col px-4 pb-8 pt-36 sm:px-6 sm:pt-32 md:flex-row md:items-center md:px-6 md:pb-0 md:pt-0">
        <motion.div
          className="flex-1 md:pr-12 lg:pr-16"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div
            variants={itemVariants}
            className="landing-badge inline-flex items-center gap-2 rounded-full px-3.5 py-1.5"
          >
            <span className="relative flex h-1.5 w-1.5">
              <span
                className={cn(
                  "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
                  theme === "light" ? "bg-[#1E88E5]" : "bg-green-400",
                )}
              />
              <span
                className={cn(
                  "relative inline-flex h-1.5 w-1.5 rounded-full",
                  theme === "light" ? "bg-[#1E88E5]" : "bg-green-400",
                )}
              />
            </span>
            <span className="landing-badge-text text-[11px] font-semibold uppercase tracking-[0.12em]">
              Decentralized RPC
            </span>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="landing-heading mt-8 text-[clamp(2.5rem,6vw,4.5rem)] font-bold leading-[0.95] tracking-tight"
          >
            AI Agents for the{" "}
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
            transaction signing on EVM, Solana, and Tron. No gatekeepers. No
            central RPC provider.
          </motion.p>

          <motion.div
            variants={itemVariants}
            className="landing-btn-row mt-8 flex flex-wrap items-center gap-3 sm:mt-10 sm:gap-4"
          >
            <Link href="/agents" className="landing-btn">
              Get Started
              <ArrowRight size={16} />
            </Link>
            <Link href="/chat" className="landing-btn">
              Try Demo
            </Link>
          </motion.div>
        </motion.div>

        <motion.div
          className="mt-8 hidden flex-1 sm:block md:mt-0"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, delay: 0.3, ease: EASE_OUT }}
        >
          <div className="relative mx-auto aspect-square max-w-md md:ml-auto md:max-w-lg">
            <div className="glow-blue absolute inset-0 rounded-full" />
            <ChainNetwork theme={theme} />
          </div>
        </motion.div>
      </section>

      <section
        ref={featuresRef}
        className="relative z-10 mx-auto max-w-7xl px-4 pb-20 pt-12 sm:px-6 sm:pb-32 sm:pt-16 md:pt-24"
      >
        <motion.div
          className="mx-auto mb-16 max-w-2xl text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={featuresInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <h2 className="landing-section-title text-3xl font-bold tracking-tight md:text-4xl">
            Everything a <span className="landing-section-accent">multi-chain</span> agent needs
          </h2>
          <p className="landing-section-desc mt-4 text-[15px]">
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
                className={cn(
                  "landing-card group relative overflow-hidden rounded-2xl",
                  isLarge ? "md:col-span-2" : "md:col-span-1",
                )}
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
                    <h3 className="landing-card-title text-[17px] font-semibold tracking-tight">
                      {feature.title}
                    </h3>
                  </div>

                  <p className="landing-card-desc max-w-md text-sm leading-relaxed">
                    {feature.description}
                  </p>

                  {isLarge && (
                    <div className="landing-card-image relative mt-6 h-32 overflow-hidden rounded-xl md:h-40">
                      <Image
                        src={`https://picsum.photos/seed/${feature.imageSeed}/600/300`}
                        alt=""
                        fill
                        className="object-cover opacity-50 transition-opacity group-hover:opacity-70"
                        sizes="(max-width: 768px) 100vw, 66vw"
                      />
                      <div className="landing-card-image-overlay absolute inset-0" />
                    </div>
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
            animate={statsInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.6, duration: 0.6 }}
          >
            <p className="text-xs">
              Real-time data via{" "}
              <span className="landing-stats-footer-gold">Pocket Network</span>{" "}
              decentralized RPC. No third-party indexers required.
            </p>
          </motion.div>
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-7xl px-4 pb-20 sm:px-6 sm:pb-32">
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <p className="landing-powered mb-8 text-[11px] font-semibold uppercase tracking-[0.18em]">
            Powered by Pocket Network
          </p>

          <div className="mx-auto flex max-w-2xl flex-wrap items-center justify-center gap-x-10 gap-y-6">
            {CHAIN_LOGOS.map((chain) => (
              <div
                key={chain.slug}
                className="landing-chain-item flex items-center gap-2.5 transition-opacity"
              >
                <Image
                  src={`https://cdn.simpleicons.org/${chain.slug}/${chainIconColor}`}
                  alt={chain.name}
                  width={24}
                  height={24}
                  className="h-6 w-6"
                />
                <span className="landing-chain-name text-sm font-medium">
                  {chain.name}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      <footer className="landing-footer safe-bottom relative z-10 border-t px-4 py-6 sm:px-6 sm:py-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-5 text-center md:flex-row md:text-left">
          <Logo
            size="xs"
            href={null}
            textClassName="landing-logo text-xs"
            accentClassName="landing-logo-accent"
          />

          <div className="flex items-center gap-6">
            <Link href="/chat" className="landing-footer-link text-xs font-medium">
              Chat
            </Link>
            <Link href="/dashboard" className="landing-footer-link text-xs font-medium">
              Dashboard
            </Link>
            <Link href="/agents" className="landing-footer-link landing-footer-link-gold text-xs font-medium">
              Agents
            </Link>
          </div>

          <p className="landing-footer-powered text-[11px]">
            Powered by <span className="landing-footer-powered-gold">Pocket Network</span>
          </p>
        </div>
      </footer>
    </div>
  );
}
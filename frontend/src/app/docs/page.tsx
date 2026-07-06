"use client";

import { useRef } from "react";
import Link from "next/link";
import { motion, useInView, useReducedMotion } from "motion/react";
import {
  Terminal,
  PlugZap,
  Globe,
  Server,
  ArrowRight,
  Copy,
  Check,
  ExternalLink,
} from "lucide-react";
import { useState } from "react";
import { SiteHeader } from "@/components/layout/site-header";
import { useLandingTheme } from "@/hooks/use-landing-theme";
import { cn } from "@/lib/utils";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const SECTIONS = [
  { id: "quickstart", label: "Quick Start" },
  { id: "api", label: "API" },
  { id: "mcp", label: "MCP" },
  { id: "chains", label: "Chains" },
  { id: "tools", label: "Tools" },
];

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="absolute right-3 top-3 rounded-md p-1.5 opacity-50 transition hover:opacity-100 hover:bg-white/10"
      aria-label="Copy to clipboard"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
}

function CodeBlock({ children, lang }: { children: string; lang?: string }) {
  return (
    <div className="group relative">
      <CopyButton text={children} />
      <pre className="overflow-x-auto rounded-xl border bg-black/30 px-4 py-3.5 text-[13px] leading-relaxed">
        <code>{children}</code>
      </pre>
    </div>
  );
}

function SectionHeading({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2
      id={id}
      className="mb-6 mt-16 text-2xl font-bold tracking-tight first:mt-0"
    >
      {children}
    </h2>
  );
}

function GradientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 landing-grid-pattern opacity-30" />
      <div className="landing-orb-blue absolute -left-40 -top-40 h-[400px] w-[400px] rounded-full blur-[120px]" />
      <div className="landing-orb-accent absolute -right-40 bottom-0 h-[300px] w-[300px] rounded-full blur-[100px]" />
    </div>
  );
}

export default function DocsPage() {
  const { theme } = useLandingTheme();
  const reduce = useReducedMotion();
  const contentRef = useRef<HTMLDivElement>(null);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="landing-page relative min-h-[100dvh]" data-landing-theme={theme}>
      <GradientBackground />
      <SiteHeader />

      <div className="relative z-10 mx-auto flex max-w-7xl gap-10 px-4 pt-8 pb-24 sm:px-6 md:pt-12">
        {/* Sidebar */}
        <aside className="hidden w-48 shrink-0 lg:block">
          <nav className="sticky top-24 space-y-0.5">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest opacity-50">
              On this page
            </p>
            {SECTIONS.map((s) => (
              <button
                key={s.id}
                onClick={() => scrollTo(s.id)}
                className="block w-full rounded-lg px-3 py-1.5 text-left text-[13px] font-medium opacity-60 transition hover:opacity-100 hover:bg-white/5"
              >
                {s.label}
              </button>
            ))}
            <div className="mt-4 border-t pt-4">
              <a
                href="https://github.com/Jayanng/PocketAgent"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-[13px] font-medium opacity-50 transition hover:opacity-100"
              >
                GitHub
                <ExternalLink size={11} />
              </a>
            </div>
          </nav>
        </aside>

        {/* Content */}
        <motion.div
          ref={contentRef}
          className="min-w-0 flex-1"
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_OUT }}
        >
          {/* Page header */}
          <div className="mb-12">
            <h1 className="text-[clamp(2rem,5vw,3rem)] font-bold leading-[1.1] tracking-tight">
              Documentation
            </h1>
            <p className="mt-3 text-[15px] opacity-60">
              Everything you need to integrate PocketAgent — REST API, MCP server,
              tool reference, and supported chains.
            </p>
          </div>

          {/* ── Quick Start ── */}
          <SectionHeading id="quickstart">Quick Start</SectionHeading>
          <div className="space-y-8">
            <div>
              <h3 className="mb-3 text-[15px] font-semibold">Install the MCP server</h3>
              <CodeBlock lang="bash">pip install pocketagent</CodeBlock>
              <p className="mt-3 text-[13px] opacity-60">
                One command installs the full PocketAgent MCP server with 51 blockchain
                tools. Requires Python 3.11+.
              </p>
            </div>

            <div>
              <h3 className="mb-3 text-[15px] font-semibold">Configure your MCP client</h3>
              <p className="mb-3 text-[13px] opacity-60">
                Add this to your Claude Desktop, Cursor, or Codex config:
              </p>
              <CodeBlock lang="json">{`{
  "mcpServers": {
    "pocketagent": {
      "command": "pocketagent-mcp",
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ENCRYPTION_KEY": "...",
        "JWT_SECRET": "..."
      }
    }
  }
}`}</CodeBlock>
            </div>

            <div>
              <h3 className="mb-3 text-[15px] font-semibold">Run the full platform locally</h3>
              <CodeBlock lang="bash">git clone https://github.com/Jayanng/PocketAgent.git
cd PocketAgent
npm install
cd backend && pip install -r requirements.txt
cp .env.example .env   # set your keys
cd .. && npm run dev</CodeBlock>
              <p className="mt-3 text-[13px] opacity-60">
                Launches the web UI at <code className="rounded bg-white/10 px-1 py-0.5 text-xs">localhost:3000</code>{" "}
                and the REST API at <code className="rounded bg-white/10 px-1 py-0.5 text-xs">localhost:8000</code>.
              </p>
            </div>
          </div>

          {/* ── API Reference ── */}
          <SectionHeading id="api">REST API</SectionHeading>
          <p className="mb-6 text-[14px] leading-relaxed opacity-70">
            All endpoints are served from the FastAPI backend. Interactive Swagger
            UI at <code className="rounded bg-white/10 px-1 py-0.5 text-xs">/docs</code>{" "}
            and ReDoc at <code className="rounded bg-white/10 px-1 py-0.5 text-xs">/redoc</code>.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b">
                  <th className="pb-3 pr-4 font-semibold">Method</th>
                  <th className="pb-3 pr-4 font-semibold">Endpoint</th>
                  <th className="pb-3 pr-4 font-semibold">Auth</th>
                  <th className="pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className="opacity-80">
                <tr className="border-b border-white/5">
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-emerald-400/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                      POST
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/agents</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">—</td>
                  <td className="py-2.5 text-[13px]">Create a new agent</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-sky-400/10 px-2 py-0.5 text-[11px] font-medium text-sky-400">
                      GET
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/agents</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">—</td>
                  <td className="py-2.5 text-[13px]">List all agents</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-sky-400/10 px-2 py-0.5 text-[11px] font-medium text-sky-400">
                      GET
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/agents/{"{id}"}</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">Token</td>
                  <td className="py-2.5 text-[13px]">Get agent details</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-amber-400/10 px-2 py-0.5 text-[11px] font-medium text-amber-400">
                      PUT
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/agents/{"{id}"}</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">Token</td>
                  <td className="py-2.5 text-[13px]">Update agent configuration</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-red-400/10 px-2 py-0.5 text-[11px] font-medium text-red-400">
                      DELETE
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/agents/{"{id}"}</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">Token</td>
                  <td className="py-2.5 text-[13px]">Soft-delete an agent</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-sky-400/10 px-2 py-0.5 text-[11px] font-medium text-sky-400">
                      GET
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/agents/{"{id}"}/balances</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">Token</td>
                  <td className="py-2.5 text-[13px]">Get multi-chain balances</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-emerald-400/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                      POST
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/agents/{"{id}"}/fund</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">Token</td>
                  <td className="py-2.5 text-[13px]">Get funding instructions</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-emerald-400/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                      POST
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/agents/{"{id}"}/reissue-token</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">Token</td>
                  <td className="py-2.5 text-[13px]">Reissue access token</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-emerald-400/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                      POST
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/chat</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">Token</td>
                  <td className="py-2.5 text-[13px]">Chat with agent (SSE stream)</td>
                </tr>
                <tr>
                  <td className="py-2.5 pr-4">
                    <span className="rounded-full bg-sky-400/10 px-2 py-0.5 text-[11px] font-medium text-sky-400">
                      GET
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[12px]">/api/analytics/relay-stats</td>
                  <td className="py-2.5 pr-4 text-[11px] opacity-50">—</td>
                  <td className="py-2.5 text-[13px]">Relay traffic analytics</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="mt-4 text-[12px] opacity-50">
            Endpoints marked <strong>Token</strong> require the{" "}
            <code className="rounded bg-white/10 px-1 py-0.5 text-xs">X-Agent-Access-Token</code> header.
          </p>

          {/* ── MCP Integration ── */}
          <SectionHeading id="mcp">MCP Server</SectionHeading>
          <p className="mb-6 text-[14px] leading-relaxed opacity-70">
            The standalone MCP server exposes all 51 tools, 5 resources, and 4
            prompts over stdio transport. Compatible with any MCP client.
          </p>

          <div className="grid gap-6 sm:grid-cols-2 mb-8">
            <div className="rounded-2xl border p-6">
              <h3 className="mb-4 text-[15px] font-semibold">Resources</h3>
              <ul className="space-y-3 text-[13px] opacity-70">
                <li><code className="rounded bg-white/10 px-1 py-0.5 text-xs">pocket://chains</code> — All chains</li>
                <li><code className="rounded bg-white/10 px-1 py-0.5 text-xs">pocket://chains/{"{chain}"}/status</code> — Chain health</li>
                <li><code className="rounded bg-white/10 px-1 py-0.5 text-xs">pocket://agents/{"{id}"}/stats</code> — Agent stats</li>
                <li><code className="rounded bg-white/10 px-1 py-0.5 text-xs">pocket://agents/{"{id}"}/wallet</code> — Wallet context</li>
                <li><code className="rounded bg-white/10 px-1 py-0.5 text-xs">pocket://cache/stats</code> — Cache metrics</li>
              </ul>
            </div>
            <div className="rounded-2xl border p-6">
              <h3 className="mb-4 text-[15px] font-semibold">Prompts</h3>
              <ul className="space-y-3 text-[13px] opacity-70">
                <li><strong>analyze_wallet</strong> — Multi-chain portfolio analysis</li>
                <li><strong>find_cheapest_chain</strong> — Lowest-fee chain finder</li>
                <li><strong>track_pokt_costs</strong> — Relay cost tracking</li>
                <li><strong>compare_and_recommend</strong> — Chain comparison</li>
              </ul>
            </div>
          </div>

          {/* ── Supported Chains ── */}
          <SectionHeading id="chains">Supported Chains</SectionHeading>
          <p className="mb-6 text-[14px] leading-relaxed opacity-70">
            52 production networks across 6 protocol families.
          </p>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                family: "EVM",
                count: 36,
                chains: "Ethereum, Polygon, Arbitrum, Optimism, Base, BNB, Avalanche, Fantom, Gnosis, Berachain, Blast, Celo, Linea, Scroll, zkSync Era, Sonic, Polygon zkEVM, Fraxtal, opBNB, Kaia, Kava, Moonbeam, Moonriver, Metis, Boba, Fuse, Harmony, IoTeX, Oasys, Sei EVM, Hyperliquid, Ink, Taiko, Unichain, XRPL EVM, zkLink Nova",
              },
              {
                family: "Cosmos",
                count: 12,
                chains: "Osmosis, Pocket, Akash, Juno, Seda, Persistence, Fetch.ai, Jackal, Cheqd, Chihuahua, Shentu, AtomOne",
              },
              { family: "Solana", count: 1, chains: "Solana Mainnet-Beta" },
              { family: "SUI", count: 1, chains: "SUI Mainnet" },
              { family: "NEAR", count: 1, chains: "NEAR Protocol Mainnet" },
              { family: "TRON", count: 1, chains: "TRON Mainnet" },
            ].map((f) => (
              <div key={f.family} className="rounded-2xl border p-5">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-[15px] font-semibold">{f.family}</h3>
                  <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-medium">
                    {f.count} chain{f.count > 1 ? "s" : ""}
                  </span>
                </div>
                <p className="text-[12px] leading-relaxed opacity-60">{f.chains}</p>
              </div>
            ))}
          </div>

          {/* ── Tools ── */}
          <SectionHeading id="tools">Tool Reference</SectionHeading>
          <p className="mb-6 text-[14px] leading-relaxed opacity-70">
            51 tools across 10 modules. Each tool is a typed function the LLM
            can call autonomously.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b">
                  <th className="pb-3 pr-4 font-semibold">Module</th>
                  <th className="pb-3 pr-4 font-semibold text-center">Tools</th>
                  <th className="pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className="opacity-80">
                {[
                  ["balance_tools", "6", "Native balance queries (EVM, Solana, Cosmos, SUI) + cross-chain comparison"],
                  ["chain_tools", "2", "List all chains, get chain metadata (RPC URL, explorer, decimals)"],
                  ["compare_tools", "3", "Compare gas fees, recommend optimal chains, estimate costs"],
                  ["transaction_tools", "15", "12 read tools (blocks, txns, receipts) + send_transaction, send_erc20, contract_call"],
                  ["token_tools", "13", "Token info, contract calls, event logs, domain resolution"],
                  ["token_transfer_tools", "6", "SPL, TRC-20, CW20, IBC, NEP-141, SUI coin transfers"],
                  ["simulation_tools", "1", "Dry-run transactions before broadcast"],
                  ["wallet_tools", "1", "Multi-chain portfolio report with CoinGecko"],
                  ["pokt_tools", "1", "Estimate relay cost in POKT"],
                  ["analytics_tools", "3", "Relay stats, history, cost breakdown"],
                ].map(([mod, count, desc]) => (
                  <tr key={mod} className="border-b border-white/5">
                    <td className="py-2.5 pr-4 font-mono text-[12px]">{mod}</td>
                    <td className="py-2.5 pr-4 text-center">
                      <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-medium">
                        {count}
                      </span>
                    </td>
                    <td className="py-2.5 text-[12px]">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── Bottom CTA ── */}
          <div className="mt-20 rounded-2xl border p-8 text-center sm:p-12">
            <h2 className="mb-3 text-xl font-bold tracking-tight">
              Ready to get started?
            </h2>
            <p className="mb-6 text-[14px] opacity-60">
              Create your first agent and start querying 52 chains in minutes.
            </p>
            <Link
              href="/agents"
              className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-[14px] font-semibold text-black transition hover:opacity-90"
            >
              Create Agent
              <ArrowRight size={15} />
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

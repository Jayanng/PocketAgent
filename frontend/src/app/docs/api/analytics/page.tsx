import { DocsPage } from "@/components/docs/docs-page";
import { ApiEndpoint, DocsProse, DocsP } from "@/components/docs/docs-ui";

export default function ApiAnalyticsPage() {
  return (
    <DocsPage title="Analytics API" description="Relay statistics, chain health probes, cost tracking, and portfolio views.">
      <DocsProse>
        <ApiEndpoint
          method="GET"
          path="/api/analytics/relay-stats?agent_id=&timeframe=day|week|all"
          auth="none"
          description="Aggregated relay counts, per-chain breakdown, daily trend, and notional POKT cost estimate."
        />
        <ApiEndpoint
          method="GET"
          path="/api/analytics/chain-health"
          auth="none"
          description="Latency and availability probes for headline chains (ethereum, polygon, arbitrum, optimism, bsc, base, solana)."
        />
        <ApiEndpoint
          method="GET"
          path="/api/analytics/cost-tracker?agent_id="
          auth="none"
          description="Per-chain spend tracking against agent caps when agent_id is provided."
        />
        <ApiEndpoint
          method="GET"
          path="/api/analytics/portfolio?agent_id="
          auth="token"
          description="Multi-chain portfolio with CoinGecko valuations when scoped to an agent."
        />
        <DocsP>
          When <code className="font-mono text-[12px]">agent_id</code> is provided on scoped endpoints, the
          token header is required and validated.
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}
export const INTERVAL_PRESETS: { label: string; seconds: number }[] = [
  { label: "5m", seconds: 300 },
  { label: "15m", seconds: 900 },
  { label: "1h", seconds: 3600 },
  { label: "6h", seconds: 21600 },
  { label: "12h", seconds: 43200 },
  { label: "24h", seconds: 86400 },
  { label: "weekly", seconds: 604800 },
];

export const TASK_TEMPLATES: {
  id: string;
  label: string;
  prompt: string;
  interval_seconds: number;
}[] = [
  {
    id: "portfolio",
    label: "Daily portfolio report",
    prompt:
      "Give me a full portfolio summary across all my chains with USD values",
    interval_seconds: 86400,
  },
  {
    id: "gas",
    label: "Hourly gas check",
    prompt:
      "Check current gas prices on Ethereum, Base, Arbitrum, Optimism and Polygon and summarize",
    interval_seconds: 3600,
  },
  {
    id: "balance",
    label: "Balance monitor",
    prompt:
      "Check my wallet balances across all chains and flag anything unusual",
    interval_seconds: 21600,
  },
  {
    id: "rebalance",
    label: "Weekly rebalance reminder",
    prompt:
      "Analyze my portfolio allocation and tell me if any position is more than 40% or less than 5% of total",
    interval_seconds: 604800,
  },
];

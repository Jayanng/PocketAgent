export type EnvVarScope = "backend" | "frontend" | "mcp";

export type EnvVarDef = {
  name: string;
  scope: EnvVarScope;
  required: boolean;
  description: string;
  example?: string;
  defaultValue?: string;
};

export const BACKEND_ENV_VARS: EnvVarDef[] = [
  { name: "OPENAI_API_KEY", scope: "backend", required: true, description: "API key for the LLM provider used by chat orchestration", example: "sk-..." },
  { name: "OPENAI_BASE_URL", scope: "backend", required: false, description: "OpenAI-compatible API base URL", defaultValue: "https://api.openai.com/v1", example: "https://api.gmi-serving.com/v1" },
  { name: "OPENAI_MODEL", scope: "backend", required: false, description: "Model identifier passed to the chat completion API", example: "openai/gpt-5.4-mini" },
  { name: "OPENAI_TEMPERATURE", scope: "backend", required: false, description: "Sampling temperature for chat completions", defaultValue: "0.3" },
  { name: "OPENAI_MAX_TOKENS", scope: "backend", required: false, description: "Max completion tokens per chat turn", defaultValue: "768" },
  { name: "CHAT_HISTORY_LIMIT", scope: "backend", required: false, description: "Number of prior messages included in LLM context", defaultValue: "10" },
  { name: "ENCRYPTION_KEY", scope: "backend", required: true, description: "32-byte key for AES-256 encryption of agent wallet keys", example: "replace-with-generated-32-byte-key" },
  { name: "JWT_SECRET", scope: "backend", required: true, description: "Secret for signing agent access tokens", example: "replace-with-generated-secret" },
  { name: "DATABASE_PATH", scope: "backend", required: false, description: "SQLite database file path (absolute recommended in production)", defaultValue: "./data/pocketagent.db" },
  { name: "CORS_ORIGINS", scope: "backend", required: false, description: "Comma-separated allowed frontend origins", defaultValue: "http://localhost:3000" },
  { name: "POCKET_RPC_URL", scope: "backend", required: false, description: "Default Pocket Network RPC gateway URL", example: "https://eth.api.pocket.network" },
  { name: "COINGECKO_API_URL", scope: "backend", required: false, description: "CoinGecko API base for portfolio valuations", defaultValue: "https://api.coingecko.com/api/v3" },
  { name: "COINGECKO_API_KEY", scope: "backend", required: false, description: "Optional CoinGecko Pro API key" },
  { name: "CACHE_TTL_BALANCE", scope: "backend", required: false, description: "Balance cache TTL in seconds", defaultValue: "300" },
  { name: "CACHE_TTL_GAS", scope: "backend", required: false, description: "Gas price cache TTL in seconds", defaultValue: "30" },
  { name: "NOTIONAL_POKT_PER_RELAY", scope: "backend", required: false, description: "Notional POKT cost estimate per relay for analytics", defaultValue: "0.00089" },
  { name: "DISABLE_AGENT_AUTH", scope: "backend", required: false, description: "Skip token checks in local dev only — never enable in production", defaultValue: "false" },
];

export const FRONTEND_ENV_VARS: EnvVarDef[] = [
  { name: "NEXT_PUBLIC_API_URL", scope: "frontend", required: true, description: "Backend API base URL (no trailing slash)", example: "http://127.0.0.1:8000" },
  { name: "NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID", scope: "frontend", required: true, description: "WalletConnect Cloud project ID for RainbowKit", example: "your-walletconnect-project-id" },
  { name: "NEXT_PUBLIC_DISABLE_AGENT_AUTH", scope: "frontend", required: false, description: "Mirror backend DISABLE_AGENT_AUTH for local UI dev", defaultValue: "false" },
];

export const MCP_ENV_VARS: EnvVarDef[] = [
  { name: "OPENAI_API_KEY", scope: "mcp", required: true, description: "Required when MCP tools invoke LLM-backed flows" },
  { name: "ENCRYPTION_KEY", scope: "mcp", required: true, description: "Required for write tools that sign with agent wallets" },
  { name: "JWT_SECRET", scope: "mcp", required: true, description: "Required to validate agent access tokens on protected tools" },
  { name: "DATABASE_PATH", scope: "mcp", required: false, description: "SQLite path for agent rows; use absolute path when installed via pip", defaultValue: "./data/pocketagent.db" },
];
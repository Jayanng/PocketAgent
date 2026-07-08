export type DocsNavLink = {
  title: string;
  href: string;
  description?: string;
};

export type DocsNavSection = {
  title: string;
  items: DocsNavLink[];
};

export const DOCS_VERSION = "1.0.1";

export const DOCS_NAV: DocsNavSection[] = [
  {
    title: "Introduction",
    items: [{ title: "Overview", href: "/docs", description: "What PocketAgent is and how to use these docs" }],
  },
  {
    title: "Getting Started",
    items: [
      { title: "Quick Start", href: "/docs/getting-started", description: "Install and run in minutes" },
      { title: "Installation", href: "/docs/getting-started/installation", description: "PyPI package and source install" },
      { title: "Local Development", href: "/docs/getting-started/local-development", description: "Full platform dev setup" },
      { title: "MCP Client Setup", href: "/docs/getting-started/mcp-setup", description: "Claude Desktop, Cursor, Codex" },
    ],
  },
  {
    title: "Concepts",
    items: [
      { title: "Platform Overview", href: "/docs/concepts", description: "How the pieces fit together" },
      { title: "Architecture", href: "/docs/concepts/architecture", description: "Frontend, API, MCP, and RPC layers" },
      { title: "Agents", href: "/docs/concepts/agents", description: "Capabilities, caps, and wallets" },
      { title: "Authentication", href: "/docs/concepts/authentication", description: "Access tokens and reissue flow" },
    ],
  },
  {
    title: "Guides",
    items: [
      { title: "Create an Agent", href: "/docs/guides/create-agent", description: "Configure chains and capabilities" },
      { title: "Fund an Agent", href: "/docs/guides/fund-agent", description: "Deposit native and token assets" },
      { title: "Chat & Streaming", href: "/docs/guides/chat", description: "REST chat and SSE events" },
      {
        title: "Automations",
        href: "/docs/guides/automations",
        description: "Schedule recurring agent prompts and track Pocket relays",
      },
    ],
  },
  {
    title: "REST API",
    items: [
      { title: "API Overview", href: "/docs/api", description: "Base URL, auth, and OpenAPI" },
      { title: "Agents", href: "/docs/api/agents", description: "CRUD, balances, funding, tokens" },
      { title: "Chat", href: "/docs/api/chat", description: "Chat, conversations, SSE stream" },
      { title: "Automations", href: "/docs/api/automations", description: "Scheduled tasks and relay stats" },
      { title: "Analytics", href: "/docs/api/analytics", description: "Relay stats, health, portfolio" },
    ],
  },
  {
    title: "MCP Server",
    items: [
      { title: "MCP Overview", href: "/docs/mcp", description: "stdio transport and adapter design" },
      { title: "Tools", href: "/docs/mcp/tools", description: "All 51 blockchain tools" },
      { title: "Resources", href: "/docs/mcp/resources", description: "Chain and agent resources" },
      { title: "Prompts", href: "/docs/mcp/prompts", description: "Built-in MCP prompts" },
    ],
  },
  {
    title: "Reference",
    items: [
      { title: "Supported Chains", href: "/docs/reference/chains", description: "52 networks across 6 protocols" },
      { title: "Configuration", href: "/docs/reference/configuration", description: "Environment variables" },
      { title: "Errors", href: "/docs/reference/errors", description: "HTTP status codes and troubleshooting" },
    ],
  },
  {
    title: "Operations",
    items: [
      { title: "Security", href: "/docs/security", description: "Caps, encryption, write-tool gates" },
      { title: "Deployment", href: "/docs/deployment", description: "Docker, Fly.io, production checklist" },
      { title: "Troubleshooting", href: "/docs/troubleshooting", description: "Common issues and fixes" },
    ],
  },
];

export const DOCS_FLAT_LINKS: DocsNavLink[] = DOCS_NAV.flatMap((section) => section.items);

export function getAdjacentDocsLinks(href: string): {
  prev: DocsNavLink | null;
  next: DocsNavLink | null;
} {
  const index = DOCS_FLAT_LINKS.findIndex((item) => item.href === href);
  if (index === -1) return { prev: null, next: null };
  return {
    prev: index > 0 ? DOCS_FLAT_LINKS[index - 1] : null,
    next: index < DOCS_FLAT_LINKS.length - 1 ? DOCS_FLAT_LINKS[index + 1] : null,
  };
}

export const DOCS_EXTERNAL_LINKS = [
  { title: "PyPI", href: "https://pypi.org/project/pokt-agent-mcp/" },
  { title: "GitHub", href: "https://github.com/Jayanng/PocketAgent" },
  { title: "OpenAPI (local)", href: "http://127.0.0.1:8000/docs" },
] as const;
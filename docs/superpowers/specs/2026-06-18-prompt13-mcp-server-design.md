# Prompt 13 — MCP Server: Design

**Date:** 2026-06-18
**Scope:** Codex Prompt 13 from `PocketAgent_Build_Plan (2).md` (lines 1647–1847)
**Status:** Approved (full transact via agent_id)

## Context

Prompt 13's `backend/mcp_server/` is currently a Prompt-2 scaffold: `server.py`
is a stub dataclass (`PocketAgentMCPServer`), `tools.py`/`resources.py` return
empty lists, and `prompts.py` does not exist. The MCP server is genuinely
unimplemented — this is a real build.

### Key discovery that reshapes the plan

The spec's pseudocode re-routes all 49 tools through a hand-written `if/elif`
chain calling `rpc_client.list_chains()`, `ChainRouter()...`, etc. **But all
49 tools are already implemented and registered** in
`backend/tools/TOOL_REGISTRY` with executors (verified: 37 read + 12 custom,
exact BQ-mirrored names, including 5 `radix_*` stubs). The chat path already
calls them via `execute_tool(name, ToolContext, args)`.

So the MCP server is a **thin adapter**, not a parallel routing layer:

- `list_tools()` → convert the 49 existing `ToolSpec` schemas (OpenAI function
  format) into MCP `Tool` objects (`name` / `description` / `inputSchema`).
- `call_tool(name, args)` → `execute_tool(name, context, args)` — reuse the
  registry. Zero duplicated routing, zero drift from the chat path.
- `list_resources()` / `read_resource()` → 5 resources from the spec.
- `list_prompts()` → 4 prompt templates from the spec.

## Goal

A working stdio MCP server exposing all 49 tools, 5 resources, and 4 prompts,
reusable by any MCP client (Claude Desktop, Codex). Verified by a hermetic
test suite and documented in `docs/mcp-server.md`.

## Approach

### Transact tools: full transact via agent_id (approved)

The MCP server has no built-in agent, but transact tools (`send_transaction`,
`send_erc20`, `contract_call`, `simulate_transaction`) need an agent wallet to
sign. The caller passes `agent_id` in the tool args; the server loads that
agent from the DB, constructs a `ToolContext` with it, and the existing
executors sign with the agent's decrypted key — identical to the chat path
(`ai_agent.py` builds `ToolContext(agent=..., rpc_client=..., relay_tracker=...,
db=...)` the same way). Read/compare/analytics tools run with a minimal
default context (no agent needed).

### Files (all under `backend/mcp_server/`)

- **`tools.py`** — `list_mcp_tools() -> list[Tool]`: converts each
  `TOOL_REGISTRY` `ToolSpec` (OpenAI function schema) to an MCP `Tool`
  (`name`, `description`, `inputSchema`). 49 tools.
- **`resources.py`** — 5 `Resource` defs + `read_resource(uri)`: chain metadata
  (`pocket://chains`), chain status (`pocket://chains/{chain}/status` via
  `rpc.get_block_number`), agent stats (`pocket://agents/{id}/stats` via
  `relay_tracker`), agent wallet (`pocket://agents/{id}/wallet` via
  `rpc.get_balance`), cache stats (`pocket://cache/stats`).
- **`prompts.py`** — 4 `Prompt` templates: `analyze_wallet`,
  `find_cheapest_chain`, `track_pokt_costs`, `compare_and_recommend`, each
  with its `PromptArgument`s.
- **`server.py`** — replaces the scaffold. `mcp.server.Server("pocketagent")`
  with `@server.list_tools()`, `@server.call_tool()`, `@server.list_resources()`,
  `@server.read_resource()`, `@server.list_prompts()`. `call_tool` resolves
  `agent_id` from args (loads agent from DB for transact; default context
  otherwise), builds `ToolContext`, calls `execute_tool`, JSON-dumps the result
  into `TextContent`. Stdio entry point: `asyncio.run(main())` using
  `mcp.server.stdio.stdio_server`.
- **`docs/mcp-server.md`** — install/run, Claude Desktop +
  Codex config (`claude_desktop_config.json` + `settings.json`), full 49-tool
  list with params, 5 resources + URIs, 4 prompts + args, usage examples,
  caching/POKT-saved notes, human-readable output + event decoding notes.

### Tests — `backend/tests/test_prompt13_mcp_server.py`

Hermetic (faked `PocketRPCClient` / `RelayTrackerService`, no network/DB for
read paths; a temp sqlite DB for the agent_id transact path). Mirrors the
`test_prompt12` fixture style. Covers:

- `list_mcp_tools()` returns 49 tools with correct names + `inputSchema`.
- Schema conversion preserves `required` fields.
- `call_tool` routes a read tool (`evm_get_balance`) through the registry and
  returns `TextContent` with JSON.
- `call_tool` routes a compare tool (`compare_chains`).
- `call_tool` with a transact tool loads the seeded agent by `agent_id`
  (default-context path is not used for transact).
- Unknown tool → error surfaced as `TextContent`, not an unhandled crash.
- `list_resources()` returns the 5 resources; `read_resource` for
  `pocket://chains` returns registry metadata, `pocket://cache/stats` returns
  cache stats.
- `list_prompts()` returns the 4 templates with correct `arguments`.

## Out of scope

- Live Pocket RPC / CoinGecko in tests (kept hermetic).
- Re-implementing the tool executors (they already exist in `tools/`).
- WebSocket/SSE MCP transports (stdio only, per spec).
- Changes to the chat path or `tools/` registry.

## Completion bar

"Flawless" = backend import clean, full pytest suite green (existing 41 +
new `test_prompt13`), `docs/mcp-server.md` complete, output shown to the user.
Frontend lint/build unchanged (Prompt 13 is backend-only). Commit + push to
GitHub.

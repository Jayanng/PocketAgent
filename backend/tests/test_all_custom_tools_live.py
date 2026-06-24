"""Test all 12 custom tools over MCP with a live agent in the database.

Steps:
1. Starts the backend API (creates the SQLite DB)
2. Creates an agent via POST /api/agents
3. Starts the MCP server and calls all custom tool categories
4. Cleans up both processes

Both API and MCP server use the same absolute DATABASE_PATH so the agent
created by the API is visible to the MCP server.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
API_BASE = "http://127.0.0.1:8765"
MCP_MODULE = "backend.mcp_server.server"

# Shared database path (absolute, same for both API and MCP server)
SHARED_DB_DIR = Path(tempfile.mkdtemp(prefix="pocketagent-mcp-test-"))
SHARED_DB_PATH = str(SHARED_DB_DIR / "pocketagent.db")

# Environment for both subprocesses: override DATABASE_PATH to shared absolute path
BASE_ENV = os.environ.copy()
BASE_ENV["DATABASE_PATH"] = SHARED_DB_PATH

EVM_TEST_FROM = "0x0000000000000000000000000000000000000001"
EVM_TEST_TO = "0x000000000000000000000000000000000000dEaD"
USDC_ETHEREUM = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

# Custom tool test cases
CUSTOM_TOOL_TESTS = [
    # (name, args, category, requires_live_rpc)
    ("estimate_relay_cost", {"chain": "ethereum", "operation": "read_balance"}, "POKT", False),
    ("compare_chains", {"chains": ["ethereum", "polygon"]}, "Compare", True),
    ("recommend_chain", {"operation_type": "native_transfer"}, "Compare", True),
    ("estimate_transaction_cost", {
        "chain": "ethereum",
        "operation_type": "native_transfer",
        "from_address": EVM_TEST_FROM,
    }, "Compare", True),
    ("analyze_wallet", {
        "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "chains": ["ethereum", "polygon"],
    }, "Compositional", True),
    ("simulate_transaction", {
        "chain": "ethereum",
        "to_address": EVM_TEST_TO,
        "amount": "0.01",
        "from_address": EVM_TEST_FROM,
        "operation_type": "native_transfer",
    }, "Simulation", True),
]

# Agent-dependent tools (tested separately with the live agent_id)
AGENT_TOOL_TESTS = [
    ("get_relay_stats", {"timeframe": "all"}, "Analytics"),
    ("get_cost_breakdown", {"timeframe": "all"}, "Analytics"),
    ("send_transaction", {"chain": "ethereum", "to_address": EVM_TEST_TO, "amount": "0"}, "Write"),
    ("send_erc20", {
        "chain": "ethereum", "token_address": USDC_ETHEREUM,
        "to_address": EVM_TEST_TO, "amount": "0", "token_decimals": 6,
    }, "Write"),
    ("contract_call", {
        "chain": "ethereum", "contract_address": USDC_ETHEREUM,
        "abi_function": "totalSupply()", "args": [], "data": "0x",
        "mode": "read",
    }, "Write"),
]


EXPECTED_LIVE_WRITE_ERRORS = (
    "insufficient funds",
    "gas required exceeds allowance",
    "exceeds ethereum spending cap",
    "nonce too low",
    "replacement transaction underpriced",
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def api_post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API_BASE}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


async def mcp_call(proc, request_id: int, name: str, args: dict, timeout: float = 25) -> dict:
    """Send a tools/call request to the MCP server and return the parsed response."""
    assert proc.stdin is not None
    assert proc.stdout is not None

    req = json.dumps({
        "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
        "params": {"name": name, "arguments": args},
    })
    proc.stdin.write((req + "\n").encode())
    await proc.stdin.drain()

    line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
    return json.loads(line.decode().strip())


async def mcp_initialize(proc) -> None:
    """Send initialize + initialized notification to the MCP server."""
    assert proc.stdin is not None
    assert proc.stdout is not None

    init = json.dumps({
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0", "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0.0"},
        },
    })
    proc.stdin.write((init + "\n").encode())
    await proc.stdin.drain()
    await asyncio.wait_for(proc.stdout.readline(), timeout=10)

    notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
    proc.stdin.write((notif + "\n").encode())
    await proc.stdin.drain()
    await asyncio.sleep(0.3)


# ── Main ─────────────────────────────────────────────────────────────────────


async def main() -> bool:
    api_proc = None
    mcp_proc = None
    all_ok = True
    agent_id = ""
    agent_access_token = ""

    try:
        # ── 1. Start the backend API ────────────────────────────────────────
        print("=" * 60)
        print("Starting backend API...")
        print("=" * 60)
        api_proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "uvicorn", "main:app",
            "--port", "8765", "--host", "127.0.0.1",
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(BACKEND_DIR),
            env=BASE_ENV,
        )
        # Wait for the API to be ready
        for _ in range(20):
            try:
                with urllib.request.urlopen(f"{API_BASE}/docs", timeout=3) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                pass
            await asyncio.sleep(0.5)
        print("[OK] API is running\n")

        # ── 2. Create an agent ──────────────────────────────────────────────
        print("-" * 60)
        print("Creating agent...")
        print("-" * 60)
        agent = api_post("/api/agents", {
            "name": "MCP Test Agent",
            "description": "Auto-created for MCP custom tool testing",
            "chains": ["ethereum", "polygon", "solana"],
            "capabilities": ["read", "compare", "transact", "analytics"],
        })
        agent_id = agent["id"]
        agent_access_token = agent["access_token"]
        wallet = agent.get("wallet_address", "unknown")
        print(f"[OK] Agent created:")
        print(f"      ID:      {agent_id}")
        print(f"      Wallet:  {wallet}")
        print(f"      Chains:  {', '.join(agent.get('chains', []))}\n")

        # ── 3. Start the MCP server ─────────────────────────────────────────
        print("-" * 60)
        print("Starting MCP server...")
        print("-" * 60)
        mcp_proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", MCP_MODULE,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
            env=BASE_ENV,
        )
        await mcp_initialize(mcp_proc)
        print("[OK] MCP server initialized\n")

        # ── 4. Test tools that don't need agent_id ──────────────────────────
        print("-" * 60)
        print("Testing custom tools (no agent_id needed)...")
        print("-" * 60)
        rid = 1
        for name, args, category, _ in CUSTOM_TOOL_TESTS:
            if category == "Simulation":
                args = {**args, "agent_id": agent_id, "agent_access_token": agent_access_token}
            try:
                resp = await mcp_call(mcp_proc, rid, name, args)
                rid += 1
                content = resp.get("result", {}).get("content", [])
                text = content[0].get("text", "") if content else ""
                text_lower = text.lower()
                is_err = "error" in text_lower[:200]
                status = "OK" if not is_err else "ERR"
                snippet = text[:150].replace("\n", " ").strip()
                print(f"  [{status}] {name}: {snippet}")
                if is_err:
                    all_ok = False
            except Exception as exc:
                print(f"  [FAIL] {name}: {exc}")
                all_ok = False
        print()

        # ── 5. Test tools with agent_id ─────────────────────────────────────
        print("-" * 60)
        print(f"Testing agent-dependent tools (agent_id={agent_id})...")
        print("-" * 60)
        for name, args_base, category in AGENT_TOOL_TESTS:
            args = {**args_base, "agent_id": agent_id, "agent_access_token": agent_access_token}
            try:
                resp = await mcp_call(mcp_proc, rid, name, args)
                rid += 1
                content = resp.get("result", {}).get("content", [])
                text = content[0].get("text", "") if content else ""
                text_lower = text.lower()
                is_err = "error" in text_lower[:200]
                if category == "Write" and any(expected in text_lower for expected in EXPECTED_LIVE_WRITE_ERRORS):
                    is_err = False
                status = "OK" if not is_err else "ERR"
                snippet = text[:150].replace("\n", " ").strip()
                print(f"  [{status}] {name}: {snippet}")
                if is_err:
                    all_ok = False
            except Exception as exc:
                print(f"  [FAIL] {name}: {exc}")
                all_ok = False
        print()

        # ── 6. Summary ────────────────────────────────────────────────────
        print("=" * 60)
        if all_ok:
            print("ALL CUSTOM TOOLS WORKED")
        else:
            print(f"SOME TESTS FAILED")
        print(f"Total custom tools tested: {len(CUSTOM_TOOL_TESTS) + len(AGENT_TOOL_TESTS)}")
        print(f"  Agent ID used: {agent_id}")
        print("=" * 60)

    finally:
        # Clean up
        for proc, name in [(mcp_proc, "MCP"), (api_proc, "API")]:
            if proc:
                try:
                    proc.stdin.close() if proc.stdin else None
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except Exception:
                    try:
                        proc.kill()
                        await proc.wait()
                    except Exception:
                        pass
                print(f"[Cleanup] {name} server stopped")
        # Remove shared temp DB
        try:
            import shutil
            shutil.rmtree(str(SHARED_DB_DIR), ignore_errors=True)
            print(f"[Cleanup] Temporary database removed")
        except Exception:
            pass

    return all_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

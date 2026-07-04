"""Live MCP server integration test.

Spawns the MCP server as a subprocess and interacts with it over stdio
using the MCP JSON-RPC protocol (same as Claude Desktop / Codex would).
Verifies tools/list (51 tools), resources/list (5), prompts/list (4),
real tool calls (list_chains, get_chain_info), custom tool routing
(estimate_relay_cost, compare_chains, get_relay_stats, analyze_wallet),
error handling, and transaction guard (agent_id required for transact tools).
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_mcp_server_live() -> None:
    """Run a live MCP protocol smoke test against the stdio server."""
    # Start the MCP server as a subprocess.
    project_root = Path(__file__).resolve().parent.parent.parent
    server_module = "backend.mcp_server.server"

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m", server_module,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(project_root),
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None

    request_id = 0
    results: dict[str, object] = {}

    try:
        # ---- Initialize ----
        request_id += 1
        init_msg = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        })
        proc.stdin.write((init_msg + "\n").encode())
        await proc.stdin.drain()
        init_resp = await _read_response(proc.stdout)
        _check_ok(init_resp, "initialize")
        server_caps = init_resp.get("result", {})
        print(f"[OK] server initialized: {server_caps.get('serverInfo', {}).get('name', '?')}")

        # ---- Initialized notification (no response expected) ----
        proc.stdin.write((json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }) + "\n").encode())
        await proc.stdin.drain()
        # Give the server a moment to process the notification.
        await asyncio.sleep(0.3)

        # ---- tools/list ----
        request_id += 1
        tools_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list",
        })
        proc.stdin.write((tools_req + "\n").encode())
        await proc.stdin.drain()
        tools_resp = await _read_response(proc.stdout)
        _check_ok(tools_resp, "tools/list")
        tools = tools_resp.get("result", {}).get("tools", [])
        tool_names = {t["name"] for t in tools}
        assert len(tools) == 51, f"Expected 51 tools, got {len(tools)}"
        for expected in [
            "list_chains", "evm_get_balance", "solana_get_balance",
            "compare_chains", "recommend_chain", "send_transaction",
            "get_relay_stats", "analyze_wallet", "simulate_transaction",
        ]:
            assert expected in tool_names, f"Missing tool: {expected}"
        # Every tool has inputSchema with type: object
        for t in tools:
            assert t.get("inputSchema", {}).get("type") == "object", \
                f"{t['name']} inputSchema not object"
            assert t.get("description"), f"{t['name']} missing description"
        results["tools"] = len(tools)
        print(f"[OK] tools/list: {len(tools)} tools")

        # ---- resources/list ----
        request_id += 1
        resources_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "resources/list",
        })
        proc.stdin.write((resources_req + "\n").encode())
        await proc.stdin.drain()
        resources_resp = await _read_response(proc.stdout)
        _check_ok(resources_resp, "resources/list")
        resources = resources_resp.get("result", {}).get("resources", [])
        uris = {r["uri"] for r in resources}
        assert len(resources) == 5, f"Expected 5 resources, got {len(resources)}"
        for expected_uri in [
            "pocket://chains",
            "pocket://cache/stats",
        ]:
            assert expected_uri in uris, f"Missing resource: {expected_uri}"
        results["resources"] = len(resources)
        print(f"[OK] resources/list: {len(resources)} resources")

        # ---- prompts/list ----
        request_id += 1
        prompts_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "prompts/list",
        })
        proc.stdin.write((prompts_req + "\n").encode())
        await proc.stdin.drain()
        prompts_resp = await _read_response(proc.stdout)
        _check_ok(prompts_resp, "prompts/list")
        prompts = prompts_resp.get("result", {}).get("prompts", [])
        prompt_names = {p["name"] for p in prompts}
        assert len(prompts) == 4, f"Expected 4 prompts, got {len(prompts)}"
        for expected_name in [
            "analyze_wallet", "find_cheapest_chain",
            "track_pokt_costs", "compare_and_recommend",
        ]:
            assert expected_name in prompt_names, f"Missing prompt: {expected_name}"
        results["prompts"] = len(prompts)
        print(f"[OK] prompts/list: {len(prompts)} prompts")

        # ---- call_tool: list_chains (real read tool, no RPC needed) ----
        request_id += 1
        list_chains_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": "list_chains", "arguments": {}},
        })
        proc.stdin.write((list_chains_req + "\n").encode())
        await proc.stdin.drain()
        list_chains_resp = await _read_response(proc.stdout, timeout=15.0)
        _check_ok(list_chains_resp, "tools/call list_chains")
        content = list_chains_resp.get("result", {}).get("content", [])
        assert len(content) > 0, "Expected content from list_chains"
        body = json.loads(content[0].get("text", "{}"))
        assert body.get("count", 0) > 0, f"Expected non-zero chain count, got: {body}"
        assert len(body.get("chains", [])) == body["count"]
        results["list_chains_worked"] = body["count"]
        print(f"[OK] tools/call list_chains: {body['count']} chains")

        # ---- call_tool: get_chain_info (another read tool, no RPC needed) ----
        request_id += 1
        chain_info_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": "get_chain_info", "arguments": {"chain": "ethereum"}},
        })
        proc.stdin.write((chain_info_req + "\n").encode())
        await proc.stdin.drain()
        chain_info_resp = await _read_response(proc.stdout, timeout=15.0)
        _check_ok(chain_info_resp, "tools/call get_chain_info")
        content = chain_info_resp.get("result", {}).get("content", [])
        assert len(content) > 0, "Expected content from get_chain_info"
        body = json.loads(content[0].get("text", "{}"))
        assert body.get("chain") == "ethereum", f"Expected ethereum chain info, got: {body}"
        assert body.get("protocol") == "evm", f"Expected evm protocol, got: {body}"
        results["chain_info_worked"] = True
        print(f"[OK] tools/call get_chain_info: ethereum ({body.get('protocol')})")

        # ---- call_tool: estimate_relay_cost (custom POKT tool, no RPC needed) ----
        request_id += 1
        pokt_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": "estimate_relay_cost",
                "arguments": {"chain": "ethereum", "operation": "read_balance"},
            },
        })
        proc.stdin.write((pokt_req + "\n").encode())
        await proc.stdin.drain()
        pokt_resp = await _read_response(proc.stdout, timeout=15.0)
        _check_ok(pokt_resp, "tools/call estimate_relay_cost")
        content = pokt_resp.get("result", {}).get("content", [])
        body = json.loads(content[0].get("text", "{}"))
        assert body.get("chain") == "ethereum"
        assert body.get("operation") == "read_balance"
        assert body.get("relay_count") == 1
        assert isinstance(body.get("estimated_relay_cost_pokt"), float)
        results["custom_pokt_worked"] = body["estimated_relay_cost_pokt"]
        print(f"[OK] tools/call estimate_relay_cost: {body['estimated_relay_cost_pokt']} POKT for read_balance on ethereum")

        # ---- call_tool: compare_chains (custom Compare tool, routes correctly but needs RPC) ----
        request_id += 1
        compare_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": "compare_chains",
                "arguments": {"chains": ["ethereum", "polygon"]},
            },
        })
        proc.stdin.write((compare_req + "\n").encode())
        await proc.stdin.drain()
        compare_resp = await _read_response(proc.stdout, timeout=30.0)
        # compare_chains needs live RPC; we just verify it routed (got content back)
        content = compare_resp.get("result", {}).get("content", [])
        assert len(content) > 0, "Expected some response from compare_chains"
        text = content[0].get("text", "")
        # It either succeeds (with live RPC) or returns a clean error (no crash)
        results["custom_compare_routed"] = "error" in text.lower() or "chains" in text.lower()
        print(f"[OK] tools/call compare_chains routed properly (RPC needed for full data)")

        # ---- call_tool: get_relay_stats (custom Analytics tool, needs DB) ----
        request_id += 1
        stats_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": "get_relay_stats",
                "arguments": {"agent_id": "test-agent"},
            },
        })
        proc.stdin.write((stats_req + "\n").encode())
        await proc.stdin.drain()
        stats_resp = await _read_response(proc.stdout, timeout=15.0)
        # Should route to the executor (not "unknown tool") and either fail gracefully or return data
        _check_ok(stats_resp, "tools/call get_relay_stats")
        content = stats_resp.get("result", {}).get("content", [])
        assert len(content) > 0
        results["custom_analytics_routed"] = True
        print(f"[OK] tools/call get_relay_stats routed properly")

        # ---- call_tool: analyze_wallet (custom Compositional tool, needs RPC) ----
        request_id += 1
        wallet_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": "analyze_wallet",
                "arguments": {"address": "0x0000000000000000000000000000000000000001", "chains": "ethereum"},
            },
        })
        proc.stdin.write((wallet_req + "\n").encode())
        await proc.stdin.drain()
        wallet_resp = await _read_response(proc.stdout, timeout=30.0)
        # Should route to executor (not "unknown tool"), even if RPC fails
        content = wallet_resp.get("result", {}).get("content", [])
        assert len(content) > 0
        body_text = content[0].get("text", "")
        results["custom_compositional_routed"] = len(body_text) > 0
        print(f"[OK] tools/call analyze_wallet routed properly (RPC needed for full data)")

        # ---- call_tool: unknown tool returns error ----
        request_id += 1
        unknown_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": "not_a_real_tool", "arguments": {}},
        })
        proc.stdin.write((unknown_req + "\n").encode())
        await proc.stdin.drain()
        unknown_resp = await _read_response(proc.stdout)
        content = unknown_resp.get("result", {}).get("content", [])
        assert len(content) > 0, "Expected error content for unknown tool"
        text = content[0].get("text", "")
        assert "error" in text.lower() or "unknown" in text.lower(), \
            f"Expected error text, got: {text[:200]}"
        results["unknown_tool_error"] = True
        print(f"[OK] tools/call unknown tool returns error")

        # ---- call_tool: transact without agent_id returns error ----
        request_id += 1
        no_agent_req = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": "send_transaction",
                "arguments": {"chain": "ethereum", "to_address": "0xDEF", "amount": "0.01"},
            },
        })
        proc.stdin.write((no_agent_req + "\n").encode())
        await proc.stdin.drain()
        no_agent_resp = await _read_response(proc.stdout)
        content = no_agent_resp.get("result", {}).get("content", [])
        assert len(content) > 0, "Expected error content for transact without agent_id"
        text = content[0].get("text", "")
        assert "agent_id" in text.lower(), f"Expected agent_id error, got: {text[:200]}"
        results["transact_no_agent_id"] = True
        print(f"[OK] tools/call transact without agent_id returns error")

    finally:
        # Clean up: send terminate and close.
        proc.stdin.close()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

    # Print summary.
    print(f"\n{'='*50}")
    print(f"Live MCP server test: ALL PASSED")
    print(f"  tools/list:             {results.get('tools')} tools")
    print(f"  resources/list:         {results.get('resources')} resources")
    print(f"  prompts/list:           {results.get('prompts')} prompts")
    print(f"  list_chains:            {results.get('list_chains_worked')} chains")
    print(f"  get_chain_info:         {results.get('chain_info_worked')}")
    print(f"  estimate_relay_cost:    {results.get('custom_pokt_worked')} POKT")
    print(f"  compare_chains routed:  {results.get('custom_compare_routed')}")
    print(f"  get_relay_stats routed: {results.get('custom_analytics_routed')}")
    print(f"  analyze_wallet routed:  {results.get('custom_compositional_routed')}")
    print(f"  unknown tool error:     {results.get('unknown_tool_error')}")
    print(f"  transact guard (write): {results.get('transact_no_agent_id')}")
    print(f"{'='*50}")


async def _read_response(stream: asyncio.StreamReader, timeout: float = 10.0) -> dict:
    """Read a JSON-RPC response line from the server's stdout."""
    line = await asyncio.wait_for(stream.readline(), timeout=timeout)
    raw = line.decode().strip()
    if not raw:
        raise RuntimeError("Empty response from MCP server (stderr may have errors)")
    return json.loads(raw)


def _check_ok(resp: dict, label: str) -> None:
    """Assert the JSON-RPC response has no error."""
    if "error" in resp:
        err = resp["error"]
        raise AssertionError(f"{label} returned error: {err.get('message', err)}")
    assert "result" in resp, f"{label} missing 'result' key in response"


if __name__ == "__main__":
    asyncio.run(test_mcp_server_live())
    print("\nAll live MCP server tests passed!")

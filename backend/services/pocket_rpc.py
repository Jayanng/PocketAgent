from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any

import httpx

try:
    from ..config import get_settings
    from .cache import ResponseCache
    from .chain_registry import CHAIN_REGISTRY, canonical_chain, get_chain_metadata
    from .output_formatter import HumanReadableFormatter
    from .price_feed import PriceFeedService
    from .relay_tracker import RelayTrackerService
except ImportError:
    from config import get_settings
    from services.cache import ResponseCache
    from services.chain_registry import CHAIN_REGISTRY, canonical_chain, get_chain_metadata
    from services.output_formatter import HumanReadableFormatter
    from services.price_feed import PriceFeedService
    from services.relay_tracker import RelayTrackerService

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Shared httpx pool for Pocket RPC + REST traffic
# -----------------------------------------------------------------------------
# Reusing one httpx.AsyncClient across requests keeps the underlying TCP/TLS
# sessions warm (DNS cached, TLS session reused, sockets kept alive). Without
# this, every tool call re-opens a fresh handshake to *.api.pocket.network —
# adding 150-300 ms of latency per relay from a trans-Atlantic Fly region to
# Pocket's US-hosted gateways. The shared client is pre-warmed by the FastAPI
# lifespan handler so the very first chat turn after a cold start still pays
# the handshake cost only once per host, not once per call.
_shared_rpc_http_client: httpx.AsyncClient | None = None
_rpc_http_pool_lock = asyncio.Lock()


async def ensure_pocket_rpc_pool() -> None:
    """Eagerly build the module-shared httpx.AsyncClient used by every Pocket
    RPC + REST call. Idempotent. Called from the FastAPI lifespan in main.py."""
    global _shared_rpc_http_client
    if _shared_rpc_http_client is not None:
        return
    async with _rpc_http_pool_lock:
        if _shared_rpc_http_client is not None:
            return
        _shared_rpc_http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
                keepalive_expiry=60.0,
            ),
            headers={"User-Agent": "pocketagent/1.0"},
        )
        logger.info("Pocket RPC httpx pool warmed (max_connections=50, keepalive=20)")


async def close_pocket_rpc_pool() -> None:
    """Close the module-shared httpx.AsyncClient. Called from the FastAPI
    lifespan shutdown so we never leave a connection pool open on app exit."""
    global _shared_rpc_http_client
    if _shared_rpc_http_client is None:
        return
    client = _shared_rpc_http_client
    _shared_rpc_http_client = None
    await client.aclose()


# balanceOf(address) ERC-20 selector + zero-padded 32-byte address argument.
_BALANCE_OF_SELECTOR = "70a08231"


def _encode_balance_of(address: str) -> str:
    clean = address.removeprefix("0x").lower()
    return f"{_BALANCE_OF_SELECTOR}{clean.rjust(64, '0')}"


# Small curated ERC-20 token list per chain for MVP token discovery. The Pocket
# public RPC exposes no native ERC-20 enumeration, so we probe a known set of
# high-liquidity tokens via balanceOf. Extend as needed.
_COMMON_ERC20: dict[str, list[dict[str, Any]]] = {
    "ethereum": [
        {"symbol": "USDC", "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6, "coingecko_id": "usd-coin"},
        {"symbol": "USDT", "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "decimals": 6, "coingecko_id": "tether"},
        {"symbol": "LINK", "address": "0x514910771AF9Ca656af840dff83E8264EcF986CA", "decimals": 18, "coingecko_id": "chainlink"},
        {"symbol": "UNI", "address": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", "decimals": 18, "coingecko_id": "uniswap"},
    ],
    "polygon": [
        {"symbol": "USDC", "address": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "decimals": 6, "coingecko_id": "usd-coin"},
        {"symbol": "USDT", "address": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", "decimals": 6, "coingecko_id": "tether"},
    ],
    "arbitrum": [
        {"symbol": "USDC", "address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "decimals": 6, "coingecko_id": "usd-coin"},
        {"symbol": "ARB", "address": "0x912CE59144191C1204E64559FE8253a0e49E6548", "decimals": 18, "coingecko_id": "arbitrum"},
    ],
    "base": [
        {"symbol": "USDC", "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6, "coingecko_id": "usd-coin"},
    ],
    "bsc": [
        {"symbol": "USDT", "address": "0x55d398326f99059fF775485246999027B3197955", "decimals": 18, "coingecko_id": "tether"},
        {"symbol": "USDC", "address": "0x8AC76A51cc950d9822D68b83fE1Ad97B32Cd580d", "decimals": 18, "coingecko_id": "usd-coin"},
    ],
}


class PocketRPCClient:
    """Pocket Network RPC client with cache, backoff, and protocol dispatch."""

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.chain_registry = CHAIN_REGISTRY
        self.rpc_urls = {chain: metadata["url"] for chain, metadata in self.chain_registry.items()}
        self.cache = ResponseCache(
            ttl_balance=settings.cache_ttl_balance,
            ttl_gas=settings.cache_ttl_gas,
            ttl_health=60,
            pokt_per_relay=settings.notional_pokt_per_relay,
        )
        self.price_feed = PriceFeedService()
        self.formatter = HumanReadableFormatter(self.price_feed)
        self.relay_tracker = RelayTrackerService()
        self.timeout = 30.0
        self.rate_limit_per_second = 30
        self._rate_windows: dict[str, deque[float]] = {chain: deque() for chain in self.rpc_urls}
        self._rate_locks: dict[str, asyncio.Lock] = {chain: asyncio.Lock() for chain in self.rpc_urls}

    @staticmethod
    def _canonical_chain(chain: str) -> str:
        return canonical_chain(chain)

    def get_protocol(self, chain: str) -> str:
        metadata = get_chain_metadata(chain)
        return metadata["protocol"]

    def get_metadata(self, chain: str) -> dict[str, Any]:
        return dict(get_chain_metadata(chain))

    async def _enforce_rate_limit(self, chain: str) -> None:
        lock = self._rate_locks[chain]
        window = self._rate_windows[chain]
        while True:
            async with lock:
                now = time.perf_counter()
                while window and now - window[0] >= 1.0:
                    window.popleft()
                if len(window) < self.rate_limit_per_second:
                    window.append(now)
                    return
                wait_seconds = max(1.0 - (now - window[0]), 0.01)
            await asyncio.sleep(wait_seconds)

    async def call(self, chain: str, method: str, params: list[Any] | None = None) -> Any:
        chain = self._canonical_chain(chain)
        params = params or []
        protocol = self.get_protocol(chain)

        if method == "eth_subscribe":
            raise ValueError(
                "eth_subscribe is not supported on Pocket public endpoints; use polling via eth_blockNumber or eth_getTransactionReceipt."
            )

        cached = self.cache.get(chain, method, params)
        if cached is not None:
            return cached

        await self._enforce_rate_limit(chain)
        if protocol == "evm":
            result = await self._call_evm(chain, method, params)
        elif protocol == "solana":
            result = await self._call_solana(chain, method, params)
        elif protocol == "sui":
            result = await self._call_sui(chain, method, params)
        elif protocol == "near":
            result = await self._call_near(chain, method, params)
        elif protocol == "tron":
            result = await self._call_tron(chain, method, params)
        elif protocol == "cosmos":
            result = await self._call_cosmos(chain, method, params)
        else:
            raise ValueError(f"Unsupported protocol for chain {chain}: {protocol}")

        self.cache.set(chain, method, params, result)
        return result

    async def call_with_backoff(self, url: str, payload: dict[str, Any], max_retries: int = 3) -> dict[str, Any]:
        return await self._request_with_backoff("POST", url, json_payload=payload, max_retries=max_retries)

    async def _request_with_backoff(
        self,
        http_method: str,
        url: str,
        *,
        json_payload: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        # Reuse the module-shared httpx pool when it's been pre-warmed by the
        # FastAPI lifespan handler — TCP + TLS sessions stay alive across all
        # chat turns, so only the FIRST call per (host, port) pays the
        # handshake. In code paths that bypass the lifespan (tests, CLI
        # executables), fall back to a short-lived client that's cleaned up
        # on return so we don't leak sockets.
        if _shared_rpc_http_client is not None:
            client = _shared_rpc_http_client
            owns_client = False
        else:
            client = httpx.AsyncClient(timeout=self.timeout)
            owns_client = True
        try:
            return await self._perform_request_with_retries(
                client,
                http_method,
                url,
                json_payload=json_payload,
                query_params=query_params,
                max_retries=max_retries,
            )
        finally:
            if owns_client:
                await client.aclose()

    async def _perform_request_with_retries(
        self,
        client: httpx.AsyncClient,
        http_method: str,
        url: str,
        *,
        json_payload: dict[str, Any] | None,
        query_params: dict[str, Any] | None,
        max_retries: int,
    ) -> dict[str, Any]:
        last_response: httpx.Response | None = None
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = await client.request(
                    http_method,
                    url,
                    json=json_payload,
                    params=query_params,
                )
                last_response = response
                if response.status_code in {408, 429, 503} and attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
                if 500 <= response.status_code < 600 and attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
                response.raise_for_status()
                # The body must be valid JSON. Pocket gateways occasionally answer
                # with an empty or plain-text/HTML error page (e.g. a 404 "No proxy
                # rule for this subdomain") instead of a JSON-RPC envelope. Parsing
                # such a body with response.json() raises a bare json.JSONDecodeError
                # ("Expecting value: line 1 column 1 (char 0)") that can escape the
                # retry loop and crash the calling tool / MCP server. Decode
                # explicitly and convert any failure into a structured RuntimeError
                # so execute_tool can degrade it into an {"available": false, ...}
                # result instead of throwing.
                if not response.content:
                    raise RuntimeError("Pocket RPC returned an empty response body.")
                try:
                    data = response.json()
                except ValueError as exc:
                    body = response.text.strip()
                    raise RuntimeError(
                        f"Pocket RPC returned a non-JSON response: "
                        f"{body[:200] or '<empty body>'}"
                    ) from exc
                if isinstance(data, dict) and "error" in data:
                    raise RuntimeError(f"RPC error: {data['error']}")
                if not isinstance(data, dict):
                    return {"result": data}
                return data
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt >= max_retries:
                    break
                await asyncio.sleep(2**attempt)

        status = last_response.status_code if last_response is not None else "request_error"
        detail = f" ({last_error})" if last_error is not None else ""
        raise RuntimeError(f"Pocket RPC request failed after retries (status={status}){detail}")

    async def call_with_failover(self, chain: str, payload: dict[str, Any]) -> Any:
        chain = self._canonical_chain(chain)
        return await self._logged_json_rpc_call(chain, payload)

    async def _logged_json_rpc_call(self, chain: str, payload: dict[str, Any]) -> Any:
        url = self.rpc_urls[chain]
        start = time.perf_counter()
        status = 500
        try:
            data = await self.call_with_backoff(url, payload)
            status = 200
            return data.get("result")
        finally:
            await self._log_relay(chain, payload.get("method", "unknown"), payload, status, start)

    async def _logged_rest_call(
        self,
        chain: str,
        method: str,
        path: str,
        *,
        http_method: str = "GET",
        json_payload: dict[str, Any] | None = None,
    ) -> Any:
        base_url = self.rpc_urls[chain].rstrip("/")
        url = f"{base_url}/{path.lstrip('/')}"
        start = time.perf_counter()
        status = 500
        try:
            data = await self._request_with_backoff(http_method, url, json_payload=json_payload)
            status = 200
            return data
        finally:
            await self._log_relay(chain, method, json_payload or {"path": path}, status, start)

    async def _log_relay(
        self,
        chain: str,
        method: str,
        request_payload: dict[str, Any],
        response_status: int,
        start: float,
    ) -> None:
        latency_ms = int((time.perf_counter() - start) * 1000)
        await self.relay_tracker.log_relay(
            chain=chain,
            method=method,
            request_payload=request_payload,
            response_status=response_status,
            latency_ms=latency_ms,
        )

    async def _call_evm(self, chain: str, method: str, params: list[Any] | None = None) -> Any:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        return await self._logged_json_rpc_call(chain, payload)

    async def _call_solana(self, chain: str, method: str, params: list[Any] | None = None) -> Any:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        return await self._logged_json_rpc_call(chain, payload)

    async def _call_sui(self, chain: str, method: str, params: list[Any] | None = None) -> Any:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        return await self._logged_json_rpc_call(chain, payload)

    async def _call_near(self, chain: str, method: str, params: list[Any] | None = None) -> Any:
        rpc_params: Any = params or []
        if method in {"block", "query"} and len(rpc_params) == 1 and isinstance(rpc_params[0], dict):
            rpc_params = rpc_params[0]
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": rpc_params}
        return await self._logged_json_rpc_call(chain, payload)

    async def _call_tron(self, chain: str, method: str, params: list[Any] | None = None) -> Any:
        if method.startswith("wallet/"):
            payload = params[0] if params else {}
            return await self._logged_rest_call(chain, method, method, http_method="POST", json_payload=payload)
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        return await self._logged_json_rpc_call(chain, payload)

    async def _call_cosmos(self, chain: str, method: str, params: list[Any] | None = None) -> Any:
        if method.startswith("/"):
            return await self._logged_rest_call(chain, method, method)
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        return await self._logged_json_rpc_call(chain, payload)

    @classmethod
    def startup_note(cls) -> str:
        return (
            "No API key required - using Pocket Network public RPC endpoints "
            "({chain-slug}.api.pocket.network) with local request throttling. "
            "POKT costs are notional estimates, not user charges."
        )

    async def get_balance(self, chain: str, address: str) -> dict[str, Any]:
        chain = self._canonical_chain(chain)
        protocol = self.get_protocol(chain)
        if protocol == "evm":
            raw = await self.call(chain, "eth_getBalance", [address, "latest"])
            return await self.formatter.enrich_balance(raw, chain, protocol)
        if protocol == "solana":
            result = await self.call(chain, "getBalance", [address])
            lamports = result.get("value", 0) if isinstance(result, dict) else result
            return await self.formatter.enrich_balance(lamports, chain, protocol)
        if protocol == "sui":
            result = await self.call(chain, "suix_getBalance", [address])
            total = result.get("totalBalance", 0) if isinstance(result, dict) else result
            return await self.formatter.enrich_balance(total, chain, protocol)
        if protocol == "near":
            result = await self.call(
                chain,
                "query",
                [{"request_type": "view_account", "finality": "final", "account_id": address}],
            )
            amount = result.get("amount", 0) if isinstance(result, dict) else result
            return await self.formatter.enrich_balance(amount, chain, protocol)
        if protocol == "tron":
            result = await self.call(chain, "wallet/getaccount", [{"address": address, "visible": True}])
            balance = result.get("balance", 0) if isinstance(result, dict) else 0
            return await self.formatter.enrich_balance(balance, chain, protocol)
        if protocol == "cosmos":
            metadata = get_chain_metadata(chain)
            path = f"/cosmos/bank/v1beta1/balances/{address}/by_denom?denom={metadata['cosmos_denom']}"
            result = await self.call(chain, path, [])
            balance = result.get("balance", {}) if isinstance(result, dict) else {}
            amount = balance.get("amount", 0) if isinstance(balance, dict) else 0
            return await self.formatter.enrich_balance(amount, chain, protocol)
        raise ValueError(f"Unsupported protocol for balance: {protocol}")

    async def get_gas_price(self, chain: str) -> dict[str, Any]:
        chain = self._canonical_chain(chain)
        protocol = self.get_protocol(chain)
        if protocol != "evm":
            return await self._get_non_evm_fee_hint(chain, protocol)

        gas_hex = await self.call(chain, "eth_gasPrice", [])
        block = await self.call(chain, "eth_getBlockByNumber", ["latest", False])
        gas_price_wei = int(gas_hex, 16) if isinstance(gas_hex, str) else int(gas_hex or 0)
        base_fee_wei = int(str(block.get("baseFeePerGas", "0x0")), 16) if isinstance(block, dict) else 0
        priority_wei = max(gas_price_wei - base_fee_wei, 0)

        metadata = get_chain_metadata(chain)
        symbol = metadata["symbol"]
        gas_price_gwei = gas_price_wei / 10**9
        base_fee_gwei = base_fee_wei / 10**9
        priority_gwei = priority_wei / 10**9

        transfer_native = (21_000 * gas_price_wei) / 10**18
        erc20_native = (42_000 * gas_price_wei) / 10**18
        transfer_usd = (await self.price_feed.get_usd_value(transfer_native, symbol))["usd"]
        erc20_usd = (await self.price_feed.get_usd_value(erc20_native, symbol))["usd"]

        return {
            "gas_price_gwei": round(gas_price_gwei, 4),
            "base_fee_gwei": round(base_fee_gwei, 4),
            "suggested_priority_gwei": round(priority_gwei, 4),
            "estimated_cost": {
                "transfer_eth": f"{transfer_native:.6f} {symbol}",
                "transfer_usd": self._usd_label(transfer_usd),
                "erc20_transfer": f"{erc20_native:.6f} {symbol}",
                "erc20_transfer_usd": self._usd_label(erc20_usd),
            },
            "chain": chain,
            "protocol": protocol,
        }

    async def _get_non_evm_fee_hint(self, chain: str, protocol: str) -> dict[str, Any]:
        metadata = get_chain_metadata(chain)
        decimals = int(metadata["decimals"])
        symbol = metadata["symbol"]
        if protocol == "sui":
            reference = await self.call(chain, "suix_getReferenceGasPrice", [])
            reference_int = int(reference)
            computation_units = 1_000
            estimated_native = reference_int * computation_units / 10**decimals
            estimated_usd = (await self.price_feed.get_usd_value(estimated_native, symbol))["usd"]
            return {
                "chain": chain,
                "protocol": protocol,
                "fee_source": "suix_getReferenceGasPrice",
                "reference_gas_price": reference_int,
                "estimated_native_fee": estimated_native,
                "estimated_cost": {
                    "transfer_native": f"{estimated_native:.9f} {symbol}",
                    "transfer_usd": self._usd_label(estimated_usd),
                },
            }
        if protocol == "solana":
            try:
                fees = await self.call(chain, "getRecentPrioritizationFees", [])
            except Exception:
                fees = []
            prioritization_lamports = 0.0
            if isinstance(fees, list) and fees:
                values = sorted(float(item.get("prioritizationFee", 0)) for item in fees if isinstance(item, dict))
                prioritization_lamports = values[len(values) // 2] / 1_000_000 if values else 0.0
            signature_lamports = 5_000
            estimated_native = (signature_lamports + prioritization_lamports) / 10**decimals
            estimated_usd = (await self.price_feed.get_usd_value(estimated_native, symbol))["usd"]
            return {
                "chain": chain,
                "protocol": protocol,
                "fee_source": "getRecentPrioritizationFees",
                "estimated_native_fee": estimated_native,
                "estimated_cost": {
                    "transfer_native": f"{estimated_native:.9f} {symbol}",
                    "transfer_usd": self._usd_label(estimated_usd),
                },
            }
        if protocol == "near":
            result = await self.call(chain, "gas_price", [None])
            gas_price = int(result.get("gas_price", result) if isinstance(result, dict) else result)
            gas_units = 300_000_000_000
            estimated_native = gas_price * gas_units / 10**decimals
            estimated_usd = (await self.price_feed.get_usd_value(estimated_native, symbol))["usd"]
            return {
                "chain": chain,
                "protocol": protocol,
                "fee_source": "gas_price",
                "estimated_native_fee": estimated_native,
                "estimated_cost": {
                    "transfer_native": f"{estimated_native:.9f} {symbol}",
                    "transfer_usd": self._usd_label(estimated_usd),
                },
            }
        if protocol == "tron":
            params = await self.call(chain, "wallet/getchainparameters", [{}])
            chain_parameters = params.get("chainParameter", []) if isinstance(params, dict) else []
            fee_limit_sun = 1_000_000
            for item in chain_parameters:
                if isinstance(item, dict) and item.get("key") in {"getTransactionFee", "getEnergyFee"}:
                    fee_limit_sun = max(fee_limit_sun, int(item.get("value") or 0))
            estimated_native = fee_limit_sun / 10**decimals
            estimated_usd = (await self.price_feed.get_usd_value(estimated_native, symbol))["usd"]
            return {
                "chain": chain,
                "protocol": protocol,
                "fee_source": "wallet/getchainparameters",
                "estimated_native_fee": estimated_native,
                "estimated_cost": {
                    "transfer_native": f"{estimated_native:.6f} {symbol}",
                    "transfer_usd": self._usd_label(estimated_usd),
                },
            }
        if protocol == "cosmos":
            estimated_native = 250_000 * 0.025 / 10**decimals
            estimated_usd = (await self.price_feed.get_usd_value(estimated_native, symbol))["usd"]
            return {
                "chain": chain,
                "protocol": protocol,
                "fee_source": "cosmos-sdk-default-gas-price",
                "estimated_native_fee": estimated_native,
                "estimated_cost": {
                    "transfer_native": f"{estimated_native:.9f} {symbol}",
                    "transfer_usd": self._usd_label(estimated_usd),
                },
            }
        return {"chain": chain, "protocol": protocol, "fee_model": "protocol-specific"}

    @staticmethod
    def _usd_label(value: float | str | None) -> str:
        if value is None:
            return "USD unavailable"
        return f"${float(value):,.2f}"

    async def get_block_number(self, chain: str) -> int:
        chain = self._canonical_chain(chain)
        protocol = self.get_protocol(chain)
        if protocol == "evm":
            block_hex = await self.call(chain, "eth_blockNumber", [])
            return int(block_hex, 16) if isinstance(block_hex, str) else int(block_hex)
        if protocol == "solana":
            return int(await self.call(chain, "getSlot", []))
        if protocol == "sui":
            checkpoint = await self.call(chain, "sui_getLatestCheckpointSequenceNumber", [])
            return int(checkpoint)
        if protocol == "near":
            block = await self.call(chain, "block", [{"finality": "final"}])
            return int(block.get("header", {}).get("height", 0))
        if protocol == "tron":
            block = await self.call(chain, "wallet/getnowblock", [{}])
            return int(block.get("block_header", {}).get("raw_data", {}).get("number", 0))
        if protocol == "cosmos":
            block = await self.call(chain, "/cosmos/base/tendermint/v1beta1/blocks/latest", [])
            header = block.get("block", {}).get("header", {}) if isinstance(block, dict) else {}
            return int(header.get("height", 0))
        raise ValueError(f"Block number is not implemented for protocol: {protocol}")

    async def get_transaction_count(self, chain: str, address: str) -> int:
        chain = self._canonical_chain(chain)
        if self.get_protocol(chain) != "evm":
            raise ValueError("Transaction count/nonce is EVM-specific in this client.")
        nonce_hex = await self.call(chain, "eth_getTransactionCount", [address, "latest"])
        return int(nonce_hex, 16) if isinstance(nonce_hex, str) else int(nonce_hex)

    async def get_chain_id(self, chain: str) -> int | str:
        chain = self._canonical_chain(chain)
        protocol = self.get_protocol(chain)
        if protocol == "evm":
            chain_id_hex = await self.call(chain, "eth_chainId", [])
            return int(chain_id_hex, 16) if isinstance(chain_id_hex, str) else int(chain_id_hex)
        return get_chain_metadata(chain)["chain_id"]

    async def estimate_gas(self, chain: str, tx: dict[str, Any]) -> dict[str, Any]:
        chain = self._canonical_chain(chain)
        if self.get_protocol(chain) != "evm":
            return {"chain": chain, "protocol": self.get_protocol(chain), "message": "Use protocol-specific fee estimation."}
        gas_hex = await self.call(chain, "eth_estimateGas", [tx])
        gas_units = int(gas_hex, 16) if isinstance(gas_hex, str) else int(gas_hex)
        gas = await self.get_gas_price(chain)
        gas_price_wei = int(float(gas["gas_price_gwei"]) * 10**9)
        total_native = (gas_units * gas_price_wei) / 10**18
        symbol = get_chain_metadata(chain)["symbol"]
        total_usd = (await self.price_feed.get_usd_value(total_native, symbol))["usd"]
        return {
            "gas_units": gas_units,
            "gas_price_gwei": gas["gas_price_gwei"],
            "total_cost_eth": f"{total_native:.6f}",
            "total_cost_usd": self._usd_label(total_usd),
            "chain": chain,
        }

    async def send_raw_transaction(self, chain: str, raw_tx: str) -> str:
        chain = self._canonical_chain(chain)
        if self.get_protocol(chain) != "evm":
            raise ValueError("send_raw_transaction currently supports EVM chains only.")
        if not raw_tx.startswith("0x"):
            raw_tx = f"0x{raw_tx}"
        tx_hash = await self.call(chain, "eth_sendRawTransaction", [raw_tx])
        if not isinstance(tx_hash, str):
            raise RuntimeError("Unexpected eth_sendRawTransaction response")
        return tx_hash

    async def get_transaction_receipt(self, chain: str, tx_hash: str) -> dict[str, Any] | None:
        chain = self._canonical_chain(chain)
        if self.get_protocol(chain) != "evm":
            raise ValueError("get_transaction_receipt currently supports EVM chains only.")
        receipt = await self.call(chain, "eth_getTransactionReceipt", [tx_hash])
        if receipt is None:
            return None
        if not isinstance(receipt, dict):
            raise RuntimeError("Unexpected eth_getTransactionReceipt response")
        return receipt

    async def multi_chain_balance(self, address: str, chains: list[str]) -> dict[str, Any]:
        tasks = [self.get_balance(chain, address) for chain in chains]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        balances: dict[str, Any] = {}
        for chain, result in zip(chains, results, strict=False):
            canonical = self._canonical_chain(chain)
            if isinstance(result, Exception):
                balances[canonical] = {"error": str(result)}
            else:
                balances[canonical] = result
        return {"address": address, "balances": balances}

    async def discover_tokens(self, chain: str, address: str) -> list[dict[str, Any]]:
        """Discover non-native token balances held by an address.

        Per-protocol strategy:
          - EVM:      query a small curated list of common ERC-20s via balanceOf.
          - Solana:   getTokenAccountsByOwner (true SPL discovery).
          - Cosmos:   /cosmos/bank/v1beta1/balances/{address} (all denoms).
          - Sui:      suix_getAllBalances (all coin types).
          - Near/Tron: deferred in MVP (no cheap discovery path via public RPC).
        Each entry: {symbol, contract, balance_formatted, amount_decimal, usd_value?}.
        """
        chain = self._canonical_chain(chain)
        protocol = self.get_protocol(chain)
        try:
            if protocol == "evm":
                return await self._discover_evm_tokens(chain, address)
            if protocol == "solana":
                return await self._discover_solana_tokens(chain, address)
            if protocol == "cosmos":
                return await self._discover_cosmos_tokens(chain, address)
            if protocol == "sui":
                return await self._discover_sui_tokens(chain, address)
        except Exception as exc:  # token discovery is best-effort; never break the analysis
            logger.warning("Token discovery failed for %s: %s", chain, exc)
            return []
        return []

    async def _discover_evm_tokens(self, chain: str, address: str) -> list[dict[str, Any]]:
        metadata = get_chain_metadata(chain)
        curated = _COMMON_ERC20.get(chain, [])
        results: list[dict[str, Any]] = []
        for token in curated:
            balance_of_call = _encode_balance_of(address)
            raw = await self.call(
                chain,
                "eth_call",
                [{"to": token["address"], "data": f"0x{balance_of_call}"}, "latest"],
            )
            try:
                units = int(raw, 16) if isinstance(raw, str) else int(raw)
            except (TypeError, ValueError):
                continue
            if units <= 0:
                continue
            decimals = int(token.get("decimals", 6))
            amount_decimal = units / 10**decimals
            usd_value = None
            price = await self.price_feed.get_price(token.get("coingecko_id", ""))
            if price is not None:
                usd_value = round(amount_decimal * price, 2)
            results.append(
                {
                    "symbol": token["symbol"],
                    "contract": token["address"],
                    "balance_formatted": f"{amount_decimal:.6f} {token['symbol']}".rstrip("0").rstrip(),
                    "amount_decimal": amount_decimal,
                    "usd_value": usd_value,
                }
            )
        return results

    async def _discover_solana_tokens(self, chain: str, address: str) -> list[dict[str, Any]]:
        accounts = await self.call(
            chain,
            "getTokenAccountsByOwner",
            [address, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}],
        )
        value = accounts.get("value", []) if isinstance(accounts, dict) else []
        results: list[dict[str, Any]] = []
        for entry in value:
            parsed = entry.get("account", {}).get("data", {}).get("parsed", {}) if isinstance(entry, dict) else {}
            info = parsed.get("info", {}) if isinstance(parsed, dict) else {}
            mint = info.get("mint")
            token_amount = info.get("tokenAmount", {}) if isinstance(info, dict) else {}
            amount = float(token_amount.get("uiAmount") or 0)
            if amount <= 0 or not mint:
                continue
            results.append(
                {
                    "symbol": mint[:8],
                    "contract": mint,
                    "balance_formatted": f"{amount} {mint[:8]}",
                    "amount_decimal": amount,
                    "usd_value": None,
                }
            )
        return results

    async def _discover_cosmos_tokens(self, chain: str, address: str) -> list[dict[str, Any]]:
        metadata = get_chain_metadata(chain)
        result = await self.call(chain, f"/cosmos/bank/v1beta1/balances/{address}", [])
        denoms = result.get("balances", []) if isinstance(result, dict) else []
        native_denom = metadata.get("cosmos_denom")
        results: list[dict[str, Any]] = []
        for item in denoms:
            denom = item.get("denom") if isinstance(item, dict) else None
            amount_str = item.get("amount", "0") if isinstance(item, dict) else "0"
            if not denom or denom == native_denom:
                continue  # native gas token is reported separately by get_balance
            decimals = int(metadata["decimals"])
            try:
                amount_decimal = float(amount_str) / 10**decimals
            except (TypeError, ValueError):
                continue
            results.append(
                {
                    "symbol": denom,
                    "contract": denom,
                    "balance_formatted": f"{amount_decimal:.6f} {denom}",
                    "amount_decimal": amount_decimal,
                    "usd_value": None,
                }
            )
        return results

    async def _discover_sui_tokens(self, chain: str, address: str) -> list[dict[str, Any]]:
        result = await self.call(chain, "suix_getAllBalances", [address])
        balances = result if isinstance(result, list) else []
        results: list[dict[str, Any]] = []
        for item in balances:
            coin_type = item.get("coinType", "") if isinstance(item, dict) else ""
            total = item.get("totalBalance", "0") if isinstance(item, dict) else "0"
            if coin_type.endswith("::sui::SUI"):
                continue  # native SUI is reported by get_balance
            try:
                amount_decimal = float(total) / 10**9
            except (TypeError, ValueError):
                continue
            symbol = coin_type.split("::")[-1] if coin_type else "unknown"
            results.append(
                {
                    "symbol": symbol,
                    "contract": coin_type,
                    "balance_formatted": f"{amount_decimal:.9f} {symbol}",
                    "amount_decimal": amount_decimal,
                    "usd_value": None,
                }
            )
        return results

    async def compare_chains(self, chains: list[str]) -> dict[str, Any]:
        async def _chain_snapshot(chain: str) -> dict[str, Any]:
            canonical = self._canonical_chain(chain)
            protocol = self.get_protocol(canonical)
            gas = await self.get_gas_price(canonical)
            snapshot: dict[str, Any] = {
                "chain": canonical,
                "protocol": protocol,
                "health": "healthy",
            }
            if protocol == "evm":
                snapshot["gas_price_gwei"] = gas["gas_price_gwei"]
                snapshot["base_fee_gwei"] = gas["base_fee_gwei"]
            else:
                snapshot["fee_hint"] = gas
            try:
                snapshot["block_number"] = await self.get_block_number(canonical)
            except Exception as exc:
                snapshot["block_number_error"] = str(exc)
            return snapshot

        results = await asyncio.gather(*[_chain_snapshot(chain) for chain in chains], return_exceptions=True)
        snapshots: list[dict[str, Any]] = []
        for chain, result in zip(chains, results, strict=False):
            if isinstance(result, Exception):
                snapshots.append({"chain": self._canonical_chain(chain), "health": "degraded", "error": str(result)})
            else:
                snapshots.append(result)

        evm_healthy = [item for item in snapshots if item.get("health") == "healthy" and "gas_price_gwei" in item]
        cheapest = min(evm_healthy, key=lambda item: item["gas_price_gwei"]) if evm_healthy else None
        return {
            "chains": snapshots,
            "recommended_chain": cheapest["chain"] if cheapest else None,
            "cache_stats": self.cache.get_cache_stats(),
        }

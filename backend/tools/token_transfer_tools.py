"""Non-EVM token-transfer tools (Part 1 of the non-EVM write-tools effort).

These replace the ``send_erc20`` "deferred" stub for non-EVM protocols by
registering protocol-specific token transfer tools that sign and broadcast with
the agent wallet. They mirror the architecture of ``send_transaction``:

  * spending-cap enforcement + recording (reused from transaction_tools)
  * tx-confirmation scheduling (reused from transaction_tools)
  * protocol wallet key resolution (reused from transaction_tools)
  * transfer services under backend/services/ that do the actual signing
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

try:
    from .registry import ToolContext, function_schema, register_tool, validate_chain_allowed
    from .transaction_tools import (
        _enforce_spending_cap,
        _record_native_spend,
        _require_protocol_private_key,
        _schedule_confirmation,
    )
except ImportError:
    from tools.registry import ToolContext, function_schema, register_tool, validate_chain_allowed
    from tools.transaction_tools import (
        _enforce_spending_cap,
        _record_native_spend,
        _require_protocol_private_key,
        _schedule_confirmation,
    )

# Nominal gas estimates (native units) used for spending-cap enforcement on
# token transfers. Token transfers spend only gas (not the token amount itself),
# so these are conservative upper bounds for a single token-transfer tx fee.
_TOKEN_GAS_ESTIMATE_NATIVE: dict[str, Decimal] = {
    "solana": Decimal("0.00001"),  # ~5000 lamports base fee
    "tron": Decimal("1"),          # TRC-20 fee varies with energy; 1 TRX is conservative
    "sui": Decimal("0.01"),        # gas in MIST; ~0.01 SUI
    "near": Decimal("0.001"),      # ~30 Tgas for ft_transfer
    "cosmos": Decimal("0.01"),     # ~0.025 gas price * typical gas
}


def _token_gas_estimate(protocol: str) -> Decimal:
    return _TOKEN_GAS_ESTIMATE_NATIVE.get(protocol, Decimal("0.001"))


def _unsupported_protocol(protocol: str, chain: str, tool_name: str) -> dict[str, Any]:
    return {
        "chain": chain,
        "protocol": protocol,
        "status": "deferred",
        "message": f"{tool_name} is only supported for the matching protocol; "
        f"got protocol '{protocol}' for chain '{chain}'.",
    }


async def send_trc20_token(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Transfer a TRC-20 token on Tron via the agent wallet."""
    chain = validate_chain_allowed(context, str(args.get("chain") or "tron"))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol != "tron":
        return _unsupported_protocol(protocol, chain, "send_trc20_token")

    try:
        from ..services.tron_trc20_transfer import (
            DEFAULT_TRC20_FEE_LIMIT_SUN,
            build_trc20_transfer_parameter,
            sign_tron_transaction,
            tron_base58_from_private_key,
        )
    except ImportError:
        from services.tron_trc20_transfer import (
            DEFAULT_TRC20_FEE_LIMIT_SUN,
            build_trc20_transfer_parameter,
            sign_tron_transaction,
            tron_base58_from_private_key,
        )

    contract_address = str(args["contract_address"])
    to_address = str(args["to_address"])
    decimals = int(args.get("decimals") or 6)
    amount_raw = int(Decimal(str(args["amount"])) * (Decimal(10) ** decimals))

    private_key = _require_protocol_private_key(context, "tron")
    from_address = tron_base58_from_private_key(private_key)
    gas = _token_gas_estimate("tron")
    _enforce_spending_cap(context, chain, gas)

    parameter = build_trc20_transfer_parameter(to_address, amount_raw)
    payload = {
        "owner_address": from_address,
        "contract_address": contract_address,
        "function_selector": "transfer(address,uint256)",
        "parameter": parameter,
        "call_value": 0,
        "fee_limit": DEFAULT_TRC20_FEE_LIMIT_SUN,
        "visible": True,
    }
    unsigned = await context.rpc_client.call(chain, "wallet/triggersmartcontract", [payload])
    signed = sign_tron_transaction(unsigned, private_key)
    broadcast = await context.rpc_client.call(chain, "wallet/broadcasttransaction", [signed])
    if not isinstance(broadcast, dict) or not bool(broadcast.get("result")):
        raise RuntimeError(f"Tron TRC-20 broadcast failed: {broadcast}")
    tx_hash = str(
        broadcast.get("txid")
        or (unsigned.get("transaction", {}) if isinstance(unsigned, dict) else {}).get("txID")
        or ""
    )

    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(context, chain, tx_hash, tool_name="send_trc20_token", original_tool_args=args)
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "tron",
        "from": from_address,
        "tx_hash": tx_hash,
        "contract_address": contract_address,
        "amount_raw": amount_raw,
        "confirmation": "pending",
    }


async def send_spl_token(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Transfer an SPL token on Solana via the agent wallet."""
    chain = validate_chain_allowed(context, str(args.get("chain") or "solana"))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol != "solana":
        return _unsupported_protocol(protocol, chain, "send_spl_token")

    try:
        from ..services.solana_spl_transfer import (
            build_and_sign_versioned_transaction,
            build_spl_transfer_instruction,
            derive_associated_token_address,
            load_solana_keypair,
        )
    except ImportError:
        from services.solana_spl_transfer import (
            build_and_sign_versioned_transaction,
            build_spl_transfer_instruction,
            derive_associated_token_address,
            load_solana_keypair,
        )

    token_mint = str(args["token_mint"])
    to_owner = str(args["to_owner_address"])
    decimals = int(args.get("decimals") or 6)
    amount_raw = int(Decimal(str(args["amount"])) * (Decimal(10) ** decimals))
    from_token_account = args.get("from_token_account")
    to_token_account = args.get("to_token_account")

    private_key = _require_protocol_private_key(context, "solana")
    keypair = load_solana_keypair(private_key)
    from_pubkey = str(keypair.pubkey())

    source = str(from_token_account) if from_token_account else derive_associated_token_address(from_pubkey, token_mint)
    dest = str(to_token_account) if to_token_account else derive_associated_token_address(to_owner, token_mint)

    gas = _token_gas_estimate("solana")
    _enforce_spending_cap(context, chain, gas)

    instruction = build_spl_transfer_instruction(source, dest, from_pubkey, amount_raw)
    blockhash_resp = await context.rpc_client.call(chain, "getLatestBlockhash", [])
    blockhash = (
        blockhash_resp.get("value", {}).get("blockhash")
        if isinstance(blockhash_resp, dict)
        else None
    )
    if not blockhash:
        raise RuntimeError("Failed to fetch Solana recent blockhash for signing.")

    raw_tx = build_and_sign_versioned_transaction(keypair, [instruction], blockhash)
    signature = await context.rpc_client.call(
        chain,
        "sendTransaction",
        [raw_tx, {"encoding": "base64", "skipPreflight": False}],
    )
    if not isinstance(signature, str):
        raise RuntimeError(f"Unexpected Solana sendTransaction response: {signature}")

    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(context, chain, signature, tool_name="send_spl_token", original_tool_args=args)
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "solana",
        "from": from_pubkey,
        "tx_hash": signature,
        "token_mint": token_mint,
        "source_token_account": source,
        "dest_token_account": dest,
        "amount_raw": amount_raw,
        "confirmation": "pending",
    }


async def send_ibc_token(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Transfer an IBC-denom token on a Cosmos chain via the SDK bank module."""
    chain = validate_chain_allowed(context, str(args["chain"]))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol != "cosmos":
        return _unsupported_protocol(protocol, chain, "send_ibc_token")

    try:
        from ..services.chain_registry import get_chain_metadata
        from ..services.cosmos_token_transfer import execute_cosmos_ibc_transfer
    except ImportError:
        from services.chain_registry import get_chain_metadata
        from services.cosmos_token_transfer import execute_cosmos_ibc_transfer

    to_address = str(args["to_address"])
    denom = str(args["denom"])
    amount_native = Decimal(str(args["amount"]))
    decimals = int(get_chain_metadata(chain)["decimals"])
    amount_base = int(amount_native * (Decimal(10) ** decimals))

    private_key = _require_protocol_private_key(context, "cosmos")
    gas = _token_gas_estimate("cosmos")
    _enforce_spending_cap(context, chain, gas)

    result = await asyncio.to_thread(
        execute_cosmos_ibc_transfer, chain, private_key, to_address, amount_base, denom
    )
    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(context, chain, result["tx_hash"], tool_name="send_ibc_token", original_tool_args=args)
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "cosmos",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "denom": result["denom"],
        "amount_base": result["amount_base"],
        "confirmation": "pending",
    }


async def send_cw20_token(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Transfer a CW20 (CosmWasm) token on a Cosmos chain via the agent wallet."""
    chain = validate_chain_allowed(context, str(args["chain"]))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol != "cosmos":
        return _unsupported_protocol(protocol, chain, "send_cw20_token")

    try:
        from ..services.cosmos_token_transfer import execute_cosmos_cw20_transfer
    except ImportError:
        from services.cosmos_token_transfer import execute_cosmos_cw20_transfer

    contract_address = str(args["contract_address"])
    to_address = str(args["to_address"])
    # CW20 amounts are raw uint128 units (decimals are contract-defined and
    # unknown to us); the caller supplies the raw amount.
    amount_raw = int(Decimal(str(args["amount"])))

    private_key = _require_protocol_private_key(context, "cosmos")
    gas = _token_gas_estimate("cosmos")
    _enforce_spending_cap(context, chain, gas)

    result = await asyncio.to_thread(
        execute_cosmos_cw20_transfer, chain, private_key, contract_address, to_address, amount_raw
    )
    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(context, chain, result["tx_hash"], tool_name="send_cw20_token", original_tool_args=args)
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "cosmos",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "contract_address": contract_address,
        "amount_raw": amount_raw,
        "confirmation": "pending",
    }


async def send_sui_token(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Transfer a SUI Move coin (non-SUI coin type) via the agent wallet."""
    chain = validate_chain_allowed(context, str(args.get("chain") or "sui"))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol != "sui":
        return _unsupported_protocol(protocol, chain, "send_sui_token")

    try:
        from ..services.sui_coin_transfer import execute_sui_coin_transfer
        from ..services.sui_transfer import sui_write_rpc_url
    except ImportError:
        from services.sui_coin_transfer import execute_sui_coin_transfer
        from services.sui_transfer import sui_write_rpc_url

    coin_type = str(args["coin_type"])
    to_address = str(args["to_address"])
    decimals = int(args.get("decimals") or 9)
    amount_raw = int(Decimal(str(args["amount"])) * (Decimal(10) ** decimals))

    keystring = _require_protocol_private_key(context, "sui")
    gas = _token_gas_estimate("sui")
    _enforce_spending_cap(context, chain, gas)

    rpc_url = sui_write_rpc_url(chain)
    tracked_coins = context.agent.get("sui_tracked_coins") or []
    result = await asyncio.to_thread(
        execute_sui_coin_transfer, rpc_url, keystring, to_address, amount_raw, coin_type, tracked_coins
    )
    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(context, chain, result["tx_hash"], tool_name="send_sui_token", original_tool_args=args)
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "sui",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "coin_type": coin_type,
        "amount": result["amount"],
        "confirmation": "pending",
    }


async def send_nep141_token(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Transfer a NEP-141 (NEAR fungible token) via the agent wallet."""
    chain = validate_chain_allowed(context, str(args.get("chain") or "near"))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol != "near":
        return _unsupported_protocol(protocol, chain, "send_nep141_token")

    try:
        from ..services.near_nep141_transfer import execute_near_nep141_transfer
    except ImportError:
        from services.near_nep141_transfer import execute_near_nep141_transfer

    contract_id = str(args["contract_id"])
    receiver_id = str(args["receiver_id"])
    decimals = int(args.get("decimals") or 18)
    amount_raw = int(Decimal(str(args["amount"])) * (Decimal(10) ** decimals))

    private_key = _require_protocol_private_key(context, "near")
    account_id = (context.agent.get("wallet_addresses") or {}).get("near")
    if not account_id:
        raise RuntimeError("NEAR agent wallet address is not configured.")

    gas = _token_gas_estimate("near")
    _enforce_spending_cap(context, chain, gas)

    result = await asyncio.to_thread(
        execute_near_nep141_transfer, str(account_id), private_key, contract_id, receiver_id, amount_raw
    )
    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(
        context,
        chain,
        result["tx_hash"],
        tool_name="send_nep141_token",
        original_tool_args=args,
        sender_account_id=str(account_id),
    )
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "near",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "contract_id": contract_id,
        "amount_raw": result["amount_raw"],
        "confirmation": "pending",
    }


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

_TOKEN_TRANSFER_TOOLS: list[tuple[str, str, dict[str, Any], list[str], Any]] = [
    (
        "send_trc20_token",
        "Send a TRC-20 token transfer on Tron with the agent wallet.",
        {
            "chain": {"type": "string"},
            "contract_address": {"type": "string"},
            "to_address": {"type": "string"},
            "amount": {"type": "string"},
            "decimals": {"type": "integer"},
        },
        ["contract_address", "to_address", "amount"],
        send_trc20_token,
    ),
    (
        "send_spl_token",
        "Send an SPL token transfer on Solana with the agent wallet.",
        {
            "chain": {"type": "string"},
            "token_mint": {"type": "string"},
            "to_owner_address": {"type": "string"},
            "amount": {"type": "string"},
            "decimals": {"type": "integer"},
            "from_token_account": {"type": "string"},
            "to_token_account": {"type": "string"},
        },
        ["token_mint", "to_owner_address", "amount"],
        send_spl_token,
    ),
    (
        "send_ibc_token",
        "Send an IBC-denom token transfer on a Cosmos chain via the SDK bank module.",
        {
            "chain": {"type": "string"},
            "to_address": {"type": "string"},
            "amount": {"type": "string"},
            "denom": {"type": "string"},
        },
        ["chain", "to_address", "amount", "denom"],
        send_ibc_token,
    ),
    (
        "send_cw20_token",
        "Send a CW20 (CosmWasm) token transfer on a Cosmos chain with the agent wallet.",
        {
            "chain": {"type": "string"},
            "contract_address": {"type": "string"},
            "to_address": {"type": "string"},
            "amount": {"type": "string"},
        },
        ["chain", "contract_address", "to_address", "amount"],
        send_cw20_token,
    ),
    (
        "send_sui_token",
        "Send a SUI Move coin (non-SUI coin type) transfer with the agent wallet.",
        {
            "chain": {"type": "string"},
            "coin_type": {"type": "string"},
            "to_address": {"type": "string"},
            "amount": {"type": "string"},
            "decimals": {"type": "integer"},
        },
        ["coin_type", "to_address", "amount"],
        send_sui_token,
    ),
    (
        "send_nep141_token",
        "Send a NEP-141 (NEAR fungible token) transfer with the agent wallet.",
        {
            "chain": {"type": "string"},
            "contract_id": {"type": "string"},
            "receiver_id": {"type": "string"},
            "amount": {"type": "string"},
            "decimals": {"type": "integer"},
        },
        ["contract_id", "receiver_id", "amount"],
        send_nep141_token,
    ),
]

TOOLS = [
    register_tool(function_schema(name, description, properties, required), "transact", executor)
    for name, description, properties, required, executor in _TOKEN_TRANSFER_TOOLS
]


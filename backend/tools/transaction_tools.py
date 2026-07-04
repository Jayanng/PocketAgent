from __future__ import annotations

import asyncio
import base64
from decimal import Decimal
from typing import Any

from eth_account import Account
from eth_abi import encode as abi_encode
from eth_utils import keccak

try:
    from ..database import update_agent
    from ..services.encryption import decrypt_private_key
    from .registry import ToolContext, function_schema, register_tool, validate_chain_allowed
    from ..config import get_settings
    from ..services.confirmation import ConfirmationService
except ImportError:
    from database import update_agent
    from services.encryption import decrypt_private_key
    from tools.registry import ToolContext, function_schema, register_tool, validate_chain_allowed
    from config import get_settings
    from services.confirmation import ConfirmationService


ERC20_TRANSFER_SELECTOR = "a9059cbb"


def _native_to_wei(amount: str | int | float | Decimal, decimals: int = 18) -> int:
    return int(Decimal(str(amount)) * (Decimal(10) ** decimals))


def _wei_to_native(amount_wei: int) -> Decimal:
    return Decimal(amount_wei) / (Decimal(10) ** 18)


def _schedule_confirmation(
    context: ToolContext,
    chain: str,
    tx_hash: str,
    *,
    tool_name: str,
    original_tool_args: dict[str, Any] | None,
    sender_account_id: str | None = None,
) -> None:
    """Spawn a background task that polls for the tx receipt and writes a
    follow-up message into the active conversation. No-op if we don't have
    enough context (no conversation_id, no DB path, etc.).
    """
    if not context.conversation_id:
        return
    try:
        db_path = get_settings().database_path
    except Exception:
        return
    agent_id = context.agent.get("id")
    ConfirmationService().schedule(
        chain=chain,
        tx_hash=tx_hash,
        conversation_id=context.conversation_id,
        db_path=db_path,
        agent_id=str(agent_id) if agent_id else None,
        sender_account_id=sender_account_id,
        tool_name=tool_name,
        original_tool_args=original_tool_args,
    )


def _require_protocol_private_key(context: ToolContext, protocol: str) -> str:
    encrypted_wallets = context.agent.get("encrypted_wallets") or {}
    encrypted_key = encrypted_wallets.get(protocol) if isinstance(encrypted_wallets, dict) else None
    if not encrypted_key and protocol == "evm":
        encrypted_key = context.agent.get("encrypted_private_key")
    if not encrypted_key:
        raise PermissionError(
            f"Agent wallet is not configured for protocol '{protocol}'. "
            "Create a new agent so protocol-specific wallets can be generated."
        )
    return decrypt_private_key(str(encrypted_key))


def _spent_by_chain(context: ToolContext) -> dict[str, Decimal]:
    raw = context.agent.get("total_spent_by_chain") or {}
    if not isinstance(raw, dict):
        return {}
    spent: dict[str, Decimal] = {}
    for chain, amount in raw.items():
        try:
            spent[str(chain)] = Decimal(str(amount))
        except Exception:
            continue
    return spent


def _chain_spent(context: ToolContext, chain: str, spent_by_chain: dict[str, Decimal]) -> Decimal:
    if chain in spent_by_chain:
        return spent_by_chain[chain]
    if spent_by_chain:
        return Decimal("0")
    return Decimal(str(context.agent.get("total_spent") or 0))


def _enforce_spending_cap(context: ToolContext, chain: str, amount_native: Decimal) -> None:
    spending_cap = Decimal(str(context.agent.get("spending_cap") or 0))
    spent_by_chain = _spent_by_chain(context)
    chain_spent = _chain_spent(context, chain, spent_by_chain)
    if spending_cap <= 0:
        raise PermissionError("Agent spending cap is zero; enable a positive cap before sending transactions.")
    if chain_spent + amount_native > spending_cap:
        raise PermissionError(
            f"Transaction exceeds {chain} spending cap: {chain_spent + amount_native} native units requested against {spending_cap} native-unit cap for this chain."
        )


async def _record_native_spend(context: ToolContext, chain: str, amount_native: Decimal) -> None:
    agent_id = context.agent.get("id")
    if not agent_id:
        return
    spent_by_chain = _spent_by_chain(context)
    spent_by_chain[chain] = _chain_spent(context, chain, spent_by_chain) + amount_native
    serializable_spend = {key: float(value) for key, value in spent_by_chain.items()}
    if context.db is not None:
        await update_agent(context.db, str(agent_id), total_spent_by_chain=serializable_spend)
    context.agent["total_spent_by_chain"] = serializable_spend


def _encode_erc20_transfer(to_address: str, amount_units: int) -> str:
    clean_address = to_address.removeprefix("0x").lower()
    if len(clean_address) != 40:
        raise ValueError("ERC-20 recipient address must be a 20-byte EVM address.")
    encoded_address = clean_address.rjust(64, "0")
    encoded_amount = hex(amount_units)[2:].rjust(64, "0")
    return f"0x{ERC20_TRANSFER_SELECTOR}{encoded_address}{encoded_amount}"


def _split_abi_types(type_list: str) -> list[str]:
    types: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(type_list):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            types.append(type_list[start:index].strip())
            start = index + 1
    tail = type_list[start:].strip()
    if tail:
        types.append(tail)
    return types


def _coerce_abi_arg(abi_type: str, value: Any) -> Any:
    if abi_type.startswith(("uint", "int")):
        return int(value)
    if abi_type == "bool":
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes"}
    if abi_type == "bytes":
        if isinstance(value, str) and value.startswith("0x"):
            return bytes.fromhex(value[2:])
        return value
    if abi_type.startswith("bytes") and abi_type != "bytes":
        if isinstance(value, str) and value.startswith("0x"):
            return bytes.fromhex(value[2:])
    return value


def _encode_abi_function_call(abi_function: str, args: list[Any]) -> str:
    if "(" not in abi_function or not abi_function.endswith(")"):
        raise ValueError(
            "abi_function must be a canonical signature such as 'transfer(address,uint256)' "
            "when raw data is not supplied."
        )
    open_paren = abi_function.index("(")
    function_name = abi_function[:open_paren].strip()
    type_list = abi_function[open_paren + 1:-1].strip()
    if not function_name:
        raise ValueError("abi_function must include a function name.")
    abi_types = _split_abi_types(type_list) if type_list else []
    if len(abi_types) != len(args):
        raise ValueError(f"abi_function expects {len(abi_types)} arguments, got {len(args)}.")
    selector = keccak(text=f"{function_name}({','.join(abi_types)})")[:4]
    encoded_args = abi_encode(abi_types, [_coerce_abi_arg(t, v) for t, v in zip(abi_types, args, strict=True)])
    return f"0x{(selector + encoded_args).hex()}"


def _contract_call_data(args: dict[str, Any]) -> str:
    raw_data = str(args.get("data") or "")
    if raw_data and raw_data != "0x":
        return raw_data if raw_data.startswith("0x") else f"0x{raw_data}"
    abi_function = str(args.get("abi_function") or "")
    call_args = args.get("args") or []
    if abi_function:
        if not isinstance(call_args, list):
            raise ValueError("contract_call args must be a list.")
        return _encode_abi_function_call(abi_function, call_args)
    return "0x"


def _json_rpc_quantity_tx(tx: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(tx)
    for key in ("value", "gas", "gasPrice", "maxFeePerGas", "maxPriorityFeePerGas", "nonce"):
        value = normalized.get(key)
        if isinstance(value, int):
            normalized[key] = hex(value)
    return normalized


async def _sign_and_send_evm_transaction(
    context: ToolContext,
    chain: str,
    tx: dict[str, Any],
    amount_for_cap: Decimal = Decimal("0"),
    *,
    tool_name: str = "send_transaction",
    original_tool_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    private_key = _require_protocol_private_key(context, "evm")
    account = Account.from_key(private_key)
    chain_id = await context.rpc_client.get_chain_id(chain)
    nonce = await context.rpc_client.get_transaction_count(chain, account.address)
    gas_price = await context.rpc_client.call(chain, "eth_gasPrice", [])
    gas_price_wei = int(gas_price, 16) if isinstance(gas_price, str) else int(gas_price)

    tx_payload = {
        "chainId": int(chain_id),
        "nonce": nonce,
        "gasPrice": gas_price_wei,
        "from": account.address,
        **tx,
    }
    if "gas" not in tx_payload:
        estimate_tx = {key: value for key, value in tx_payload.items() if key not in {"chainId", "nonce", "gasPrice"}}
        gas_estimate = await context.rpc_client.call(chain, "eth_estimateGas", [_json_rpc_quantity_tx(estimate_tx)])
        tx_payload["gas"] = int(gas_estimate, 16) if isinstance(gas_estimate, str) else int(gas_estimate)

    native_spend_for_cap = amount_for_cap + _wei_to_native(int(tx_payload["gas"]) * gas_price_wei)
    if native_spend_for_cap > 0:
        _enforce_spending_cap(context, chain, native_spend_for_cap)

    signed = Account.sign_transaction(tx_payload, private_key)
    raw_transaction = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
    tx_hash = await context.rpc_client.send_raw_transaction(chain, raw_transaction.hex())
    if native_spend_for_cap > 0:
        await _record_native_spend(context, chain, native_spend_for_cap)

    _schedule_confirmation(
        context,
        chain,
        tx_hash,
        tool_name=tool_name,
        original_tool_args=original_tool_args,
    )
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "evm",
        "from": account.address,
        "tx_hash": tx_hash,
        "gas": tx_payload["gas"],
        "gas_price_wei": gas_price_wei,
        "cap_spend_native": str(native_spend_for_cap),
        "confirmation": "pending",
    }


async def _sign_and_send_solana_transaction(
    context: ToolContext,
    chain: str,
    to_address: str,
    lamports: int,
    amount_for_cap: Decimal = Decimal("0"),
    *,
    tool_name: str = "send_transaction",
    original_tool_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from solders.hash import Hash
    from solders.keypair import Keypair
    from solders.message import MessageV0
    from solders.pubkey import Pubkey
    from solders.system_program import TransferParams, transfer
    from solders.transaction import VersionedTransaction

    private_key = _require_protocol_private_key(context, "solana")
    if amount_for_cap > 0:
        _enforce_spending_cap(context, chain, amount_for_cap)

    raw_key = bytes.fromhex(private_key.removeprefix("0x"))
    keypair = Keypair.from_bytes(raw_key) if len(raw_key) == 64 else Keypair.from_seed(raw_key)
    from_pubkey = keypair.pubkey()
    to_pubkey = Pubkey.from_string(to_address)

    blockhash_resp = await context.rpc_client.call(chain, "getLatestBlockhash", [])
    blockhash_str = blockhash_resp.get("value", {}).get("blockhash") if isinstance(blockhash_resp, dict) else None
    if not blockhash_str:
        raise RuntimeError("Failed to fetch Solana recent blockhash for signing.")

    instruction = transfer(
        TransferParams(
            from_pubkey=from_pubkey,
            to_pubkey=to_pubkey,
            lamports=lamports,
        )
    )
    message = MessageV0.try_compile(from_pubkey, [instruction], [], Hash.from_string(blockhash_str))
    transaction = VersionedTransaction(message, [keypair])
    raw_tx = base64.b64encode(bytes(transaction)).decode("ascii")
    signature = await context.rpc_client.call(
        chain,
        "sendTransaction",
        [raw_tx, {"encoding": "base64", "skipPreflight": False}],
    )
    if not isinstance(signature, str):
        raise RuntimeError(f"Unexpected Solana sendTransaction response: {signature}")
    if amount_for_cap > 0:
        await _record_native_spend(context, chain, amount_for_cap)

    _schedule_confirmation(
        context,
        chain,
        signature,
        tool_name=tool_name,
        original_tool_args=original_tool_args,
    )
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "solana",
        "from": str(from_pubkey),
        "tx_hash": signature,
        "lamports": lamports,
        "confirmation": "pending",
    }


async def _sign_and_send_cosmos_transaction(
    context: ToolContext,
    chain: str,
    to_address: str,
    amount_base: int,
    amount_for_cap: Decimal = Decimal("0"),
    *,
    tool_name: str = "send_transaction",
    original_tool_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    private_key = _require_protocol_private_key(context, "cosmos")
    if amount_for_cap > 0:
        _enforce_spending_cap(context, chain, amount_for_cap)

    try:
        from ..services.cosmos_transfer import cosmos_address_from_private_key, execute_cosmos_native_transfer
        from ..services.chain_registry import get_chain_metadata
    except ImportError:
        from backend.services.cosmos_transfer import cosmos_address_from_private_key, execute_cosmos_native_transfer
        from backend.services.chain_registry import get_chain_metadata

    metadata = get_chain_metadata(chain)
    bech32_prefix = str(metadata.get("cosmos_bech32_prefix") or "cosmos")
    sender = cosmos_address_from_private_key(private_key, bech32_prefix)
    balance = await context.rpc_client.get_balance(chain, sender)
    available_base = int(balance.get("wei", balance.get("raw", 0)) or 0)
    if available_base < amount_base:
        symbol = balance.get("symbol", metadata["symbol"])
        raise RuntimeError(
            f"Insufficient {symbol} balance for transfer: "
            f"requested {amount_base} base units, available {available_base} base units."
        )

    result = await asyncio.to_thread(
        execute_cosmos_native_transfer,
        chain,
        private_key,
        to_address,
        amount_base,
    )
    if amount_for_cap > 0:
        await _record_native_spend(context, chain, amount_for_cap)

    _schedule_confirmation(
        context,
        chain,
        result["tx_hash"],
        tool_name=tool_name,
        original_tool_args=original_tool_args,
    )
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "cosmos",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "amount_base": result["amount_base"],
        "denom": result["denom"],
        "confirmation": "pending",
    }


async def _sign_and_send_near_transaction(
    context: ToolContext,
    chain: str,
    to_address: str,
    amount_yocto: int,
    amount_for_cap: Decimal = Decimal("0"),
    *,
    tool_name: str = "send_transaction",
    original_tool_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    private_key = _require_protocol_private_key(context, "near")
    if amount_for_cap > 0:
        _enforce_spending_cap(context, chain, amount_for_cap)

    try:
        from ..services.near_transfer import execute_near_native_transfer
    except ImportError:
        from backend.services.near_transfer import execute_near_native_transfer

    account_id = (context.agent.get("wallet_addresses") or {}).get("near")
    if not account_id:
        raise RuntimeError("NEAR agent wallet address is not configured.")

    balance = await context.rpc_client.get_balance(chain, str(account_id))
    available_yocto = int(balance.get("wei", balance.get("raw", 0)) or 0)
    if available_yocto < amount_yocto:
        symbol = balance.get("symbol", "NEAR")
        raise RuntimeError(
            f"Insufficient {symbol} balance for transfer: "
            f"requested {amount_yocto} yoctoNEAR, available {available_yocto} yoctoNEAR."
        )

    result = await asyncio.to_thread(
        execute_near_native_transfer,
        str(account_id),
        private_key,
        to_address,
        amount_yocto,
    )
    if amount_for_cap > 0:
        await _record_native_spend(context, chain, amount_for_cap)

    _schedule_confirmation(
        context,
        chain,
        result["tx_hash"],
        tool_name=tool_name,
        original_tool_args=original_tool_args,
        sender_account_id=str(account_id),
    )
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "near",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "amount_yocto": result["amount_yocto"],
        "confirmation": "pending",
    }


async def _sign_and_send_sui_transaction(
    context: ToolContext,
    chain: str,
    to_address: str,
    amount_mist: int,
    amount_for_cap: Decimal = Decimal("0"),
    *,
    tool_name: str = "send_transaction",
    original_tool_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        from ..services.sui_transfer import execute_sui_native_transfer, sui_write_rpc_url
    except ImportError:
        from services.sui_transfer import execute_sui_native_transfer, sui_write_rpc_url

    keystring = _require_protocol_private_key(context, "sui")
    if amount_for_cap > 0:
        _enforce_spending_cap(context, chain, amount_for_cap)

    sender = (context.agent.get("wallet_addresses") or {}).get("sui")
    if sender:
        balance = await context.rpc_client.get_balance(chain, str(sender))
        available_mist = int(balance.get("wei", balance.get("raw", 0)) or 0)
        if available_mist < amount_mist:
            symbol = balance.get("symbol", "SUI")
            raise RuntimeError(
                f"Insufficient {symbol} balance for transfer: "
                f"requested {amount_mist} MIST, available {available_mist} MIST."
            )

    rpc_url = sui_write_rpc_url(chain)
    tracked_coins = context.agent.get("sui_tracked_coins") or []
    result = await asyncio.to_thread(
        execute_sui_native_transfer,
        rpc_url,
        keystring,
        to_address,
        amount_mist,
        tracked_coins,
    )
    if context.db is not None and result.get("tracked_coins") is not None:
        await update_agent(
            context.db,
            str(context.agent["id"]),
            sui_tracked_coins=result["tracked_coins"],
        )
        context.agent["sui_tracked_coins"] = result["tracked_coins"]
    if amount_for_cap > 0:
        await _record_native_spend(context, chain, amount_for_cap)

    _schedule_confirmation(
        context,
        chain,
        result["tx_hash"],
        tool_name=tool_name,
        original_tool_args=original_tool_args,
        sender_account_id=str(sender) if sender else None,
    )
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "sui",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "amount_mist": result["amount_mist"],
        "confirmation": "pending",
    }


async def _sign_and_send_tron_transaction(
    context: ToolContext,
    chain: str,
    to_address: str,
    amount_sun: int,
    amount_for_cap: Decimal = Decimal("0"),
    *,
    tool_name: str = "send_transaction",
    original_tool_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from tronpy.keys import PrivateKey

    private_key = _require_protocol_private_key(context, "tron")
    if amount_for_cap > 0:
        _enforce_spending_cap(context, chain, amount_for_cap)

    tron_key = PrivateKey.fromhex(private_key.removeprefix("0x"))
    from_address = tron_key.public_key.to_base58check_address()
    unsigned = await context.rpc_client.call(
        chain,
        "wallet/createtransaction",
        [
            {
                "owner_address": from_address,
                "to_address": to_address,
                "amount": amount_sun,
                "visible": True,
            }
        ],
    )
    if not isinstance(unsigned, dict) or not unsigned.get("txID"):
        raise RuntimeError(f"Unexpected Tron create transaction response: {unsigned}")

    signature = tron_key.sign_msg_hash(bytes.fromhex(str(unsigned["txID"]))).hex()
    signed = {**unsigned, "signature": [signature]}
    broadcast = await context.rpc_client.call(chain, "wallet/broadcasttransaction", [signed])
    if not isinstance(broadcast, dict) or not bool(broadcast.get("result")):
        raise RuntimeError(f"Tron broadcast failed: {broadcast}")
    tx_hash = str(broadcast.get("txid") or unsigned["txID"])
    if amount_for_cap > 0:
        await _record_native_spend(context, chain, amount_for_cap)

    _schedule_confirmation(
        context,
        chain,
        tx_hash,
        tool_name=tool_name,
        original_tool_args=original_tool_args,
    )
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "tron",
        "from": from_address,
        "tx_hash": tx_hash,
        "amount_sun": amount_sun,
        "confirmation": "pending",
    }


def _unsupported_write_deferred(protocol: str, chain: str) -> dict[str, Any]:
    return {
        "chain": chain,
        "protocol": protocol,
        "status": "deferred",
        "message": (
            "Live native transaction signing and broadcast are implemented for EVM, Solana, Tron, "
            "Cosmos, Sui, and NEAR. "
            f"{protocol.title()} writes are not supported for this chain."
        ),
    }


async def evm_get_block_number(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Lightweight latest block height — use this instead of evm_get_block for 'latest block' queries."""
    chain = validate_chain_allowed(context, str(args["chain"]))
    block_number = await context.rpc_client.get_block_number(chain)
    return {"chain": chain, "block_number": block_number}


def _summarize_evm_block(result: Any, *, full_transactions: bool) -> Any:
    """eth_getBlockByNumber(false) still returns every tx hash; strip that for LLM-sized payloads."""
    if full_transactions or not isinstance(result, dict):
        return result
    transactions = result.get("transactions")
    if not isinstance(transactions, list):
        return result
    summary = {key: value for key, value in result.items() if key != "transactions"}
    summary["transactionCount"] = len(transactions)
    return summary


async def evm_get_block(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    block = args.get("block", "latest")
    full_transactions = bool(args.get("full_transactions", False))
    result = await context.rpc_client.call(
        chain, "eth_getBlockByNumber", [block, full_transactions]
    )
    return _summarize_evm_block(result, full_transactions=full_transactions)


async def evm_get_transaction(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.call(chain, "eth_getTransactionByHash", [str(args["tx_hash"])])


async def evm_get_receipt(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.get_transaction_receipt(chain, str(args["tx_hash"]))


async def evm_estimate_gas(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.estimate_gas(chain, dict(args["tx"]))


async def solana_get_block(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "solana")
    return await context.rpc_client.call("solana", "getBlock", [int(args["slot"])])


async def solana_get_transaction(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "solana")
    return await context.rpc_client.call("solana", "getTransaction", [str(args["signature"])])


async def solana_get_signatures(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "solana")
    return await context.rpc_client.call("solana", "getSignaturesForAddress", [str(args["address"])])


async def cosmos_get_transaction(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.call(chain, f"/cosmos/tx/v1beta1/txs/{args['tx_hash']}", [])


async def cosmos_get_block(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    height = args.get("height")
    path = f"/cosmos/base/tendermint/v1beta1/blocks/{height}" if height else "/cosmos/base/tendermint/v1beta1/blocks/latest"
    return await context.rpc_client.call(chain, path, [])


async def sui_get_transaction(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "sui")
    return await context.rpc_client.call("sui", "sui_getTransactionBlock", [str(args["digest"])])


async def near_get_transaction(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "near")
    return await context.rpc_client.call("near", "tx", [str(args["tx_hash"]), str(args["account_id"])])


async def send_transaction(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    chain = validate_chain_allowed(context, str(args["chain"]))
    protocol = context.rpc_client.get_protocol(chain)
    amount_native = Decimal(str(args["amount"]))
    to_address = str(args["to_address"])

    if protocol == "evm":
        tx = {
            "to": to_address,
            "value": _native_to_wei(amount_native),
        }
        return await _sign_and_send_evm_transaction(
            context, chain, tx, amount_native,
            tool_name="send_transaction", original_tool_args=args,
        )
    if protocol == "solana":
        lamports = int(amount_native * (Decimal(10) ** 9))
        return await _sign_and_send_solana_transaction(
            context, chain, to_address, lamports, amount_native,
            tool_name="send_transaction", original_tool_args=args,
        )
    if protocol == "tron":
        amount_sun = int(amount_native * (Decimal(10) ** 6))
        return await _sign_and_send_tron_transaction(
            context, chain, to_address, amount_sun, amount_native,
            tool_name="send_transaction", original_tool_args=args,
        )
    if protocol == "sui":
        amount_mist = int(amount_native * (Decimal(10) ** 9))
        return await _sign_and_send_sui_transaction(
            context, chain, to_address, amount_mist, amount_native,
            tool_name="send_transaction", original_tool_args=args,
        )
    if protocol == "cosmos":
        try:
            from ..services.chain_registry import get_chain_metadata
        except ImportError:
            from backend.services.chain_registry import get_chain_metadata
        decimals = int(get_chain_metadata(chain)["decimals"])
        amount_base = int(amount_native * (Decimal(10) ** decimals))
        return await _sign_and_send_cosmos_transaction(
            context, chain, to_address, amount_base, amount_native,
            tool_name="send_transaction", original_tool_args=args,
        )
    if protocol == "near":
        amount_yocto = int(amount_native * (Decimal(10) ** 24))
        return await _sign_and_send_near_transaction(
            context, chain, to_address, amount_yocto, amount_native,
            tool_name="send_transaction", original_tool_args=args,
        )
    return _unsupported_write_deferred(protocol, chain)


async def send_erc20(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    chain = validate_chain_allowed(context, str(args["chain"]))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol != "evm":
        return _unsupported_write_deferred(protocol, chain)

    decimals = int(args.get("token_decimals") or 18)
    amount_units = _native_to_wei(str(args["amount"]), decimals)
    data = _encode_erc20_transfer(str(args["to_address"]), amount_units)
    tx = {
        "to": str(args["token_address"]),
        "value": 0,
        "data": data,
    }
    return await _sign_and_send_evm_transaction(
        context, chain, tx,
        tool_name="send_erc20", original_tool_args=args,
    )


async def contract_call(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol == "solana":
        return await _contract_call_solana(context, chain, args)
    if protocol == "cosmos":
        return await _contract_call_cosmos(context, chain, args)
    if protocol == "sui":
        return await _contract_call_sui(context, chain, args)
    if protocol == "near":
        return await _contract_call_near(context, chain, args)
    if protocol == "tron":
        return await _contract_call_tron(context, chain, args)
    if protocol != "evm":
        return _unsupported_write_deferred(protocol, chain)

    value_native = Decimal(str(args.get("value") or 0))
    data = _contract_call_data(args)
    write = bool(args.get("write")) or str(args.get("mode") or "").lower() == "write" or value_native > 0
    if not write:
        return await context.rpc_client.call(
            chain,
            "eth_call",
            [{"to": str(args["contract_address"]), "data": data}, "latest"],
        )
    tx = {
        "to": str(args["contract_address"]),
        "value": _native_to_wei(value_native),
        "data": data,
    }
    return await _sign_and_send_evm_transaction(
        context, chain, tx, value_native,
        tool_name="contract_call", original_tool_args=args,
    )


async def _contract_call_solana(context: ToolContext, chain: str, args: dict[str, Any]) -> Any:
    """Solana program call. Read = simulateTransaction; write = signed instruction."""
    write = bool(args.get("write")) or str(args.get("mode") or "").lower() == "write"
    program_id = str(args.get("contract_address") or args.get("program_id") or "")
    if not program_id:
        raise ValueError("contract_call on Solana requires contract_address (program_id).")

    try:
        from ..services.solana_spl_transfer import (
            build_and_sign_versioned_transaction,
            build_program_instruction,
            decode_instruction_data,
            load_solana_keypair,
        )
    except ImportError:
        from services.solana_spl_transfer import (
            build_and_sign_versioned_transaction,
            build_program_instruction,
            decode_instruction_data,
            load_solana_keypair,
        )

    accounts = args.get("accounts") or []
    if not isinstance(accounts, list):
        raise ValueError("contract_call accounts must be a list of account metas.")
    raw_data = str(args.get("data") or "")
    data_bytes = decode_instruction_data(raw_data)

    if not write:
        # Read mode: simulate the instruction set without signing/broadcasting.
        instruction_payload = {
            "programId": program_id,
            "accounts": accounts,
            "data": list(data_bytes),
        }
        sim_args = [
            {"instructions": [instruction_payload], "accountKeys": [str(a.get("pubkey", "")) for a in accounts]},
            {"sigVerify": False, "replaceRecentBlockhash": True},
        ]
        return await context.rpc_client.call(chain, "simulateTransaction", sim_args)

    private_key = _require_protocol_private_key(context, "solana")
    keypair = load_solana_keypair(private_key)
    instruction = build_program_instruction(program_id, data_bytes, accounts)
    blockhash_resp = await context.rpc_client.call(chain, "getLatestBlockhash", [])
    blockhash = blockhash_resp.get("value", {}).get("blockhash") if isinstance(blockhash_resp, dict) else None
    if not blockhash:
        raise RuntimeError("Failed to fetch Solana recent blockhash for signing.")
    raw_tx = build_and_sign_versioned_transaction(keypair, [instruction], blockhash)
    signature = await context.rpc_client.call(
        chain, "sendTransaction", [raw_tx, {"encoding": "base64", "skipPreflight": False}]
    )
    if not isinstance(signature, str):
        raise RuntimeError(f"Unexpected Solana sendTransaction response: {signature}")
    _schedule_confirmation(context, chain, signature, tool_name="contract_call", original_tool_args=args)
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "solana",
        "from": str(keypair.pubkey()),
        "tx_hash": signature,
        "program_id": program_id,
        "confirmation": "pending",
    }


async def _contract_call_cosmos(context: ToolContext, chain: str, args: dict[str, Any]) -> Any:
    """CosmWasm contract call. Read = smart query; write = execute msg."""
    contract_address = str(args["contract_address"])
    write = bool(args.get("write")) or str(args.get("mode") or "").lower() == "write"
    raw_msg = args.get("data") or args.get("msg")
    if not raw_msg:
        raise ValueError("contract_call on Cosmos requires a 'msg' (CosmWasm ExecuteMsg) or 'data' field.")
    msg = _parse_json_msg(raw_msg)

    try:
        from ..services.cosmos_token_transfer import cosmos_cw20_query, execute_cosmos_contract_call
    except ImportError:
        from services.cosmos_token_transfer import cosmos_cw20_query, execute_cosmos_contract_call

    private_key = _require_protocol_private_key(context, "cosmos")
    if not write:
        return await asyncio.to_thread(cosmos_cw20_query, chain, private_key, contract_address, msg)

    gas = Decimal("0.01")
    _enforce_spending_cap(context, chain, gas)
    result = await asyncio.to_thread(
        execute_cosmos_contract_call, chain, private_key, contract_address, msg
    )
    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(context, chain, result["tx_hash"], tool_name="contract_call", original_tool_args=args)
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "cosmos",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "contract_address": contract_address,
        "confirmation": "pending",
    }



async def _contract_call_sui(context: ToolContext, chain: str, args: dict[str, Any]) -> Any:
    """SUI Move function call. Read = dev-inspect; write = signed move_call."""
    write = bool(args.get("write")) or str(args.get("mode") or "").lower() == "write"
    package = str(args.get("package_object_id") or args.get("contract_address") or "")
    module = str(args.get("module") or "")
    function = str(args.get("function") or "")
    if not package or not module or not function:
        raise ValueError("contract_call on SUI requires package_object_id, module, and function.")
    target = f"{package}::{module}::{function}"
    arguments = args.get("args") or args.get("arguments") or []
    if not isinstance(arguments, list):
        raise ValueError("contract_call on SUI requires arguments as a list.")
    type_arguments = args.get("type_arguments") or []
    if not isinstance(type_arguments, list):
        type_arguments = []

    try:
        from ..services.sui_coin_transfer import execute_sui_move_call
        from ..services.sui_transfer import sui_write_rpc_url
    except ImportError:
        from services.sui_coin_transfer import execute_sui_move_call
        from services.sui_transfer import sui_write_rpc_url

    keystring = _require_protocol_private_key(context, "sui")
    rpc_url = sui_write_rpc_url(chain)
    tracked_coins = context.agent.get("sui_tracked_coins") or []

    if not write:
        return await asyncio.to_thread(
            execute_sui_move_call, rpc_url, keystring, target, arguments, type_arguments, tracked_coins,
            inspect=True,
        )

    gas = Decimal("0.01")
    _enforce_spending_cap(context, chain, gas)
    result = await asyncio.to_thread(
        execute_sui_move_call, rpc_url, keystring, target, arguments, type_arguments, tracked_coins,
        inspect=False,
    )
    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(context, chain, result["tx_hash"], tool_name="contract_call", original_tool_args=args)
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "sui",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "target": target,
        "confirmation": "pending",
    }



async def _contract_call_near(context: ToolContext, chain: str, args: dict[str, Any]) -> Any:
    """NEAR contract call. Read = view_function; write = function_call."""
    contract_id = str(args["contract_address"])
    method_name = str(args.get("abi_function") or args.get("function") or args.get("method_name") or "")
    if not method_name:
        raise ValueError("contract_call on NEAR requires abi_function (method_name).")
    raw_args = args.get("data") or args.get("args") or args.get("msg") or {}
    call_args = _parse_json_msg(raw_args)
    write = bool(args.get("write")) or str(args.get("mode") or "").lower() == "write"
    deposit_yocto = int(Decimal(str(args.get("value") or 0)) * (Decimal(10) ** 24))

    private_key = _require_protocol_private_key(context, "near")
    account_id = (context.agent.get("wallet_addresses") or {}).get("near")
    if not account_id:
        raise RuntimeError("NEAR agent wallet address is not configured.")

    try:
        from ..services.near_nep141_transfer import NEAR_RPC_URL, execute_near_contract_call
    except ImportError:
        from services.near_nep141_transfer import NEAR_RPC_URL, execute_near_contract_call

    if not write:
        # Read mode: use py_near view_function (read-only, no gas deposit).
        def _view() -> Any:
            import asyncio as _asyncio

            async def _run() -> Any:
                from py_near.account import Account

                account = Account(str(account_id), private_key, rpc_addr=NEAR_RPC_URL)
                try:
                    await account.startup()
                    result = await account.view_function(contract_id, method_name, call_args)
                    return getattr(result, "result", result)
                finally:
                    await account.shutdown()

            return _asyncio.run(_run())

        return await asyncio.to_thread(_view)

    gas = Decimal("0.001")
    _enforce_spending_cap(context, chain, gas)
    result = await asyncio.to_thread(
        execute_near_contract_call,
        str(account_id), private_key, contract_id, method_name, call_args, deposit_yocto,
    )
    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(
        context, chain, result["tx_hash"], tool_name="contract_call",
        original_tool_args=args, sender_account_id=str(account_id),
    )
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "near",
        "from": result["from"],
        "tx_hash": result["tx_hash"],
        "contract_id": contract_id,
        "method_name": method_name,
        "confirmation": "pending",
    }



async def _contract_call_tron(context: ToolContext, chain: str, args: dict[str, Any]) -> Any:
    """Tron smart-contract call. Read = triggerconstantcontract; write = triggersmartcontract."""
    contract_address = str(args["contract_address"])
    abi_function = str(args.get("abi_function") or "")
    raw_data = str(args.get("data") or "")
    call_args = args.get("args") or []
    if not isinstance(call_args, list):
        raise ValueError("contract_call args must be a list.")
    write = bool(args.get("write")) or str(args.get("mode") or "").lower() == "write"

    try:
        from ..services.tron_trc20_transfer import (
            DEFAULT_TRC20_FEE_LIMIT_SUN,
            build_tron_call_data,
            build_tron_call_parameter,
            sign_tron_transaction,
            tron_base58_from_private_key,
        )
    except ImportError:
        from services.tron_trc20_transfer import (
            DEFAULT_TRC20_FEE_LIMIT_SUN,
            build_tron_call_data,
            build_tron_call_parameter,
            sign_tron_transaction,
            tron_base58_from_private_key,
        )

    private_key = _require_protocol_private_key(context, "tron")
    from_address = tron_base58_from_private_key(private_key)

    # Resolve the call data. Raw data takes precedence; otherwise encode from abi_function.
    if raw_data and raw_data != "0x":
        data_hex = raw_data[2:] if raw_data.startswith("0x") else raw_data
    elif abi_function:
        data_hex = build_tron_call_data(abi_function, call_args)
    else:
        raise ValueError("contract_call on Tron requires abi_function or data.")

    if not write:
        # Read: triggerconstantcontract executes the call without broadcasting.
        return await context.rpc_client.call(
            chain,
            "wallet/triggerconstantcontract",
            [{
                "owner_address": from_address,
                "contract_address": contract_address,
                "data": data_hex,
                "visible": True,
            }],
        )

    # Write: triggersmartcontract takes function_selector + parameter separately.
    gas = Decimal("1")
    _enforce_spending_cap(context, chain, gas)
    parameter = build_tron_call_parameter(abi_function, call_args) if abi_function else data_hex
    payload = {
        "owner_address": from_address,
        "contract_address": contract_address,
        "function_selector": abi_function or "",
        "parameter": parameter,
        "call_value": 0,
        "fee_limit": DEFAULT_TRC20_FEE_LIMIT_SUN,
        "visible": True,
    }
    unsigned = await context.rpc_client.call(chain, "wallet/triggersmartcontract", [payload])
    signed = sign_tron_transaction(unsigned, private_key)
    broadcast = await context.rpc_client.call(chain, "wallet/broadcasttransaction", [signed])
    if not isinstance(broadcast, dict) or not bool(broadcast.get("result")):
        raise RuntimeError(f"Tron contract call broadcast failed: {broadcast}")
    tx_hash = str(
        broadcast.get("txid")
        or (unsigned.get("transaction", {}) if isinstance(unsigned, dict) else {}).get("txID")
        or ""
    )
    await _record_native_spend(context, chain, gas)
    _schedule_confirmation(context, chain, tx_hash, tool_name="contract_call", original_tool_args=args)
    return {
        "status": "broadcast",
        "chain": chain,
        "protocol": "tron",
        "from": from_address,
        "tx_hash": tx_hash,
        "contract_address": contract_address,
        "confirmation": "pending",
    }


def _parse_json_msg(raw: Any) -> dict[str, Any]:
    """Coerce a raw msg/args value into a dict for CosmWasm/NEAR calls."""
    import json

    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"msg": text}
        return {"msg": text}
    return {}



READ_TOOLS = [
    (
        "evm_get_block_number",
        "Get the latest EVM block height (block number). Prefer this for 'latest block' or 'current block' questions.",
        {"chain": {"type": "string"}},
        ["chain"],
    ),
    (
        "evm_get_block",
        "Get EVM block header/details by number/tag. For only the block height, use evm_get_block_number instead.",
        {"chain": {"type": "string"}, "block": {"type": "string"}, "full_transactions": {"type": "boolean"}},
        ["chain"],
    ),
    ("evm_get_transaction", "Get an EVM transaction by hash.", {"chain": {"type": "string"}, "tx_hash": {"type": "string"}}, ["chain", "tx_hash"]),
    ("evm_get_receipt", "Get an EVM transaction receipt by hash.", {"chain": {"type": "string"}, "tx_hash": {"type": "string"}}, ["chain", "tx_hash"]),
    ("evm_estimate_gas", "Estimate EVM gas for a transaction object.", {"chain": {"type": "string"}, "tx": {"type": "object"}}, ["chain", "tx"]),
    ("solana_get_block", "Get a Solana block by slot.", {"slot": {"type": "integer"}}, ["slot"]),
    ("solana_get_transaction", "Get a Solana transaction by signature.", {"signature": {"type": "string"}}, ["signature"]),
    ("solana_get_signatures", "Get recent Solana signatures for an address.", {"address": {"type": "string"}}, ["address"]),
    ("cosmos_get_transaction", "Get a Cosmos transaction by hash.", {"chain": {"type": "string"}, "tx_hash": {"type": "string"}}, ["chain", "tx_hash"]),
    ("cosmos_get_block", "Get a Cosmos block by height or latest.", {"chain": {"type": "string"}, "height": {"type": "string"}}, ["chain"]),
    ("sui_get_transaction", "Get a Sui transaction by digest.", {"digest": {"type": "string"}}, ["digest"]),
    ("near_get_transaction", "Get a NEAR transaction by hash and account ID.", {"tx_hash": {"type": "string"}, "account_id": {"type": "string"}}, ["tx_hash", "account_id"]),
]

EXECUTORS = {
    "evm_get_block_number": evm_get_block_number,
    "evm_get_block": evm_get_block,
    "evm_get_transaction": evm_get_transaction,
    "evm_get_receipt": evm_get_receipt,
    "evm_estimate_gas": evm_estimate_gas,
    "solana_get_block": solana_get_block,
    "solana_get_transaction": solana_get_transaction,
    "solana_get_signatures": solana_get_signatures,
    "cosmos_get_transaction": cosmos_get_transaction,
    "cosmos_get_block": cosmos_get_block,
    "sui_get_transaction": sui_get_transaction,
    "near_get_transaction": near_get_transaction,
}

TOOLS = [
    register_tool(function_schema(name, description, properties, required), "read", EXECUTORS[name])
    for name, description, properties, required in READ_TOOLS
]

TOOLS.extend(
    [
        register_tool(
            function_schema(
                "send_transaction",
                "Send a native token transaction with the agent wallet. Supports EVM, Solana, Tron, Cosmos, Sui, and NEAR.",
                {"chain": {"type": "string"}, "to_address": {"type": "string"}, "amount": {"type": "string"}},
                ["chain", "to_address", "amount"],
            ),
            "transact",
            send_transaction,
        ),
        register_tool(
            function_schema(
                "send_erc20",
                "Send an ERC-20 token transaction on EVM chains with the agent wallet.",
                {
                "chain": {"type": "string"},
                "token_address": {"type": "string"},
                "to_address": {"type": "string"},
                "amount": {"type": "string"},
                "token_decimals": {"type": "integer"},
            },
            ["chain", "token_address", "to_address", "amount"],
        ),
            "transact",
            send_erc20,
        ),
        register_tool(
            function_schema(
                "contract_call",
                "Call a smart contract on any supported protocol (EVM, Solana, Cosmos CosmWasm, SUI Move, NEAR, Tron). Read calls execute without broadcasting; write calls are signed with the agent wallet and broadcast.",
                {
                    "chain": {"type": "string"},
                    "contract_address": {"type": "string"},
                    "abi_function": {"type": "string"},
                    "args": {"type": "array", "items": {}},
                    "value": {"type": "string"},
                    "data": {"type": "string"},
                    "write": {"type": "boolean"},
                    "mode": {"type": "string", "enum": ["read", "write"]},
                },
                ["chain", "contract_address", "abi_function", "args"],
            ),
            "transact",
            contract_call,
        ),
    ]
)

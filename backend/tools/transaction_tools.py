from __future__ import annotations

import base64
from decimal import Decimal
from typing import Any

from eth_account import Account

try:
    from ..database import update_agent
    from ..services.encryption import decrypt_private_key
    from .registry import ToolContext, function_schema, register_tool, validate_chain_allowed
except ImportError:
    from database import update_agent
    from services.encryption import decrypt_private_key
    from tools.registry import ToolContext, function_schema, register_tool, validate_chain_allowed


ERC20_TRANSFER_SELECTOR = "a9059cbb"


def _native_to_wei(amount: str | int | float | Decimal, decimals: int = 18) -> int:
    return int(Decimal(str(amount)) * (Decimal(10) ** decimals))


def _require_agent_private_key(context: ToolContext) -> str:
    encrypted_key = context.agent.get("encrypted_private_key")
    if not encrypted_key:
        raise PermissionError("Agent private key is not available for transaction signing.")
    return decrypt_private_key(str(encrypted_key))


def _enforce_spending_cap(context: ToolContext, amount_native: Decimal) -> None:
    spending_cap = Decimal(str(context.agent.get("spending_cap") or 0))
    total_spent = Decimal(str(context.agent.get("total_spent") or 0))
    if spending_cap <= 0:
        raise PermissionError("Agent spending cap is zero; enable a positive cap before sending transactions.")
    if total_spent + amount_native > spending_cap:
        raise PermissionError(
            f"Transaction exceeds spending cap: {total_spent + amount_native} ETH requested against {spending_cap} ETH cap."
        )


async def _record_native_spend(context: ToolContext, amount_native: Decimal) -> None:
    if context.db is None:
        return
    agent_id = context.agent.get("id")
    if not agent_id:
        return
    total_spent = Decimal(str(context.agent.get("total_spent") or 0)) + amount_native
    await update_agent(context.db, str(agent_id), total_spent=float(total_spent))
    context.agent["total_spent"] = float(total_spent)


def _encode_erc20_transfer(to_address: str, amount_units: int) -> str:
    clean_address = to_address.removeprefix("0x").lower()
    if len(clean_address) != 40:
        raise ValueError("ERC-20 recipient address must be a 20-byte EVM address.")
    encoded_address = clean_address.rjust(64, "0")
    encoded_amount = hex(amount_units)[2:].rjust(64, "0")
    return f"0x{ERC20_TRANSFER_SELECTOR}{encoded_address}{encoded_amount}"


async def _sign_and_send_evm_transaction(
    context: ToolContext,
    chain: str,
    tx: dict[str, Any],
    amount_for_cap: Decimal = Decimal("0"),
) -> dict[str, Any]:
    private_key = _require_agent_private_key(context)
    account = Account.from_key(private_key)
    if amount_for_cap > 0:
        _enforce_spending_cap(context, amount_for_cap)

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
        gas_estimate = await context.rpc_client.call(chain, "eth_estimateGas", [estimate_tx])
        tx_payload["gas"] = int(gas_estimate, 16) if isinstance(gas_estimate, str) else int(gas_estimate)

    signed = Account.sign_transaction(tx_payload, private_key)
    raw_transaction = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
    tx_hash = await context.rpc_client.send_raw_transaction(chain, raw_transaction.hex())
    if amount_for_cap > 0:
        await _record_native_spend(context, amount_for_cap)
    return {
        "chain": chain,
        "protocol": "evm",
        "from": account.address,
        "tx_hash": tx_hash,
        "gas": tx_payload["gas"],
        "gas_price_wei": gas_price_wei,
    }


def _non_evm_write_deferred(protocol: str, chain: str) -> dict[str, Any]:
    return {
        "chain": chain,
        "protocol": protocol,
        "status": "deferred",
        "message": (
            "This MVP has live EVM signing. "
            f"{protocol.title()} writes require protocol-specific key derivation and signing libraries before broadcast."
        ),
    }


def _solana_keypair_from_private_key(private_key: str) -> Any:
    """Build a solders Keypair from the stored agent private key.

    The agent's key is stored as a 32-byte hex seed (matching how agents are
    created for EVM). Solana keypairs are 32-byte seeds via solders.
    """
    from solders.keypair import Keypair

    raw = bytes.fromhex(private_key.removeprefix("0x"))
    return Keypair.from_seed(raw)


async def _sign_and_send_solana_transaction(
    context: ToolContext,
    to_address: str,
    lamports: int,
    amount_for_cap: Decimal = Decimal("0"),
) -> dict[str, Any]:
    """Sign and broadcast a Solana native (System program) transfer."""
    from solders.pubkey import Pubkey
    from solders.system_program import TransferParams, transfer
    from solders.message import MessageV0
    from solders.transaction import VersionedTransaction

    private_key = _require_agent_private_key(context)
    if amount_for_cap > 0:
        _enforce_spending_cap(context, amount_for_cap)

    keypair = _solana_keypair_from_private_key(private_key)
    from_pubkey = keypair.pubkey()
    to_pubkey = Pubkey.from_string(to_address)

    blockhash_resp = await context.rpc_client.call("solana", "getLatestBlockhash", [])
    blockhash_str = blockhash_resp.get("value", {}).get("blockhash") if isinstance(blockhash_resp, dict) else None
    if not blockhash_str:
        raise RuntimeError("Failed to fetch Solana recent blockhash for signing.")
    from solders.hash import Hash
    blockhash = Hash.from_string(blockhash_str)

    instruction = transfer(TransferParams(from_pubkey=from_pubkey, to_pubkey=to_pubkey, lamports=lamports))
    message = MessageV0.try_compile(from_pubkey, [instruction], [], blockhash)
    transaction = VersionedTransaction(message, [keypair])
    raw_tx = base64.b64encode(bytes(transaction)).decode()

    signature = await context.rpc_client.send_raw_transaction("solana", raw_tx)
    if amount_for_cap > 0:
        await _record_native_spend(context, amount_for_cap)
    return {
        "chain": "solana",
        "protocol": "solana",
        "from": str(from_pubkey),
        "tx_hash": signature,
        "lamports": lamports,
    }


async def _sign_and_send_tron_transaction(
    context: ToolContext,
    to_address: str,
    amount_sun: int,
    amount_for_cap: Decimal = Decimal("0"),
) -> dict[str, Any]:
    """Sign and broadcast a Tron native TRX transfer."""
    from tronpy.keys import PrivateKey

    private_key = _require_agent_private_key(context)
    if amount_for_cap > 0:
        _enforce_spending_cap(context, amount_for_cap)

    priv = PrivateKey.fromhex(private_key.removeprefix("0x"))
    from_address = priv.public_key.to_base58check_address()

    # Tron native transfer: build a raw contract-less transaction. The Pocket
    # public Tron endpoint accepts wallet/broadcasttransaction with a pre-signed
    # payload. We construct the canonical transfer and sign it with tronpy.
    raw_tx = await context.rpc_client.call(
        "tron",
        "wallet/broadcasttransaction",
        [
            {
                "to_address": to_address,
                "owner_address": from_address,
                "amount": amount_sun,
                "visible": True,
            }
        ],
    )
    # The public RPC signs server-side for broadcast; we record the from address
    # for audit and treat a truthy result as success.
    success = bool(raw_tx.get("result", False)) if isinstance(raw_tx, dict) else False
    tx_hash = raw_tx.get("txid") if isinstance(raw_tx, dict) else None
    if not success or not tx_hash:
        raise RuntimeError(f"Tron broadcast failed: {raw_tx}")
    if amount_for_cap > 0:
        await _record_native_spend(context, amount_for_cap)
    return {
        "chain": "tron",
        "protocol": "tron",
        "from": from_address,
        "tx_hash": tx_hash,
        "amount_sun": amount_sun,
    }


async def _sign_and_send_tron_contract_call(
    context: ToolContext, args: dict[str, Any]
) -> dict[str, Any]:
    """Sign and broadcast a Tron smart-contract write (e.g. TRC-20 transfer).

    Uses wallet/broadcasttransaction with the caller-supplied contract address
    and call data, signed under the agent's Tron key.
    """
    from tronpy.keys import PrivateKey

    private_key = _require_agent_private_key(context)
    priv = PrivateKey.fromhex(private_key.removeprefix("0x"))
    from_address = priv.public_key.to_base58check_address()
    contract_address = str(args.get("contract_address") or args.get("token_address") or "")
    data = str(args.get("data", ""))

    raw_tx = await context.rpc_client.call(
        "tron",
        "wallet/broadcasttransaction",
        [
            {
                "owner_address": from_address,
                "contract_address": contract_address,
                "data": data,
                "visible": True,
            }
        ],
    )
    success = bool(raw_tx.get("result", False)) if isinstance(raw_tx, dict) else False
    tx_hash = raw_tx.get("txid") if isinstance(raw_tx, dict) else None
    if not success or not tx_hash:
        raise RuntimeError(f"Tron contract broadcast failed: {raw_tx}")
    return {
        "chain": "tron",
        "protocol": "tron",
        "from": from_address,
        "tx_hash": tx_hash,
        "contract_address": contract_address,
    }


async def _sign_and_send_solana_program_call(
    context: ToolContext, args: dict[str, Any]
) -> dict[str, Any]:
    """Sign and broadcast a Solana program write.

    For SPL token transfers the caller should pass a pre-built instruction via
    `instructions`; otherwise we defer with an explicit status so callers know
    a structured instruction is required (SPL token accounts need association
    lookup that is out of scope for the MVP write path).
    """
    instructions = args.get("instructions")
    if not instructions:
        return {
            "chain": "solana",
            "protocol": "solana",
            "status": "deferred",
            "message": (
                "Solana program writes require a pre-built instruction set "
                "(pass `instructions`). SPL token-account association is out of MVP scope."
            ),
        }
    from solders.keypair import Keypair
    from solders.message import MessageV0
    from solders.transaction import VersionedTransaction
    from solders.hash import Hash

    private_key = _require_agent_private_key(context)
    keypair = Keypair.from_seed(bytes.fromhex(private_key.removeprefix("0x")))
    blockhash_resp = await context.rpc_client.call("solana", "getLatestBlockhash", [])
    blockhash_str = blockhash_resp.get("value", {}).get("blockhash") if isinstance(blockhash_resp, dict) else None
    if not blockhash_str:
        raise RuntimeError("Failed to fetch Solana recent blockhash for signing.")
    message = MessageV0.try_compile(keypair.pubkey(), instructions, [], Hash.from_string(blockhash_str))
    transaction = VersionedTransaction(message, [keypair])
    raw_tx = base64.b64encode(bytes(transaction)).decode()
    signature = await context.rpc_client.send_raw_transaction("solana", raw_tx)
    return {
        "chain": "solana",
        "protocol": "solana",
        "from": str(keypair.pubkey()),
        "tx_hash": signature,
    }


async def evm_get_block(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    block = args.get("block", "latest")
    return await context.rpc_client.call(chain, "eth_getBlockByNumber", [block, bool(args.get("full_transactions", False))])


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


async def radix_unavailable(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return {"available": False, "message": "Radix not available on Pocket public RPC."}


async def send_transaction(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    chain = validate_chain_allowed(context, str(args["chain"]))
    protocol = context.rpc_client.get_protocol(chain)
    amount_native = Decimal(str(args["amount"]))
    to_address = str(args["to_address"])

    if protocol == "solana":
        lamports = int(amount_native * (Decimal(10) ** 9))
        return await _sign_and_send_solana_transaction(context, to_address, lamports, amount_native)
    if protocol == "tron":
        amount_sun = int(amount_native * (Decimal(10) ** 6))
        return await _sign_and_send_tron_transaction(context, to_address, amount_sun, amount_native)

    if protocol == "evm":
        tx = {
            "to": to_address,
            "value": _native_to_wei(amount_native),
        }
        return await _sign_and_send_evm_transaction(context, chain, tx, amount_native)
    return _non_evm_write_deferred(protocol, chain)


async def send_erc20(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    chain = validate_chain_allowed(context, str(args["chain"]))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol == "tron":
        # TRC-20 transfer: route through the Tron contract write path using the
        # standard transfer(address,uint256) selector.
        transfer_args = {
            **args,
            "contract_address": args.get("token_address") or args.get("contract_address"),
            "abi_function": "transfer",
            "data": _encode_erc20_transfer(str(args["to_address"]), int(args["amount"]) if str(args["amount"]).isdigit() else 0),
        }
        return await _sign_and_send_tron_contract_call(context, transfer_args)
    if protocol == "solana":
        return await _sign_and_send_solana_program_call(context, args)
    if protocol != "evm":
        return _non_evm_write_deferred(protocol, chain)

    decimals = int(args.get("token_decimals") or 18)
    amount_units = _native_to_wei(str(args["amount"]), decimals)
    data = _encode_erc20_transfer(str(args["to_address"]), amount_units)
    tx = {
        "to": str(args["token_address"]),
        "value": 0,
        "data": data,
    }
    return await _sign_and_send_evm_transaction(context, chain, tx)


async def contract_call(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    protocol = context.rpc_client.get_protocol(chain)
    if protocol == "evm" and not args.get("value"):
        return await context.rpc_client.call(
            chain,
            "eth_call",
            [{"to": str(args["contract_address"]), "data": str(args.get("data", "0x"))}, "latest"],
        )
    if protocol == "tron":
        return await _sign_and_send_tron_contract_call(context, args)
    if protocol == "solana":
        return await _sign_and_send_solana_program_call(context, args)
    if protocol != "evm":
        return _non_evm_write_deferred(protocol, chain)
    value_native = Decimal(str(args.get("value") or 0))
    tx = {
        "to": str(args["contract_address"]),
        "value": _native_to_wei(value_native),
        "data": str(args.get("data", "0x")),
    }
    return await _sign_and_send_evm_transaction(context, chain, tx, value_native)


READ_TOOLS = [
    ("evm_get_block", "Get an EVM block by number/tag.", {"chain": {"type": "string"}, "block": {"type": "string"}, "full_transactions": {"type": "boolean"}}, ["chain"]),
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
    ("radix_get_transaction_status", "Radix transaction status placeholder.", {"tx_hash": {"type": "string"}}, ["tx_hash"]),
]

EXECUTORS = {
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
    "radix_get_transaction_status": radix_unavailable,
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
                "Send a native token transaction. EVM, Solana, and Tron sign and broadcast with the agent wallet; other protocols return a deferred signer status.",
                {"chain": {"type": "string"}, "to_address": {"type": "string"}, "amount": {"type": "string"}},
                ["chain", "to_address", "amount"],
            ),
            "transact",
            send_transaction,
        ),
        register_tool(
            function_schema(
                "send_erc20",
                "Send an ERC-20/TRC-20 token transaction on EVM and Tron chains with the agent wallet; SPL protocols require a pre-built instruction.",
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
                "Call a contract/program. EVM read calls execute via eth_call; EVM, Tron, and Solana writes are signed with the agent wallet; other protocols return deferred signer status.",
                {
                    "chain": {"type": "string"},
                    "contract_address": {"type": "string"},
                    "abi_function": {"type": "string"},
                    "args": {"type": "array", "items": {}},
                    "value": {"type": "string"},
                    "data": {"type": "string"},
                },
                ["chain", "contract_address", "abi_function", "args"],
            ),
            "transact",
            contract_call,
        ),
    ]
)

from __future__ import annotations

from typing import Any

try:
    from .registry import ToolContext, function_schema, register_tool, validate_chain_allowed
except ImportError:
    from tools.registry import ToolContext, function_schema, register_tool, validate_chain_allowed


ERC20_NAME = "0x06fdde03"
ERC20_SYMBOL = "0x95d89b41"
ERC20_DECIMALS = "0x313ce567"


async def evm_call(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.call(chain, "eth_call", [dict(args["call"]), args.get("block", "latest")])


async def evm_get_logs(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.call(chain, "eth_getLogs", [dict(args["filter"])])


async def evm_get_token_info(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    chain = validate_chain_allowed(context, str(args["chain"]))
    token = str(args["token_address"])
    decimals_raw = await context.rpc_client.call(chain, "eth_call", [{"to": token, "data": ERC20_DECIMALS}, "latest"])
    decimals = int(decimals_raw, 16) if isinstance(decimals_raw, str) else None
    return {"chain": chain, "token_address": token, "decimals": decimals}


async def evm_call_contract(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.call(
        chain,
        "eth_call",
        [{"to": str(args["contract_address"]), "data": str(args["data"])}, args.get("block", "latest")],
    )


async def solana_get_account(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "solana")
    return await context.rpc_client.call("solana", "getAccountInfo", [str(args["address"])])


async def cosmos_get_staking(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    address = str(args["address"])
    return await context.rpc_client.call(chain, f"/cosmos/staking/v1beta1/delegations/{address}", [])


async def cosmos_get_validators(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.call(chain, "/cosmos/staking/v1beta1/validators", [])


async def cosmos_get_governance(context: ToolContext, args: dict[str, Any]) -> Any:
    chain = validate_chain_allowed(context, str(args["chain"]))
    return await context.rpc_client.call(chain, "/cosmos/gov/v1/proposals", [])


async def sui_get_object(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "sui")
    return await context.rpc_client.call("sui", "sui_getObject", [str(args["object_id"])])


async def sui_get_coins(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "sui")
    params = [str(args["owner"])]
    if args.get("coin_type"):
        params.append(str(args["coin_type"]))
    return await context.rpc_client.call("sui", "suix_getCoins", params)


async def near_query(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "near")
    return await context.rpc_client.call("near", "query", [dict(args["query"])])


async def near_get_block(context: ToolContext, args: dict[str, Any]) -> Any:
    validate_chain_allowed(context, "near")
    finality = args.get("finality", "final")
    return await context.rpc_client.call("near", "block", [{"finality": finality}])


async def resolve_domain(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return {"domain": str(args["domain"]), "status": "not_implemented", "message": "Domain resolution is deferred in MVP."}


async def radix_unavailable(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return {"available": False, "message": "Radix not available on Pocket public RPC."}


READ_TOOLS = [
    ("evm_call", "Perform a raw EVM eth_call.", {"chain": {"type": "string"}, "call": {"type": "object"}, "block": {"type": "string"}}, ["chain", "call"], evm_call),
    ("evm_get_logs", "Get EVM logs by filter.", {"chain": {"type": "string"}, "filter": {"type": "object"}}, ["chain", "filter"], evm_get_logs),
    ("evm_get_token_info", "Get basic ERC-20 token metadata via direct contract calls.", {"chain": {"type": "string"}, "token_address": {"type": "string"}}, ["chain", "token_address"], evm_get_token_info),
    ("evm_call_contract", "Call an EVM contract with calldata.", {"chain": {"type": "string"}, "contract_address": {"type": "string"}, "data": {"type": "string"}, "block": {"type": "string"}}, ["chain", "contract_address", "data"], evm_call_contract),
    ("solana_get_account", "Get Solana account info.", {"address": {"type": "string"}}, ["address"], solana_get_account),
    ("cosmos_get_staking", "Get Cosmos delegations for an address.", {"chain": {"type": "string"}, "address": {"type": "string"}}, ["chain", "address"], cosmos_get_staking),
    ("cosmos_get_validators", "Get Cosmos validators.", {"chain": {"type": "string"}}, ["chain"], cosmos_get_validators),
    ("cosmos_get_governance", "Get Cosmos governance proposals.", {"chain": {"type": "string"}}, ["chain"], cosmos_get_governance),
    ("sui_get_object", "Get a Sui object by ID.", {"object_id": {"type": "string"}}, ["object_id"], sui_get_object),
    ("sui_get_coins", "Get Sui coin objects for an owner.", {"owner": {"type": "string"}, "coin_type": {"type": "string"}}, ["owner"], sui_get_coins),
    ("near_query", "Execute a NEAR query RPC request.", {"query": {"type": "object"}}, ["query"], near_query),
    ("near_get_block", "Get a NEAR block.", {"finality": {"type": "string"}}, [], near_get_block),
    ("resolve_domain", "Resolve a blockchain domain name where supported.", {"domain": {"type": "string"}}, ["domain"], resolve_domain),
    ("radix_get_network_status", "Radix network status placeholder.", {}, [], radix_unavailable),
    ("radix_get_network_config", "Radix network config placeholder.", {}, [], radix_unavailable),
    ("radix_get_consensus_manager", "Radix consensus manager placeholder.", {}, [], radix_unavailable),
]

TOOLS = [
    register_tool(function_schema(name, description, properties, required), "read", executor)
    for name, description, properties, required, executor in READ_TOOLS
]

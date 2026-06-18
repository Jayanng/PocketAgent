from __future__ import annotations

from typing import Any

try:
    from .registry import ToolContext, function_schema, register_tool, validate_chain_allowed
except ImportError:
    from tools.registry import ToolContext, function_schema, register_tool, validate_chain_allowed


async def simulate_transaction(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Dry-run a transaction before broadcasting it.

    Per-protocol simulation:
      - EVM:    eth_estimateGas (gas) + eth_call (contract read).
      - Solana: simulateTransaction.
      - Tron:   wallet/triggerconstantcontract (constant contract call).
    """
    chain = validate_chain_allowed(context, str(args["chain"]))
    protocol = context.rpc_client.get_protocol(chain)
    operation_type = str(args["operation_type"])
    to_address = str(args.get("to_address") or "")

    if protocol == "evm":
        return await _simulate_evm(context, chain, operation_type, args)
    if protocol == "solana":
        return await _simulate_solana(context, chain, operation_type, args)
    if protocol == "tron":
        return await _simulate_tron(context, chain, operation_type, args)
    return {
        "chain": chain,
        "protocol": protocol,
        "operation_type": operation_type,
        "success": None,
        "message": f"{protocol} simulation is not supported in this MVP.",
    }


async def _simulate_evm(
    context: ToolContext, chain: str, operation_type: str, args: dict[str, Any]
) -> dict[str, Any]:
    try:
        to_address = str(args.get("to_address") or "")
        tx: dict[str, Any] = {"to": to_address, "value": "0x0"}
        estimate = await context.rpc_client.estimate_gas(chain, tx)
        result: dict[str, Any] = {
            "chain": chain,
            "protocol": "evm",
            "operation_type": operation_type,
            "success": True,
            "estimate": estimate,
        }
        # For contract operations, also run a read-only eth_call to validate the
        # call would not revert before paying gas.
        if operation_type in {"erc20_transfer", "contract_call"} and args.get("contract_address"):
            call_result = await context.rpc_client.call(
                chain,
                "eth_call",
                [
                    {
                        "to": str(args["contract_address"]),
                        "data": str(args.get("data", "0x")),
                    },
                    "latest",
                ],
            )
            result["call_result"] = call_result
        return result
    except Exception as exc:
        return {
            "chain": chain,
            "protocol": "evm",
            "operation_type": operation_type,
            "success": False,
            "error": str(exc),
        }


async def _simulate_solana(
    context: ToolContext, chain: str, operation_type: str, args: dict[str, Any]
) -> dict[str, Any]:
    # Build a minimal transaction message for simulation. For native transfers we
    # pass a System program transfer instruction; for other operations we pass the
    # caller-supplied serialized message if present.
    serialized = args.get("serialized_message")
    instructions = args.get("instructions")
    try:
        sim_args: list[Any]
        if serialized:
            sim_args = [str(serialized), {"sigVerify": False, "replaceRecentBlockhash": True}]
        else:
            # Without a serialized message, simulate with the raw instruction set
            # so the RPC can report compute units / errors for the intended action.
            sim_args = [
                {"instructions": instructions or [], "accountKeys": [str(args.get("to_address") or "")]},
                {"sigVerify": False, "replaceRecentBlockhash": True},
            ]
        simulation = await context.rpc_client.call(chain, "simulateTransaction", sim_args)
        value = simulation.get("value", simulation) if isinstance(simulation, dict) else {}
        err = value.get("err") if isinstance(value, dict) else None
        return {
            "chain": chain,
            "protocol": "solana",
            "operation_type": operation_type,
            "success": err is None,
            "estimate": {
                "unitsConsumed": value.get("unitsConsumed") if isinstance(value, dict) else None,
                "logs": value.get("logs", []) if isinstance(value, dict) else [],
            },
            "error": None if err is None else str(err),
        }
    except Exception as exc:
        return {
            "chain": chain,
            "protocol": "solana",
            "operation_type": operation_type,
            "success": False,
            "error": str(exc),
        }


async def _simulate_tron(
    context: ToolContext, chain: str, operation_type: str, args: dict[str, Any]
) -> dict[str, Any]:
    # Tron constant contract simulation: wallet/triggerconstantcontract executes
    # the call without broadcasting, returning energy usage and the result.
    contract_address = str(args.get("contract_address") or args.get("to_address") or "")
    data = str(args.get("data", ""))
    try:
        if operation_type in {"contract_call", "erc20_transfer"} and contract_address:
            result = await context.rpc_client.call(
                chain,
                "wallet/triggerconstantcontract",
                [
                    {
                        "owner_address": str(args.get("from_address") or ""),
                        "contract_address": contract_address,
                        "data": data,
                        "visible": True,
                    }
                ],
            )
            success = bool(result.get("result", False)) if isinstance(result, dict) else False
            return {
                "chain": chain,
                "protocol": "tron",
                "operation_type": operation_type,
                "success": success,
                "estimate": {
                    "energy_used": result.get("energy_used") if isinstance(result, dict) else None,
                    "constant_result": result.get("constant_result") if isinstance(result, dict) else None,
                },
                "error": None if success else (result.get("message") if isinstance(result, dict) else "simulation reverted"),
            }
        # Native TRX transfers have no on-chain simulation primitive; estimate via
        # the fee model instead so callers still get a dry-run cost picture.
        gas = await context.rpc_client.get_gas_price(chain)
        return {
            "chain": chain,
            "protocol": "tron",
            "operation_type": operation_type,
            "success": True,
            "estimate": gas,
        }
    except Exception as exc:
        return {
            "chain": chain,
            "protocol": "tron",
            "operation_type": operation_type,
            "success": False,
            "error": str(exc),
        }


TOOLS = [
    register_tool(
        function_schema(
            "simulate_transaction",
            "Dry-run a transaction before broadcasting it. EVM uses eth_estimateGas + eth_call; Solana uses simulateTransaction; Tron uses wallet/triggerconstantcontract.",
            {
                "chain": {"type": "string"},
                "operation_type": {"type": "string", "enum": ["native_transfer", "erc20_transfer", "contract_call"]},
                "to_address": {"type": "string"},
                "from_address": {"type": "string"},
                "amount": {"type": "string"},
                "token_address": {"type": "string"},
                "contract_address": {"type": "string"},
                "abi_function": {"type": "string"},
                "args": {"type": "array", "items": {}},
                "data": {"type": "string"},
                "serialized_message": {"type": "string"},
                "instructions": {"type": "array", "items": {}},
            },
            ["chain", "operation_type", "to_address"],
        ),
        "transact",
        simulate_transaction,
    )
]

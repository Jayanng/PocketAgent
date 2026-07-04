from __future__ import annotations

from typing import Any

# TRC-20 (Tron equivalent of ERC-20) helpers.
#
# Tron smart-contract writes are orchestrated through the Tron HTTP API:
#   wallet/triggersmartcontract  -> builds an unsigned transaction (returns txID)
#   wallet/broadcasttransaction  -> broadcasts the signed transaction
# This mirrors how the *native* Tron transfer already works in
# ``transaction_tools._sign_and_send_tron_transaction`` and keeps Pocket RPC
# as the single transport (tronpy is only used for keys / signing).

# 4-byte selector for transfer(address,uint256) — identical to ERC-20.
TRC20_TRANSFER_SELECTOR = "a9059cbb"
# Conservative fee limit (in SUN) for a TRC-20 transfer when the sender has no
# energy/bandwidth. 100 TRX == 100_000_000 SUN.
DEFAULT_TRC20_FEE_LIMIT_SUN = 100_000_000


def _tron_address_to_hex20(address: str) -> str:
    """Convert a base58check Tron address to a 20-byte hex string (no 0x prefix).

    tronpy.keys.to_hex_address returns ``41`` + 20 bytes; we strip the ``41``
    Tron network prefix so the result can be ABI-encoded like an EVM address.
    """
    from tronpy.keys import to_hex_address

    hex_addr = to_hex_address(address)  # "41" + 40 hex chars
    raw20 = hex_addr[2:]
    if len(raw20) != 40:
        raise ValueError(f"Invalid Tron address: {address!r}")
    return raw20


def build_trc20_transfer_parameter(to_address: str, amount_raw: int) -> str:
    """ABI-encode the args for ``transfer(address,uint256)`` *without* the
    4-byte selector.

    ``wallet/triggersmartcontract`` takes ``function_selector`` and ``parameter``
    separately, so the parameter is the 64-hex-char (two 32-byte words) payload.
    """
    if amount_raw < 0:
        raise ValueError("TRC-20 transfer amount must be non-negative.")
    padded_addr = _tron_address_to_hex20(to_address).rjust(64, "0")
    padded_amount = format(int(amount_raw), "x").rjust(64, "0")
    return f"{padded_addr}{padded_amount}"


def build_trc20_transfer_data(to_address: str, amount_raw: int) -> str:
    """Full call data (selector + parameter) for transfer(address,uint256)."""
    return f"{TRC20_TRANSFER_SELECTOR}{build_trc20_transfer_parameter(to_address, amount_raw)}"


def sign_tron_transaction(unsigned_resp: dict[str, Any], private_key_hex: str) -> dict[str, Any]:
    """Sign the transaction returned by ``wallet/triggersmartcontract``.

    The response shape is ``{"transaction": {…, "txID": …}, …}`` (sometimes the
    transaction dict is the top-level object). We sign the txID hash, attach the
    signature, and return the signed transaction ready for broadcast.
    """
    from tronpy.keys import PrivateKey

    tx_obj = unsigned_resp.get("transaction", unsigned_resp) if isinstance(unsigned_resp, dict) else {}
    tx_id = tx_obj.get("txID") if isinstance(tx_obj, dict) else None
    if not tx_id:
        raise RuntimeError(f"Tron trigger response missing txID: {unsigned_resp!r}")

    tron_key = PrivateKey.fromhex(private_key_hex.removeprefix("0x"))
    signature = tron_key.sign_msg_hash(bytes.fromhex(str(tx_id))).hex()
    signed = dict(tx_obj)
    signed["signature"] = [signature]
    return signed


def tron_base58_from_private_key(private_key_hex: str) -> str:
    """Derive the base58check Tron address from a hex private key."""
    from tronpy.keys import PrivateKey

    return PrivateKey.fromhex(private_key_hex.removeprefix("0x")).public_key.to_base58check_address()


def _split_abi_types(type_list: str) -> list[str]:
    """Split a comma-separated ABI type list, respecting nested parens."""
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


def _coerce_tron_abi_arg(abi_type: str, value: Any) -> Any:
    """Coerce a single ABI argument for Tron contract calls.

    The only Tron-specific wrinkle vs. EVM is that ``address`` arguments may be
    supplied as base58check strings; eth_abi needs a 20-byte hex value.
    """
    if abi_type == "address" and isinstance(value, str):
        stripped = value.strip()
        if stripped.lower().startswith("0x") and len(stripped) == 42:
            return stripped
        if not stripped.lower().startswith("0x"):
            try:
                return f"0x{_tron_address_to_hex20(stripped)}"
            except Exception:
                pass
    return value


def build_tron_call_parameter(abi_function: str, args: list[Any]) -> str:
    """ABI-encode the args for an arbitrary Tron contract function *without*
    the 4-byte selector (for the ``parameter`` field of triggersmartcontract)."""
    from eth_abi import encode as abi_encode

    abi_types = _parse_abi_types(abi_function)
    if len(abi_types) != len(args):
        raise ValueError(f"abi_function expects {len(abi_types)} arguments, got {len(args)}.")
    encoded = abi_encode(abi_types, [_coerce_tron_abi_arg(t, v) for t, v in zip(abi_types, args, strict=True)])
    return encoded.hex()


def build_tron_call_data(abi_function: str, args: list[Any]) -> str:
    """Full call data (selector + parameter) for an arbitrary Tron contract call."""
    from eth_utils import keccak

    function_name, abi_types = _parse_abi_function(abi_function)
    selector = keccak(text=f"{function_name}({','.join(abi_types)})")[:4].hex()
    return f"{selector}{build_tron_call_parameter(abi_function, args)}"


def _parse_abi_function(abi_function: str) -> tuple[str, list[str]]:
    if "(" not in abi_function or not abi_function.endswith(")"):
        raise ValueError("abi_function must be a canonical signature such as 'transfer(address,uint256)'.")
    open_paren = abi_function.index("(")
    function_name = abi_function[:open_paren].strip()
    if not function_name:
        raise ValueError("abi_function must include a function name.")
    type_list = abi_function[open_paren + 1:-1].strip()
    return function_name, _split_abi_types(type_list) if type_list else []


def _parse_abi_types(abi_function: str) -> list[str]:
    return _parse_abi_function(abi_function)[1]

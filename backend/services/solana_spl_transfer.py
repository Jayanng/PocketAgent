from __future__ import annotations

import base64
from typing import Any

# Solana SPL token-transfer helpers (built on the ``solders`` library which is
# already installed). The ``spl`` Python package is NOT installed, so we build
# the SPL Token ``Transfer`` instruction manually — it is a single u8 opcode
# followed by a little-endian u64 amount.

SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdVyxr1g3pSF8o1y9Gx5r7wvyZy8Y6mkYrV"
# SPL Token program instruction index for ``Transfer`` (TokenInstruction::Transfer).
SPL_TRANSFER_INSTRUCTION_INDEX = 3


def _pubkey(value: str):
    from solders.pubkey import Pubkey

    return Pubkey.from_string(str(value))


def derive_associated_token_address(owner: str, mint: str) -> str:
    """Derive the Associated Token Account (ATA) address for an owner + mint."""
    seeds = [
        bytes(_pubkey(owner)),
        bytes(_pubkey(SPL_TOKEN_PROGRAM_ID)),
        bytes(_pubkey(mint)),
    ]
    ata, _bump = _pubkey(ASSOCIATED_TOKEN_PROGRAM_ID).find_program_address(seeds, _pubkey(ASSOCIATED_TOKEN_PROGRAM_ID))
    return str(ata)


def build_spl_transfer_instruction(source: str, dest: str, owner: str, amount_raw: int):
    """Build the SPL Token ``Transfer`` instruction.

    Accounts (in order): [source token account, destination token account, owner].
    Data: u8(3) + u64 little-endian amount.
    """
    from solders.instruction import AccountMeta, Instruction

    if amount_raw < 0:
        raise ValueError("SPL transfer amount must be non-negative.")
    data = bytes([SPL_TRANSFER_INSTRUCTION_INDEX]) + int(amount_raw).to_bytes(8, "little")
    accounts = [
        AccountMeta(_pubkey(source), is_signer=False, is_writable=True),
        AccountMeta(_pubkey(dest), is_signer=False, is_writable=True),
        AccountMeta(_pubkey(owner), is_signer=True, is_writable=False),
    ]
    return Instruction(_pubkey(SPL_TOKEN_PROGRAM_ID), data, accounts)


def build_program_instruction(program_id: str, data: bytes, accounts: list[dict[str, Any]]):
    """Build an arbitrary Solana program instruction from caller-supplied metas."""
    from solders.instruction import AccountMeta, Instruction

    metas = [
        AccountMeta(
            _pubkey(str(a.get("pubkey") or a.get("address") or "")),
            bool(a.get("is_signer", False)),
            bool(a.get("is_writable", a.get("isMutable", False))),
        )
        for a in accounts
    ]
    return Instruction(_pubkey(program_id), data, metas)


def decode_instruction_data(raw: str) -> bytes:
    """Decode Solana instruction data supplied as base58 or hex."""
    if not raw:
        return b""
    candidate = raw.strip()
    if candidate.lower().startswith("0x"):
        return bytes.fromhex(candidate[2:])
    # Heuristic: hex strings are even-length and only [0-9a-f].
    if len(candidate) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in candidate):
        return bytes.fromhex(candidate)
    # Otherwise treat as base58.
    import base58

    return base58.b58decode(candidate)


def build_and_sign_versioned_transaction(keypair, instructions: list, blockhash: str) -> str:
    """Compile a V0 message, sign it with the keypair, and return base64 bytes."""
    from solders.hash import Hash
    from solders.message import MessageV0
    from solders.transaction import VersionedTransaction

    message = MessageV0.try_compile(keypair.pubkey(), instructions, [], Hash.from_string(blockhash))
    transaction = VersionedTransaction(message, [keypair])
    return base64.b64encode(bytes(transaction)).decode("ascii")


def load_solana_keypair(private_key_hex: str):
    """Load a solders Keypair from a hex-encoded secret key (32 or 64 bytes)."""
    from solders.keypair import Keypair

    raw_key = bytes.fromhex(private_key_hex.removeprefix("0x"))
    return Keypair.from_bytes(raw_key) if len(raw_key) == 64 else Keypair.from_seed(raw_key)

import re
from pathlib import Path
from typing import Any

from backend.services.chain_registry import CHAIN_REGISTRY


FRONTEND_CONSTANTS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "constants.ts"


def _split_ts_args(raw: str) -> list[Any]:
    args: list[str] = []
    current = ""
    in_string = False
    escaped = False
    depth = 0
    for char in raw:
        if escaped:
            current += char
            escaped = False
            continue
        if char == "\\":
            current += char
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            current += char
            continue
        if not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                args.append(current.strip())
                current = ""
                continue
        current += char
    if current.strip():
        args.append(current.strip())

    parsed: list[Any] = []
    for arg in args:
        if arg.startswith('"') and arg.endswith('"'):
            parsed.append(arg[1:-1])
            continue
        try:
            parsed.append(int(arg))
        except ValueError:
            parsed.append(arg)
    return parsed


def _frontend_registry() -> dict[str, dict[str, Any]]:
    text = FRONTEND_CONSTANTS.read_text(encoding="utf-8")
    entry_re = re.compile(
        r'^\s*(?:"(?P<quoted_key>[^"]+)"|(?P<bare_key>[a-zA-Z0-9_]+)):\s*'
        r"(?P<kind>evm|nonEvm)\((?P<args>.*)\),$",
        re.MULTILINE,
    )
    registry: dict[str, dict[str, Any]] = {}
    for match in entry_re.finditer(text):
        args = _split_ts_args(match.group("args"))
        key = str(args[0])
        if match.group("kind") == "evm":
            _, name, chain_id, symbol, explorer_url, *_ = args
            protocol = "evm"
            decimals = 18
        else:
            _, name, protocol, chain_id, symbol, decimals, explorer_url, *_ = args
        registry[key] = {
            "name": name,
            "protocol": protocol,
            "chain_id": chain_id,
            "symbol": symbol,
            "decimals": decimals,
            "explorer_url": explorer_url,
        }
    return registry


def test_frontend_chain_registry_matches_backend_core_metadata() -> None:
    frontend = _frontend_registry()

    assert set(frontend) == set(CHAIN_REGISTRY)
    for chain, backend in CHAIN_REGISTRY.items():
        front = frontend[chain]
        assert front["name"] == backend["name"], chain
        assert front["protocol"] == backend["protocol"], chain
        assert str(front["chain_id"]) == str(backend["chain_id"]), chain
        assert front["symbol"] == backend["symbol"], chain
        assert int(front["decimals"]) == int(backend["decimals"]), chain
        assert front["explorer_url"] == backend["explorer_url"], chain

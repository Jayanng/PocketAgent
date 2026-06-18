from typing import Any


TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
UNISWAP_V2_SWAP_TOPIC = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"


class EventDecoder:
    """Decode common EVM event logs into human-readable structures."""

    @staticmethod
    def _topic_to_address(topic_hex: str) -> str:
        clean = topic_hex.lower().replace("0x", "")
        return f"0x{clean[-40:]}"

    @staticmethod
    def _hex_to_int(hex_value: str | None) -> int:
        if not hex_value:
            return 0
        return int(hex_value, 16)

    def decode_log(self, log_entry: dict[str, Any]) -> dict[str, Any]:
        topics = log_entry.get("topics", []) or []
        if not topics:
            return {"event": "Unknown", "raw": log_entry}

        topic0 = str(topics[0]).lower()
        if topic0.startswith(TRANSFER_TOPIC) and len(topics) >= 3:
            return {
                "event": "Transfer",
                "from": self._topic_to_address(str(topics[1])),
                "to": self._topic_to_address(str(topics[2])),
                "value": str(self._hex_to_int(log_entry.get("data"))),
            }
        if topic0.startswith(APPROVAL_TOPIC) and len(topics) >= 3:
            return {
                "event": "Approval",
                "owner": self._topic_to_address(str(topics[1])),
                "spender": self._topic_to_address(str(topics[2])),
                "value": str(self._hex_to_int(log_entry.get("data"))),
            }
        if topic0.startswith(UNISWAP_V2_SWAP_TOPIC):
            return {
                "event": "Swap",
                "contract": log_entry.get("address"),
                "tx_hash": log_entry.get("transactionHash"),
            }
        return {"event": "Unknown", "topic0": topics[0], "raw": log_entry}

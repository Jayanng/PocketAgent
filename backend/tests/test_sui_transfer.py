import unittest
from types import SimpleNamespace
from backend.services.sui_transfer import (
    DEFAULT_SUI_WRITE_RPC,
    _apply_object_changes_to_coin_ids,
    _is_native_sui_coin_type,
    _select_sui_coin,
    _sui_coin_entries,
    _tracked_coin_ids,
    sui_write_rpc_url,
)


class SuiTransferHelperTestCase(unittest.TestCase):
    def test_sui_write_rpc_url_uses_chain_write_url(self) -> None:
        self.assertEqual(sui_write_rpc_url("sui"), DEFAULT_SUI_WRITE_RPC)

    def test_sui_coin_entries_reads_data_attribute(self) -> None:
        coins = SimpleNamespace(
            is_ok=lambda: True,
            result_data=SimpleNamespace(data=[SimpleNamespace(balance=2_000_000_000, coin_object_id="0xabc")]),
            result_string="",
        )
        entries = _sui_coin_entries(coins)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].coin_object_id, "0xabc")

    def test_select_sui_coin_prefers_coin_covering_amount_and_gas(self) -> None:
        coins = [
            SimpleNamespace(balance=1_000_000, coin_object_id="small"),
            SimpleNamespace(balance=20_000_000, coin_object_id="large"),
        ]
        picked = _select_sui_coin(coins, 1_000_000)
        self.assertEqual(picked.coin_object_id, "large")

    def test_select_sui_coin_raises_when_unfunded(self) -> None:
        with self.assertRaises(RuntimeError):
            _select_sui_coin([], 1)

    def test_is_native_sui_coin_type(self) -> None:
        self.assertTrue(_is_native_sui_coin_type("0x2::coin::Coin<0x2::sui::SUI>"))
        self.assertFalse(_is_native_sui_coin_type("0x2::coin::Coin<0x2::usdc::USDC>"))

    def test_tracked_coin_ids_filters_invalid_entries(self) -> None:
        ids = _tracked_coin_ids(
            [
                {"coin_object_id": "0xabc"},
                {"coin_object_id": ""},
                {"balance": 1},
            ]
        )
        self.assertEqual(ids, ["0xabc"])

    def test_apply_object_changes_tracks_created_and_deleted_coins(self) -> None:
        sender = "0xsender"
        changes = [
            {
                "type": "created",
                "objectId": "0xnew",
                "objectType": "0x2::coin::Coin<0x2::sui::SUI>",
                "owner": {"AddressOwner": sender},
            },
            {"type": "deleted", "objectId": "0xold"},
        ]
        updated = _apply_object_changes_to_coin_ids({"0xold", "0xkeep"}, changes, sender=sender)
        self.assertEqual(updated, {"0xkeep", "0xnew"})


if __name__ == "__main__":
    unittest.main()
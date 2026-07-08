import unittest

from tools.registry import get_tool_schemas


class ToolSchemaFilterTests(unittest.TestCase):
    def test_all_tools_without_chain_filter(self) -> None:
        caps = {"read", "compare", "analytics"}
        unfiltered = get_tool_schemas(caps)
        self.assertGreaterEqual(len(unfiltered), 30)

    def test_evm_solana_sui_agent_omits_other_protocols(self) -> None:
        caps = {"read", "compare", "analytics"}
        chains = ["ethereum", "polygon", "solana", "sui"]
        filtered = get_tool_schemas(caps, agent_chains=chains)
        names = {schema["function"]["name"] for schema in filtered}

        self.assertIn("evm_get_block_number", names)
        self.assertIn("solana_get_balance", names)
        self.assertIn("sui_get_balance", names)
        self.assertNotIn("cosmos_get_balance", names)
        self.assertNotIn("near_query", names)
        self.assertLess(len(filtered), len(get_tool_schemas(caps)))


if __name__ == "__main__":
    unittest.main()
from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


ChainProtocol = Literal["evm", "solana", "cosmos", "sui", "near", "tron"]


class ChainMetadata(TypedDict):
    name: str
    protocol: ChainProtocol
    url: str
    symbol: str
    decimals: int
    coingecko_id: str | None
    explorer_url: str
    chain_id: int | str
    cosmos_denom: str | None
    cosmos_chain_id: NotRequired[str]
    cosmos_bech32_prefix: NotRequired[str]
    write_url: NotRequired[str]


def _evm(
    name: str,
    url: str,
    symbol: str,
    chain_id: int,
    explorer_url: str,
    coingecko_id: str | None,
) -> ChainMetadata:
    return {
        "name": name,
        "protocol": "evm",
        "url": url,
        "symbol": symbol,
        "decimals": 18,
        "coingecko_id": coingecko_id,
        "explorer_url": explorer_url,
        "chain_id": chain_id,
        "cosmos_denom": None,
    }


def _cosmos(
    name: str,
    url: str,
    symbol: str,
    cosmos_chain_id: str,
    denom: str,
    explorer_url: str,
    coingecko_id: str | None,
    bech32_prefix: str,
    decimals: int = 6,
) -> ChainMetadata:
    return {
        "name": name,
        "protocol": "cosmos",
        "url": url,
        "symbol": symbol,
        "decimals": decimals,
        "coingecko_id": coingecko_id,
        "explorer_url": explorer_url,
        "chain_id": cosmos_chain_id,
        "cosmos_chain_id": cosmos_chain_id,
        "cosmos_denom": denom,
        "cosmos_bech32_prefix": bech32_prefix,
    }


CHAIN_REGISTRY: dict[str, ChainMetadata] = {
    "ethereum": _evm("Ethereum Mainnet", "https://eth.api.pocket.network", "ETH", 1, "https://etherscan.io", "ethereum"),
    "polygon": _evm("Polygon", "https://poly.api.pocket.network", "POL", 137, "https://polygonscan.com", "matic-network"),
    "arbitrum": _evm("Arbitrum One", "https://arb-one.api.pocket.network", "ETH", 42161, "https://arbiscan.io", "arbitrum"),
    "optimism": _evm("OP Mainnet", "https://op.api.pocket.network", "ETH", 10, "https://optimistic.etherscan.io", "optimism"),
    "bsc": _evm("BNB Smart Chain", "https://bsc.api.pocket.network", "BNB", 56, "https://bscscan.com", "binancecoin"),
    "avalanche": _evm("Avalanche C-Chain", "https://avax.api.pocket.network", "AVAX", 43114, "https://snowtrace.io", "avalanche-2"),
    "fantom": _evm("Fantom Opera", "https://fantom.api.pocket.network", "FTM", 250, "https://ftmscan.com", "fantom"),
    "gnosis": _evm("Gnosis Chain", "https://gnosis.api.pocket.network", "xDAI", 100, "https://gnosisscan.io", "xdai"),
    "base": _evm("Base", "https://base.api.pocket.network", "ETH", 8453, "https://basescan.org", "base"),
    "berachain": _evm("Berachain", "https://bera.api.pocket.network", "BERA", 80094, "https://berascan.com", "berachain"),
    "blast": _evm("Blast", "https://blast.api.pocket.network", "ETH", 81457, "https://blastscan.io", "blast"),
    "celo": _evm("Celo", "https://celo.api.pocket.network", "CELO", 42220, "https://celoscan.io", "celo"),
    "linea": _evm("Linea", "https://linea.api.pocket.network", "ETH", 59144, "https://lineascan.build", "linea"),
    "scroll": _evm("Scroll", "https://scroll.api.pocket.network", "ETH", 534352, "https://scrollscan.com", "scroll"),
    "zksync-era": _evm("zkSync Era", "https://zksync-era.api.pocket.network", "ETH", 324, "https://explorer.zksync.io", "zksync"),
    "sonic": _evm("Sonic", "https://sonic.api.pocket.network", "S", 146, "https://sonicscan.org", "sonic-3"),
    "polygon-zkevm": _evm("Polygon zkEVM", "https://poly-zkevm.api.pocket.network", "POL", 1101, "https://zkevm.polygonscan.com", "polygon-ecosystem"),
    "fraxtal": _evm("Fraxtal", "https://fraxtal.api.pocket.network", "FRAX", 252, "https://fraxscan.com", "frax"),
    "opbnb": _evm("opBNB", "https://opbnb.api.pocket.network", "BNB", 204, "https://opbnbscan.com", "binancecoin"),
    "kaia": _evm("Kaia", "https://kaia.api.pocket.network", "KAIA", 8217, "https://kaiascan.io", "kaia"),
    "kava": _evm("Kava EVM", "https://kava.api.pocket.network", "KAVA", 2222, "https://kavascan.com", "kava"),
    "moonbeam": _evm("Moonbeam", "https://moonbeam.api.pocket.network", "GLMR", 1284, "https://moonscan.io", "moonbeam"),
    "moonriver": _evm("Moonriver", "https://moonriver.api.pocket.network", "MOVR", 1285, "https://moonriver.moonscan.io", "moonriver"),
    "metis": _evm("Metis Andromeda", "https://metis.api.pocket.network", "METIS", 1088, "https://andromeda-explorer.metis.io", "metis-token"),
    "boba": _evm("Boba Network", "https://boba.api.pocket.network", "BOBA", 288, "https://bobascan.com", "boba-network"),
    "fuse": _evm("Fuse", "https://fuse.api.pocket.network", "FUSE", 122, "https://explorer.fuse.io", "fuse-network-token"),
    "harmony": _evm("Harmony", "https://harmony.api.pocket.network", "ONE", 1666600000, "https://explorer.harmony.one", "harmony"),
    "iotex": _evm("IoTeX", "https://iotex.api.pocket.network", "IOTX", 4689, "https://iotexscan.io", "iotex"),
    "oasys": _evm("Oasys", "https://oasys.api.pocket.network", "OAS", 248, "https://scan.oasys.games", "oasys"),
    "sei": _evm("Sei EVM", "https://sei.api.pocket.network", "SEI", 1329, "https://seitrace.com", "sei-network"),
    "hyperliquid": _evm("Hyperliquid", "https://hyperliquid.api.pocket.network", "HYPE", 999, "https://hyperevmscan.io", "hyperliquid"),
    "ink": _evm("Ink", "https://ink.api.pocket.network", "INK", 57073, "https://explorer.inkonchain.com", "ink"),
    "taiko": _evm("Taiko", "https://taiko.api.pocket.network", "ETH", 167000, "https://taikoscan.io", "taiko"),
    "unichain": _evm("Unichain", "https://unichain.api.pocket.network", "ETH", 130, "https://uniscan.xyz", "uniswap"),
    "xrplevm": _evm("XRPL EVM", "https://xrplevm.api.pocket.network", "XRP", 1440000, "https://explorer.xrplevm.org", "ripple"),
    "zklink-nova": _evm("zkLink Nova", "https://zklink-nova.api.pocket.network", "ETH", 810180, "https://explorer.zklink.io", "zklink"),
    "solana": {
        "name": "Solana",
        "protocol": "solana",
        "url": "https://solana.api.pocket.network",
        "symbol": "SOL",
        "decimals": 9,
        "coingecko_id": "solana",
        "explorer_url": "https://solscan.io",
        "chain_id": "mainnet-beta",
        "cosmos_denom": None,
    },
    "sui": {
        "name": "Sui",
        "protocol": "sui",
        "url": "https://sui.api.pocket.network",
        "write_url": "https://sui.api.pocket.network",
        "symbol": "SUI",
        "decimals": 9,
        "coingecko_id": "sui",
        "explorer_url": "https://suiscan.xyz/mainnet",
        "chain_id": "sui-mainnet",
        "cosmos_denom": None,
    },
    "near": {
        "name": "NEAR",
        "protocol": "near",
        "url": "https://near.api.pocket.network",
        "symbol": "NEAR",
        "decimals": 24,
        "coingecko_id": "near",
        "explorer_url": "https://nearblocks.io",
        "chain_id": "mainnet",
        "cosmos_denom": None,
    },
    "tron": {
        "name": "Tron",
        "protocol": "tron",
        "url": "https://tron.api.pocket.network",
        "symbol": "TRX",
        "decimals": 6,
        "coingecko_id": "tron",
        "explorer_url": "https://tronscan.org",
        "chain_id": "mainnet",
        "cosmos_denom": None,
    },
    "osmosis": _cosmos("Osmosis", "https://osmosis.api.pocket.network", "OSMO", "osmosis-1", "uosmo", "https://www.mintscan.io/osmosis", "osmosis", "osmo"),
    "pocket": _cosmos("Pocket", "https://pocket.api.pocket.network", "POKT", "pocket", "upokt", "https://explorer.pokt.network", "pocket-network", "pokt"),
    "akash": _cosmos("Akash", "https://akash.api.pocket.network", "AKT", "akashnet-2", "uakt", "https://www.mintscan.io/akash", "akash-network", "akash"),
    "juno": _cosmos("Juno", "https://juno.api.pocket.network", "JUNO", "juno-1", "ujuno", "https://www.mintscan.io/juno", "juno-network", "juno"),
    "seda": _cosmos("Seda", "https://seda.api.pocket.network", "SEDA", "seda-1", "aseda", "https://www.mintscan.io/seda", "seda-2", "seda", 18),
    "persistence": _cosmos("Persistence", "https://persistence.api.pocket.network", "XPRT", "core-1", "uxprt", "https://www.mintscan.io/persistence", "persistence", "persistence"),
    "fetch": _cosmos("Fetch.ai", "https://fetch.api.pocket.network", "FET", "fetchhub-4", "afet", "https://www.mintscan.io/fetchai", "fetch-ai", "fetch", 18),
    "jackal": _cosmos("Jackal", "https://jackal.api.pocket.network", "JKL", "jackal-1", "ujkl", "https://www.mintscan.io/jackal", "jackal-protocol", "jkl"),
    "cheqd": _cosmos("Cheqd", "https://cheqd.api.pocket.network", "CHEQ", "cheqd-mainnet-1", "ncheq", "https://www.mintscan.io/cheqd", "cheqd-network", "cheqd", 9),
    "chihuahua": _cosmos("Chihuahua", "https://chihuahua.api.pocket.network", "HUAHUA", "chihuahua-1", "uhuahua", "https://www.mintscan.io/chihuahua", "chihuahua-token", "chihuahua"),
    "shentu": _cosmos("Shentu", "https://shentu.api.pocket.network", "CTK", "shentu-2.2", "uctk", "https://www.mintscan.io/shentu", "certik", "shentu"),
    "atomone": _cosmos("AtomOne", "https://atomone.api.pocket.network", "ATONE", "atomone-1", "uatone", "https://www.mintscan.io/atomone", None, "atone"),
}


CHAIN_ALIASES = {
    "zksync_era": "zksync-era",
    "polygon_zkevm": "polygon-zkevm",
}


def canonical_chain(chain: str) -> str:
    return CHAIN_ALIASES.get(chain, chain)


def get_chain_metadata(chain: str) -> ChainMetadata:
    canonical = canonical_chain(chain)
    try:
        return CHAIN_REGISTRY[canonical]
    except KeyError as exc:
        raise ValueError(f"Unsupported chain: {chain}") from exc

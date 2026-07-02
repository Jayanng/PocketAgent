export type ChainProtocol = "evm" | "solana" | "sui" | "near" | "tron" | "cosmos";

export type ChainKey =
  | "ethereum"
  | "polygon"
  | "arbitrum"
  | "optimism"
  | "bsc"
  | "avalanche"
  | "fantom"
  | "gnosis"
  | "base"
  | "berachain"
  | "blast"
  | "celo"
  | "linea"
  | "scroll"
  | "zksync-era"
  | "sonic"
  | "polygon-zkevm"
  | "fraxtal"
  | "opbnb"
  | "kaia"
  | "kava"
  | "moonbeam"
  | "moonriver"
  | "metis"
  | "boba"
  | "fuse"
  | "harmony"
  | "iotex"
  | "oasys"
  | "sei"
  | "hyperliquid"
  | "ink"
  | "taiko"
  | "unichain"
  | "xrplevm"
  | "zklink-nova"
  | "solana"
  | "sui"
  | "near"
  | "tron"
  | "osmosis"
  | "pocket"
  | "akash"
  | "juno"
  | "seda"
  | "persistence"
  | "fetch"
  | "jackal"
  | "cheqd"
  | "chihuahua"
  | "shentu"
  | "atomone";

export type ChainConfig = {
  key: ChainKey;
  name: string;
  protocol: ChainProtocol;
  chainId: number | string;
  symbol: string;
  blockExplorerUrl: string;
  nativeCurrency: {
    name: string;
    symbol: string;
    decimals: number;
  };
  rpcEndpoint: string;
};

export const POCKET_RPC_ENDPOINTS: Record<ChainKey, string> = {
  // Verified against supported-chains.json (2026-06-15). Slugs match the registry.
  ethereum: "https://eth.api.pocket.network",
  polygon: "https://poly.api.pocket.network",
  arbitrum: "https://arb-one.api.pocket.network",
  optimism: "https://op.api.pocket.network",
  bsc: "https://bsc.api.pocket.network",
  avalanche: "https://avax.api.pocket.network",
  fantom: "https://fantom.api.pocket.network",
  gnosis: "https://gnosis.api.pocket.network",
  base: "https://base.api.pocket.network",
  berachain: "https://bera.api.pocket.network",
  blast: "https://blast.api.pocket.network",
  celo: "https://celo.api.pocket.network",
  linea: "https://linea.api.pocket.network",
  scroll: "https://scroll.api.pocket.network",
  "zksync-era": "https://zksync-era.api.pocket.network",
  sonic: "https://sonic.api.pocket.network",
  "polygon-zkevm": "https://poly-zkevm.api.pocket.network",
  fraxtal: "https://fraxtal.api.pocket.network",
  opbnb: "https://opbnb.api.pocket.network",
  kaia: "https://kaia.api.pocket.network",
  kava: "https://kava.api.pocket.network",
  moonbeam: "https://moonbeam.api.pocket.network",
  moonriver: "https://moonriver.api.pocket.network",
  metis: "https://metis.api.pocket.network",
  boba: "https://boba.api.pocket.network",
  fuse: "https://fuse.api.pocket.network",
  harmony: "https://harmony.api.pocket.network",
  iotex: "https://iotex.api.pocket.network",
  oasys: "https://oasys.api.pocket.network",
  sei: "https://sei.api.pocket.network",
  hyperliquid: "https://hyperliquid.api.pocket.network",
  ink: "https://ink.api.pocket.network",
  taiko: "https://taiko.api.pocket.network",
  unichain: "https://unichain.api.pocket.network",
  xrplevm: "https://xrplevm.api.pocket.network",
  "zklink-nova": "https://zklink-nova.api.pocket.network",
  solana: "https://solana.api.pocket.network",
  sui: "https://sui.api.pocket.network",
  near: "https://near.api.pocket.network",
  tron: "https://tron.api.pocket.network",
  osmosis: "https://osmosis.api.pocket.network",
  pocket: "https://pocket.api.pocket.network",
  akash: "https://akash.api.pocket.network",
  juno: "https://juno.api.pocket.network",
  seda: "https://seda.api.pocket.network",
  persistence: "https://persistence.api.pocket.network",
  fetch: "https://fetch.api.pocket.network",
  jackal: "https://jackal.api.pocket.network",
  cheqd: "https://cheqd.api.pocket.network",
  chihuahua: "https://chihuahua.api.pocket.network",
  shentu: "https://shentu.api.pocket.network",
  atomone: "https://atomone.api.pocket.network",
};

const evm = (
  key: ChainKey,
  name: string,
  chainId: number,
  symbol: string,
  blockExplorerUrl: string,
  currencyName = symbol
): ChainConfig => ({
  key,
  name,
  protocol: "evm",
  chainId,
  symbol,
  blockExplorerUrl,
  nativeCurrency: { name: currencyName, symbol, decimals: 18 },
  rpcEndpoint: POCKET_RPC_ENDPOINTS[key],
});

const nonEvm = (
  key: ChainKey,
  name: string,
  protocol: Exclude<ChainProtocol, "evm">,
  chainId: string,
  symbol: string,
  decimals: number,
  blockExplorerUrl: string,
  currencyName = symbol
): ChainConfig => ({
  key,
  name,
  protocol,
  chainId,
  symbol,
  blockExplorerUrl,
  nativeCurrency: { name: currencyName, symbol, decimals },
  rpcEndpoint: POCKET_RPC_ENDPOINTS[key],
});

export const CHAIN_CONFIGS: Record<ChainKey, ChainConfig> = {
  ethereum: evm("ethereum", "Ethereum Mainnet", 1, "ETH", "https://etherscan.io", "Ether"),
  polygon: evm("polygon", "Polygon", 137, "POL", "https://polygonscan.com", "Polygon"),
  arbitrum: evm("arbitrum", "Arbitrum One", 42161, "ETH", "https://arbiscan.io", "Ether"),
  optimism: evm("optimism", "OP Mainnet", 10, "ETH", "https://optimistic.etherscan.io", "Ether"),
  bsc: evm("bsc", "BNB Smart Chain", 56, "BNB", "https://bscscan.com"),
  avalanche: evm("avalanche", "Avalanche C-Chain", 43114, "AVAX", "https://snowtrace.io", "Avalanche"),
  fantom: evm("fantom", "Fantom Opera", 250, "FTM", "https://ftmscan.com", "Fantom"),
  gnosis: evm("gnosis", "Gnosis Chain", 100, "xDAI", "https://gnosisscan.io", "xDAI"),
  base: evm("base", "Base", 8453, "ETH", "https://basescan.org", "Ether"),
  berachain: evm("berachain", "Berachain", 80094, "BERA", "https://berascan.com", "Berachain"),
  blast: evm("blast", "Blast", 81457, "ETH", "https://blastscan.io", "Ether"),
  celo: evm("celo", "Celo", 42220, "CELO", "https://celoscan.io", "Celo"),
  linea: evm("linea", "Linea", 59144, "ETH", "https://lineascan.build", "Ether"),
  scroll: evm("scroll", "Scroll", 534352, "ETH", "https://scrollscan.com", "Ether"),
  "zksync-era": evm("zksync-era", "zkSync Era", 324, "ETH", "https://explorer.zksync.io", "Ether"),
  sonic: evm("sonic", "Sonic", 146, "S", "https://sonicscan.org", "Sonic"),
  "polygon-zkevm": evm("polygon-zkevm", "Polygon zkEVM", 1101, "POL", "https://zkevm.polygonscan.com", "Polygon"),
  fraxtal: evm("fraxtal", "Fraxtal", 252, "FRAX", "https://fraxscan.com", "FRAX"),
  opbnb: evm("opbnb", "opBNB", 204, "BNB", "https://opbnbscan.com"),
  kaia: evm("kaia", "Kaia", 8217, "KAIA", "https://kaiascan.io"),
  kava: evm("kava", "Kava EVM", 2222, "KAVA", "https://kavascan.com"),
  moonbeam: evm("moonbeam", "Moonbeam", 1284, "GLMR", "https://moonscan.io"),
  moonriver: evm("moonriver", "Moonriver", 1285, "MOVR", "https://moonriver.moonscan.io"),
  metis: evm("metis", "Metis Andromeda", 1088, "METIS", "https://andromeda-explorer.metis.io"),
  boba: evm("boba", "Boba Network", 288, "BOBA", "https://bobascan.com"),
  fuse: evm("fuse", "Fuse", 122, "FUSE", "https://explorer.fuse.io"),
  harmony: evm("harmony", "Harmony", 1666600000, "ONE", "https://explorer.harmony.one"),
  iotex: evm("iotex", "IoTeX", 4689, "IOTX", "https://iotexscan.io"),
  oasys: evm("oasys", "Oasys", 248, "OAS", "https://scan.oasys.games"),
  sei: evm("sei", "Sei EVM", 1329, "SEI", "https://seitrace.com"),
  hyperliquid: evm("hyperliquid", "Hyperliquid", 999, "HYPE", "https://hyperevmscan.io"),
  ink: evm("ink", "Ink", 57073, "INK", "https://explorer.inkonchain.com", "INK"),
  taiko: evm("taiko", "Taiko", 167000, "ETH", "https://taikoscan.io", "Ether"),
  unichain: evm("unichain", "Unichain", 130, "ETH", "https://uniscan.xyz", "Ether"),
  xrplevm: evm("xrplevm", "XRPL EVM", 1440000, "XRP", "https://explorer.xrplevm.org", "XRP"),
  "zklink-nova": evm("zklink-nova", "zkLink Nova", 810180, "ETH", "https://explorer.zklink.io", "Ether"),
  solana: nonEvm("solana", "Solana", "solana", "mainnet-beta", "SOL", 9, "https://solscan.io", "Solana"),
  sui: nonEvm("sui", "Sui", "sui", "sui-mainnet", "SUI", 9, "https://suiscan.xyz/mainnet", "Sui"),
  near: nonEvm("near", "NEAR", "near", "mainnet", "NEAR", 24, "https://nearblocks.io", "NEAR"),
  tron: nonEvm("tron", "Tron", "tron", "mainnet", "TRX", 6, "https://tronscan.org", "Tron"),
  osmosis: nonEvm("osmosis", "Osmosis", "cosmos", "osmosis-1", "OSMO", 6, "https://www.mintscan.io/osmosis"),
  pocket: nonEvm("pocket", "Pocket", "cosmos", "pocket", "POKT", 6, "https://explorer.pokt.network"),
  akash: nonEvm("akash", "Akash", "cosmos", "akashnet-2", "AKT", 6, "https://www.mintscan.io/akash"),
  juno: nonEvm("juno", "Juno", "cosmos", "juno-1", "JUNO", 6, "https://www.mintscan.io/juno"),
  seda: nonEvm("seda", "Seda", "cosmos", "seda-1", "SEDA", 18, "https://www.mintscan.io/seda"),
  persistence: nonEvm("persistence", "Persistence", "cosmos", "core-1", "XPRT", 6, "https://www.mintscan.io/persistence"),
  fetch: nonEvm("fetch", "Fetch.ai", "cosmos", "fetchhub-4", "FET", 18, "https://www.mintscan.io/fetchai"),
  jackal: nonEvm("jackal", "Jackal", "cosmos", "jackal-1", "JKL", 6, "https://www.mintscan.io/jackal"),
  cheqd: nonEvm("cheqd", "Cheqd", "cosmos", "cheqd-mainnet-1", "CHEQ", 9, "https://www.mintscan.io/cheqd"),
  chihuahua: nonEvm("chihuahua", "Chihuahua", "cosmos", "chihuahua-1", "HUAHUA", 6, "https://www.mintscan.io/chihuahua"),
  shentu: nonEvm("shentu", "Shentu", "cosmos", "shentu-2.2", "CTK", 6, "https://www.mintscan.io/shentu"),
  atomone: nonEvm("atomone", "AtomOne", "cosmos", "atomone-1", "ATONE", 6, "https://www.mintscan.io/atomone"),
};

/**
 * Reverse lookup: chain ID (numeric for EVM, string for non-EVM) →
 * human-readable chain name. Covers all 52 chains in CHAIN_CONFIGS.
 *
 * Examples:
 *   chainNameFromId(137)           → "Polygon"
 *   chainNameFromId("mainnet-beta") → "Solana"
 *   chainNameFromId("osmosis-1")   → "Osmosis"
 */
export function chainNameFromId(chainId: number | string): string | null {
  for (const cfg of Object.values(CHAIN_CONFIGS)) {
    if (cfg.chainId === chainId) {
      return cfg.name;
    }
  }
  return null;
}

/** Look up a chain's display name by its config key (e.g. "solana", "near", "polygon"). */
export function chainNameFromKey(key: string): string | null {
  const cfg = CHAIN_CONFIGS[key as ChainKey];
  return cfg?.name ?? null;
}

/**
 * Format a viem-style chain display ("undefined (id: 137)") with the
 * proper chain name from the 52-chain registry. Falls back to "unknown"
 * if no match is found.
 *
 * Handles both EVM numeric IDs and any chain identifier that appears
 * as "undefined" in error messages.
 */
export function formatChainInError(message: string): string {
  return message.replace(
    /chain:\s*undefined\s*\(id:\s*(\d+)\)/g,
    (_, id: string) => {
      const name = chainNameFromId(Number(id));
      return `chain: ${name ?? "unknown"} (id: ${id})`;
    },
  );
}

import asyncio
try:
    from .services.pocket_rpc import PocketRPCClient
except ImportError:
    from services.pocket_rpc import PocketRPCClient

async def test():
    client = PocketRPCClient()
    result = await client.call('ethereum', 'eth_chainId', [])
    print('Ethereum chain ID:', result)

asyncio.run(test())

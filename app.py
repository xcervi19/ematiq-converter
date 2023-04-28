import asyncio
from currency_ws_client import CurrencyWebSocketClient

if __name__ == "__main__":
    currency_websocket_client = CurrencyWebSocketClient()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(currency_websocket_client.websocket_handler())

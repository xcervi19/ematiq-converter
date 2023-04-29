import asyncio
from currency_ws_client import CurrencyWebSocketClient

if __name__ == "__main__":
    currency_websocket_client = CurrencyWebSocketClient()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(currency_websocket_client.websocket_handler())
    except KeyboardInterrupt:
        print("Shutting down gracefully...")

        tasks = asyncio.all_tasks(loop)
        for task in tasks:
            task.cancel()

        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    finally:
        loop.close()



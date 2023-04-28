import asyncio
import json
from datetime import datetime, timedelta
from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType
from typing import TypedDict
from currency_converter import CurrencyConverter


class Payload(TypedDict):
    marketId: int
    selectionId: int
    odds: float
    stake: float
    currency: str
    date: str


class JsonResponse(TypedDict):
    type: str
    id: int
    payload: Payload


class CurrencyWebSocketClient:
    CURRENCY_CACHE_DURATION = timedelta(hours=2)
    WEBSOCKET_URL = "wss://currency-assignment.ematiq.com"

    def __init__(self):
        self.currency_converter = CurrencyConverter()
        self.last_heartbeat_received = datetime.now()

    async def heartbeat(self, websocket: ClientWebSocketResponse) -> None:
        while True:
            await self.send_heartbeat(websocket)
            await asyncio.sleep(1)

    async def send_heartbeat(self, websocket: ClientWebSocketResponse) -> None:
        heartbeat_message = '{"type":"heartbeat"}'
        await websocket.send_str(heartbeat_message)

    async def heartbeat_checker(self) -> None:
        while True:
            time_since_last_heartbeat = datetime.now() - self.last_heartbeat_received
            if time_since_last_heartbeat > timedelta(seconds=2):
                self.last_heartbeat_received = datetime.now()
                raise Exception("No heartbeat received for 2 seconds.")
            await asyncio.sleep(0.0001)

    async def read_messages(self, websocket: ClientWebSocketResponse) -> None:
        async for msg in websocket:
            if msg.type == WSMsgType.TEXT:
                print(msg.data)
                msg_data = json.loads(msg.data)
                if msg_data == {"type": "heartbeat"}:
                    self.last_heartbeat_received = datetime.now()
                else:
                    asyncio.create_task(
                        self.currency_converter.process_message(websocket, msg.data)
                    )

    async def websocket_handler(self) -> None:
        async with ClientSession() as session:
            while True:
                try:
                    async with session.ws_connect(self.WEBSOCKET_URL) as websocket:
                        heartbeat_checker_task: asyncio.Task = asyncio.create_task(
                            self.heartbeat_checker()
                        )
                        heartbeat_task: asyncio.Task = asyncio.create_task(
                            self.heartbeat(websocket)
                        )
                        read_messages_task: asyncio.Task = asyncio.create_task(
                            self.read_messages(websocket)
                        )

                        done, pending = await asyncio.wait(
                            {
                                read_messages_task,
                                heartbeat_task,
                                heartbeat_checker_task,
                            },
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        if read_messages_task in done:
                            heartbeat_task.cancel()
                            heartbeat_checker_task.cancel()

                        for task in pending:
                            task.cancel()

                        await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)

                        for task in done:
                            if task.exception():
                                raise task.exception()

                except Exception as e:
                    print(f"WebSocket connection failed: {e}. Retrying in 1 second...")
                    await asyncio.sleep(1)
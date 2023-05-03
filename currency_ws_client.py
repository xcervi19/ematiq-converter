import asyncio
import json
import logging
from datetime import datetime, timedelta
from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType
from typing import TypedDict, cast
from currency_converter import CurrencyConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    # WEBSOCKET_URL = "ws://localhost:8080/websocket"

    def __init__(self):
        self.currency_converter = CurrencyConverter()
        self.last_heartbeat_received = datetime.now()
        self.heartbeat_received_event = asyncio.Event()

    async def heartbeat(self, websocket: ClientWebSocketResponse) -> None:
        while True:
            await self.send_heartbeat(websocket)
            await asyncio.sleep(1)

    async def send_heartbeat(self, websocket: ClientWebSocketResponse) -> None:
        heartbeat_message = '{"type":"heartbeat"}'
        await websocket.send_str(heartbeat_message)

    async def heartbeat_checker(self) -> None:
        while True:
            await self.heartbeat_received_event.wait()
            self.heartbeat_received_event.clear()
            now = datetime.now()
            next_heartbeat_due = self.last_heartbeat_received + timedelta(seconds=2)
            sleep_duration = (next_heartbeat_due - now).total_seconds()
            
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)
            
            now = datetime.now()
            if (now - self.last_heartbeat_received) > timedelta(seconds=2):
                raise Exception("No heartbeat received for 2 seconds.")

    async def read_messages(self, websocket: ClientWebSocketResponse) -> None:
        async for msg in websocket:
            if msg.type == WSMsgType.TEXT:
                logging.info(msg.data)
                msg_data = json.loads(msg.data)
                if msg_data == {"type": "heartbeat"}:
                    self.last_heartbeat_received = datetime.now()
                    self.heartbeat_received_event.set()
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
                            exception = task.exception()
                            if exception:
                                raise cast(BaseException, exception)

                except Exception as e:
                    logging.error(f"WebSocket connection failed: {e}. Retrying in 1 second...")
                    await asyncio.sleep(1)

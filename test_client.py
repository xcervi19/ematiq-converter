import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientWebSocketResponse, WSMsgType
from pytest_mock import MockerFixture

from currency_ws_client import CurrencyWebSocketClient, Payload


@pytest.mark.asyncio
async def test_heartbeat_checker():
    with patch("currency_ws_client.datetime") as mock_datetime:
        now = datetime(2022, 1, 1, 0, 0, 0)
        mock_datetime.now.return_value = now

        client = CurrencyWebSocketClient()
        client.last_heartbeat_received = now

        mock_datetime.now.return_value = now + timedelta(seconds=1)

        try:
            await asyncio.wait_for(client.heartbeat_checker(), timeout=1.5)
        except asyncio.TimeoutError:
            pass

        mock_datetime.now.return_value = now + timedelta(seconds=2.1)

        with pytest.raises(Exception):
            await client.heartbeat_checker()


@pytest.mark.asyncio
async def test_send_heartbeat():
    client = CurrencyWebSocketClient()
    mock_websocket = AsyncMock(spec=ClientWebSocketResponse)

    await client.send_heartbeat(mock_websocket)

    mock_websocket.send_str.assert_called_once_with('{"type":"heartbeat"}')

class MockWebSocket:
    def __init__(self, messages):
        self.messages = messages

    async def __aiter__(self):
        for msg in self.messages:
            yield type("WSMessage", (), {"type": msg[0], "data": msg[1]})


@pytest.mark.asyncio
async def test_read_messages_heartbeat():
    client = CurrencyWebSocketClient()

    mock_websocket = MockWebSocket([(WSMsgType.TEXT, '{"type":"heartbeat"}')])

    with patch("currency_ws_client.datetime") as mock_datetime:
        now = datetime(2022, 1, 1, 0, 0, 0)
        mock_datetime.now.return_value = now

        await client.read_messages(mock_websocket)

        assert client.last_heartbeat_received == now


@pytest.mark.asyncio
async def test_read_messages_other_msg():
    client = CurrencyWebSocketClient()

    mock_websocket = MockWebSocket([(WSMsgType.TEXT, '{"type":"other"}')])

    with patch("currency_ws_client.asyncio.create_task") as mock_create_task:
        await client.read_messages(mock_websocket)

        mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_handler(mocker: MockerFixture):
    client = CurrencyWebSocketClient()

    mocker.patch.object(
        client, "read_messages", side_effect=Exception("Test exception")
    )

    with patch("currency_ws_client.ClientSession.ws_connect") as mock_ws_connect:
        mock_websocket = AsyncMock(spec=ClientWebSocketResponse)
        mock_ws_connect.return_value.__aenter__.return_value = mock_websocket

        with pytest.raises(Exception):
            await asyncio.wait_for(client.websocket_handler(), timeout=2)

import pytest
import asyncio
import json
from unittest.mock import patch
from datetime import datetime, timedelta

from currency_converter import CurrencyConverter, JsonResponse
from currency_ws_client import CurrencyWebSocketClient
from unittest.mock import AsyncMock
from pytest_mock import MockerFixture
from aiohttp import ClientWebSocketResponse

import httpretty
from aioresponses import aioresponses
import unittest
import asyncio
from unittest.mock import MagicMock
from aiohttp import ClientResponse
from currency_converter import CurrencyConverter, JsonResponse


@pytest.fixture
def currency_converter():
    return CurrencyConverter()


@pytest.fixture
def api_response():
    return JsonResponse(
        {
            "motd": {
                "msg": "If you or your company use this project or like what we doing, please consider backing us so we can continue maintaining and evolving this project.",
                "url": "https://exchangerate.host/#/donate",
            },
            "success": True,
            "historical": True,
            "base": "EUR",
            "date": "2021-05-18",
            "rates": {
                "TZS": 2834.582279,
                "UAH": 33.520836,
                "UGX": 4318.484677,
                "USD": 1.222385,
            },
        }
    )


@pytest.mark.asyncio
async def test_fetch_exchange_rate(currency_converter, api_response):
    date = "2021-05-18"
    currency = "USD"
    request_url = f"{CurrencyConverter.EXCHANGE_RATE_API}/{date}?base={CurrencyConverter.CURRENCY}"

    with aioresponses() as mocked:
        mocked.get(request_url, status=200, payload=api_response)
        rate = await currency_converter.fetch_exchange_rate(date, currency)
        assert rate == api_response["rates"][currency]

    # Test that the rate is cached and cache is used for the same date and currency
    with aioresponses() as mocked:
        cached_rate = await currency_converter.fetch_exchange_rate(date, currency)
        assert cached_rate == rate
        assert not mocked.requests


@pytest.mark.asyncio
async def test_process_message(mocker: MockerFixture) -> None:
    # Mock websocket and its send_str method
    class MockWebsocket:
        async def send_str(self, msg):
            self.sent_msg = msg

    websocket = MockWebsocket()

    # Mock fetch_exchange_rate function
    async def mock_fetch_exchange_rate(date, currency):
        return 1.222385

    converter = CurrencyConverter()
    mocker.patch.object(
        converter,
        "fetch_exchange_rate",
        AsyncMock(side_effect=mock_fetch_exchange_rate),
    )

    # Sample message to process
    message = json.dumps(
        {
            "type": "message",
            "id": 456,
            "payload": {
                "marketId": 123456,
                "selectionId": 987654,
                "odds": 2.2,
                "stake": 253.67,
                "currency": "USD",
                "date": "2021-05-18T21:32:42.324Z",
            },
        }
    )

    websocket_client = CurrencyWebSocketClient()
    # Replace the original CurrencyConverter instance with the mocked one
    websocket_client.currency_converter = converter
    await websocket_client.currency_converter.process_message(websocket, message)

    expected_response = {
        "type": "message",
        "id": 456,
        "payload": {
            "marketId": 123456,
            "selectionId": 987654,
            "odds": 2.2,
            "stake": 207.52054,
            "currency": "EUR",
            "date": "2021-05-18T21:32:42.324Z",
        },
    }

    assert json.loads(websocket.sent_msg) == expected_response


@pytest.mark.asyncio
async def test_fetch_exchange_rate_error(currency_converter, mocker):
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.reason = "Server error"
    mocker.patch(
        "currency_converter.ClientSession.get",
        new_callable=AsyncMock,
        return_value=mock_response,
    )

    with pytest.raises(Exception):
        await currency_converter.fetch_exchange_rate("2023-04-27", "USD")


@pytest.mark.asyncio
async def test_process_message_error(currency_converter, mocker):
    websocket = AsyncMock(spec=ClientWebSocketResponse)

    message = {
        "type": "message",
        "id": 1,
        "payload": {"date": "2023-04-27T00:00:00", "currency": "USD", "stake": 100},
    }

    mocker.patch(
        "currency_converter.CurrencyConverter.fetch_exchange_rate",
        side_effect=Exception("API error"),
    )
    await currency_converter.process_message(websocket, json.dumps(message))

    websocket.send_str.assert_called_once_with(
        json.dumps(
            {
                "type": "error",
                "id": 1,
                "message": "Unable to convert stake. Error: API error",
            }
        )
    )

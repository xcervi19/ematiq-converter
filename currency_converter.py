import asyncio
import logging
import json
from locale import currency
from typing import Dict
from datetime import datetime, timedelta
from aiohttp import ClientSession, ClientWebSocketResponse
from typing import TypedDict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class JsonResponse(TypedDict):
    motd: dict[str, str]
    success: bool
    query: dict[str, str]
    info: dict[str, float]
    historical: bool
    date: str
    result: float
    rates: dict[str, float]


class CurrencyConverter:
    EXCHANGE_RATE_API = "https://api.exchangerate.host"
    CURRENCY = "EUR"
    CURRENCY_CACHE_DURATION = timedelta(hours=2)

    def __init__(self):
        self.currency_cache: Dict[str, Dict[str, float]] = {}
        self.currency_cache_expiration: Dict[str, datetime] = {}

    async def fetch_exchange_rate(self, date: str, currency: str) -> float:
        if (
            date in self.currency_cache
            and currency in self.currency_cache[date]
            and datetime.now() < self.currency_cache_expiration[date]
        ):
            return self.currency_cache[date][currency]

        async with ClientSession() as session:
            async with session.get(
                f"{self.EXCHANGE_RATE_API}/{date}?base={self.CURRENCY}"
            ) as response:
                if response.status == 200:
                    json_response: JsonResponse = await response.json()
                    logging.info(json_response)
                    if json_response["success"]:
                        rates = json_response["rates"]
                        if date not in self.currency_cache:
                            self.currency_cache[date] = {}
                        if date not in self.currency_cache_expiration:
                            self.currency_cache_expiration[date] = (
                                datetime.now() + self.CURRENCY_CACHE_DURATION
                            )
                        self.currency_cache[date].update(rates)
                        return float(rates[currency])
                    else:
                        raise Exception(
                            "Exchange rate API error: Request not successful"
                        )
                else:
                    raise Exception(
                        f"Exchange rate API error: {response.status} {response.reason}"
                    )

    async def process_message(self, websocket: ClientWebSocketResponse, message: str):
        data = json.loads(message)
        if data["type"] == "message":
            try:
                date_str = data["payload"]["date"][:10]
                currency = data["payload"]["currency"]
                rate = await self.fetch_exchange_rate(date_str, currency)
                converted_stake = round(data["payload"]["stake"] / rate, 5)
                data["payload"]["stake"] = converted_stake
                data["payload"]["currency"] = self.CURRENCY
            except Exception as e:
                data = {
                    "type": "error",
                    "id": data["id"],
                    "message": f"Unable to convert stake. Error: {str(e)}",
                }
            logging.info(json.dumps(data))
            await websocket.send_str(json.dumps(data))

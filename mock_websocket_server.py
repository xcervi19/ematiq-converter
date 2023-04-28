import asyncio
from aiohttp import web


async def mock_websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async def send_heartbeat():
        i = 0
        while True:
            i = i+1
            await ws.send_str('{"type": "heartbeat"}')
            if i%5 == 0:
                print(i)
                await asyncio.sleep(2.001) 
            else:
                await asyncio.sleep(1)

    heartbeat_task = asyncio.create_task(send_heartbeat())

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            print(f"Received message: {msg.data}")

    print("WebSocket connection closed")
    heartbeat_task.cancel()
    return ws


app = web.Application()
app.router.add_get("/websocket", mock_websocket_handler)

web.run_app(app)

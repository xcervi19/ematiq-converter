# Ematiq Currency Conversion Application

The Ematiq Currency Conversion Application is a small, nice, and compact Python application that implements a solution for currency conversion using a WebSocket connection. This application listens for messages from a server, converts the currency of the received messages, and sends the converted data back to the server.

## TO DO
```
test_client.py::test_websocket_handler
  /opt/anaconda3/envs/ematiq/lib/python3.11/selectors.py:72: RuntimeWarning: coroutine 'CurrencyConverter.process_message' was never awaited
    return self._selector._fd_to_key[fd]
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
```
## Technical Stack

- Python 3.11
- Poetry
- Black
- aiohttp 3.8.4
- ExchangeRate API

## Application Architecture

The application consists of three main components:

1. `CurrencyWebSocketClient`: Responsible for handling WebSocket connection, sending and receiving messages, and maintaining a heartbeat.
2. `CurrencyConverter`: Fetches exchange rates from the ExchangeRate API and performs currency conversion.
3. `app.py`: The entry point of the application, which initializes the CurrencyWebSocketClient and starts the event loop.

```
+-------------------+   +---------------------+   +--------------------+
| CurrencyWebSocket |<->| CurrencyConverter   |<->| ExchangeRate API   |
| Client            |   |                     |   |                    |
+-------------------+   +---------------------+   +--------------------+
```

The `websocket_handler` manages the WebSocket connection and coordinates three main asynchronous tasks: sending heartbeat messages, checking for received heartbeat messages, and processing incoming messages.

Here's a text representation of the async processes:

```
+--------------------------------------------------+
|              websocket_handler                   |
|                                                  |
|   +-----------------------------+                |
|   |   send_heartbeat (Task 1)   |                |
|   |   Sends a heartbeat message |                |
|   |   every 1 second            |                |
|   +-----------------------------+                |
|                     |                             |
|                     v                             |
|   +-----------------------------+                |
|   |   heartbeat_checker (Task 2)|<---------------|----+
|   |   Checks for a received     |                |    |
|   |   heartbeat within 2 seconds|                |    |
|   |   (0.0001s sleep between    |                |    |
|   |   checks)                   |                |    |
|   +-----------------------------+                |    |
|   | (Connected state)           |                |    |
|   +-----------------------------+                |    |
|   |   read_messages (Task 3)    |----------------|----+
|   |   Processes incoming        |
|   |   messages from the server  |
|   +-----------------------------+
|                                                  |
+--------------------------------------------------+

```

1. **send_heartbeat**: This async task sends a heartbeat message to the server every 1 second. The purpose of this task is to maintain an active connection with the server.

2. **heartbeat_checker**: This async task checks if a heartbeat message has been received within the last 2 seconds. It runs in a tight loop, with a 0.0001-second sleep between iterations, to ensure high precision. If no heartbeat is received within the 2-second threshold, it raises an exception, which is caught by the `websocket_handler` and triggers a reconnection attempt.

3. **read_messages**: This async task is responsible for processing incoming messages from the server. It listens for new messages and, upon receiving one, passes it to the `CurrencyConverter` to handle the currency conversion. This task also updates the `last_heartbeat_received` variable when a heartbeat message is received.

The `websocket_handler` uses `asyncio.wait` to run all three tasks concurrently. It monitors the tasks for completion and handles exceptions as needed, including re-establishing the WebSocket connection in case of a failure.

## Installation

Install the required packages using Poetry.

   ```
   conda create --name ematiq python
   conda activate ematiq
   poetry install
   ```

## Running the Application

1. Activate the virtual environment.

2. Run the main script.

   ```
   python app.py
   ```

This will start the application, establish a WebSocket connection, and begin listening for messages from the server. The application will automatically convert the currency of the received messages and send the converted data back to the server.

## Run unit tests
```
poetry run pytest test_converter.py
poetry run pytest test_client.py
```

## Formating
```
poetry run black
```

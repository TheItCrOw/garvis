import json
from fastapi import WebSocket
from app.utils.log_utils import log_message
from starlette.websockets import WebSocketState


class WebsocketMessenger:

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def send_json(self, payload: dict, log: bool = True):
        if log:
            log_message("SEND", payload)
        if self.websocket.client_state != WebSocketState.CONNECTED:
            return
        await self.websocket.send_text(json.dumps(payload))

import asyncio
import sys
from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.history: List[str] = []
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        for message in self.history:
            try:
                await websocket.send_text(message)
            except Exception:
                pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        self.history.append(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop


class _StdoutBridge:
    def __init__(self, stream):
        self.stream = stream
        self._buffer = ""

    def write(self, text: str):
        if not text:
            return 0
        self.stream.write(text)
        self.stream.flush()
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._forward(line)
        return len(text)

    def flush(self):
        if self._buffer.strip():
            self._forward(self._buffer)
            self._buffer = ""
        self.stream.flush()

    def _forward(self, line: str):
        message = line.strip()
        if not message:
            return
        if manager.loop and manager.loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), manager.loop)


_stdout_bridge = _StdoutBridge(sys.__stdout__)
_stderr_bridge = _StdoutBridge(sys.__stderr__)


def install_stdout_bridge():
    sys.stdout = _stdout_bridge
    sys.stderr = _stderr_bridge


def set_broadcast_loop(loop: asyncio.AbstractEventLoop):
    manager.set_loop(loop)

manager = ConnectionManager()

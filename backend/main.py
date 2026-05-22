import asyncio
import sys
import ctypes

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .log_manager import manager, install_stdout_bridge, set_broadcast_loop

install_stdout_bridge()

from .routers import control, vision, macro, system, blueprint

if sys.platform == "win32":
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
		
app = FastAPI(title="PYDD Auto Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(control.router, prefix="/api/control", tags=["Control"])
app.include_router(vision.router, prefix="/api/vision", tags=["Vision"])
app.include_router(macro.router, prefix="/api/macro", tags=["Macro Tools"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(blueprint.router, prefix="/api/blueprint", tags=["Blueprint"])


@app.on_event("startup")
async def init_log_broadcast_loop():
    set_broadcast_loop(asyncio.get_running_loop())

@app.get("/")
def read_root():
    return {"status": "ok", "message": "PYDD Backend is running."}

@app.websocket("/api/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

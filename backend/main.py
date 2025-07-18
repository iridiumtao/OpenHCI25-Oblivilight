import asyncio
import logging
import os
from typing import List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.core.agent import system_state, SystemState
from backend.core.chains import get_chains
from backend.core.tools import (
    create_memory,
    read_memory,
    update_memory,
    generate_card_image,
    LightControlTool,
)
from backend.services.stt_service import transcribe_realtime, transcribe_full
import numpy as np

# --- App Initialization ---
load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Oblivilight Backend")

# Mount static files for videos
app.mount("/static", StaticFiles(directory="backend/static"), name="static")


# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected: {websocket.client}")

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            await connection.send_json(message)
            
manager = ConnectionManager()
light_control_tool = LightControlTool(manager)

# --- Pydantic Models for API ---
class DeviceSignal(BaseModel):
    signal: str

class InjectContext(BaseModel):
    context: str
    
class UpdateSummary(BaseModel):
    full_summary: str

# --- WebSocket Endpoint ---
@app.websocket("/ws/projector")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
# --- API Endpoints ---
@app.post("/api/device/signal", status_code=200)
async def device_signal(payload: DeviceSignal):
    valid_signals = ["FORGET_8S", "FORGET_30S", "SLEEP_TRIGGER", "WAKE_UP"]
    if payload.signal not in valid_signals:
        raise HTTPException(status_code=400, detail="Invalid signal type.")

    logger.info(f"Received signal: {payload.signal}")
    
    # Placeholder for agent logic
    # Example: await agent.handle_signal(payload.signal)
    
    return {"status": "ok", "message": f"Signal '{payload.signal}' received and is being processed."}

@app.get("/api/memory/{uuid}", status_code=200)
async def get_memory(uuid: str):
    try:
        memory_data = read_memory(uuid)
        return memory_data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Memory not found.")

@app.put("/api/memory/{uuid}", status_code=200)
async def put_memory(uuid: str, payload: UpdateSummary):
    try:
        updated_memory = update_memory(uuid, {"full_summary": payload.full_summary})
        return updated_memory
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Memory not found.")
        
@app.post("/api/session/inject-context", status_code=200)
async def inject_context(payload: InjectContext):
    if not payload.context:
        raise HTTPException(status_code=400, detail="Context cannot be empty.")
    
    system_state.injected_context = payload.context
    logger.info(f"Injected context: {payload.context[:100]}...")
    
    return {"status": "success", "message": "Context injected."}


# --- Background Tasks & Core Logic (To be expanded) ---

async def real_time_emotion_analysis():
    """
    A background task that continuously processes audio for emotion analysis.
    """
    # This is a simplified placeholder. A real implementation would use
    # a proper audio streaming solution as outlined in the spec,
    # likely involving `sounddevice` in a separate thread feeding a queue.
    
    logger.info("Starting real-time emotion analysis loop...")
    while True:
        await asyncio.sleep(10) # Process every 10 seconds
        if system_state.is_listening and not system_state.is_processing:
            logger.info("Processing audio for emotion...")
            # 1. Get audio chunk (placeholder)
            # In a real scenario, this comes from an audio queue.
            # Example: audio_chunk = await audio_queue.get() 
            
            # 2. Transcribe
            # text = transcribe_realtime(audio_chunk)
            
            # 3. Analyze emotion (placeholder)
            # chains = get_chains()
            # emotion_result = await chains['emotion'].arun(input=text)
            
            # 4. Send to projector
            # emotion = emotion_result.get("text_emotion", "neutral")
            # await light_control_tool.set_light_effect(emotion)
            pass # End of placeholder logic


@app.on_event("startup")
async def startup_event():
    # Initialize chains and other resources
    get_chains()
    logger.info("Application startup: Initialized LangChain chains.")
    
    # Start the background task
    # asyncio.create_task(real_time_emotion_analysis())
    
    # Set initial state
    await light_control_tool.set_light_effect("IDLE", is_mode=True)
    logger.info("Application ready. Set initial state to IDLE.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
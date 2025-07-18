import asyncio
import logging
import os
from typing import List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.core.agent import agent
from backend.core.chains import get_chains
from backend.core.tools import (
    create_memory,
    read_memory,
    update_memory,
    generate_card_image,
    LightControlTool,
)
from backend.services.stt_service import transcribe_realtime
from backend.services.audio_service import audio_q, start_mic_thread
import numpy as np
import queue

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

    # 功能: 建立與前端投影頁面的長連線，用於後端主動推送燈效指令。
    # 訊息格式 (後端 -> 前端): {"type": "SET_EMOTION", "payload": {"emotion": "<emotion_label>"}}
    # 或 {"type": "SET_MODE", "payload": {"mode": "<mode_name>"}}。
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
    
    # Delegate signal handling to the agent
    asyncio.create_task(agent.handle_signal(payload.signal))
    
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
    
    agent.system_state.injected_context = payload.context
    logger.info(f"Injected context: {payload.context[:100]}...")
    
    return {"status": "success", "message": "Context injected."}


# --- Background Tasks & Core Logic ---

async def real_time_emotion_analysis():
    """
    A background task that continuously processes audio for emotion analysis.
    """
    buffer = np.zeros((0, 1), dtype=np.float32)
    # Configuration based on whisper_realtime.py
    WINDOW_SEC = 3
    STEP_SEC = 0.8
    TRIM_OLD_AUDIO = True
    MAX_BUFFER_SEC = 5
    SAMPLE_RATE = 16_000
    
    WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_SEC)
    STEP_SAMPLES = int(SAMPLE_RATE * STEP_SEC)
    MAX_BUFFER_SAMPLES = int(SAMPLE_RATE * MAX_BUFFER_SEC)
    
    frames_since_last_transcription = 0
    loop = asyncio.get_running_loop()
    
    logger.info("Starting real-time emotion analysis loop...")
    while True:
        if not agent.system_state.is_listening or agent.system_state.is_processing:
            await asyncio.sleep(0.5) # Wait if not listening or if busy
            continue

        try:
            # Get audio frame from the queue
            frame = await loop.run_in_executor(None, audio_q.get, 0.1)
            buffer = np.vstack((buffer, frame))
            frames_since_last_transcription += frame.shape[0]

            # Trim buffer to save memory
            if TRIM_OLD_AUDIO and len(buffer) > MAX_BUFFER_SAMPLES:
                buffer = buffer[-MAX_BUFFER_SAMPLES:]
            elif not TRIM_OLD_AUDIO and len(buffer) > WINDOW_SAMPLES * 2:
                buffer = buffer[-WINDOW_SAMPLES:]

            # Check if we have enough data to transcribe
            if len(buffer) < WINDOW_SAMPLES or frames_since_last_transcription < STEP_SAMPLES:
                continue

            frames_since_last_transcription = 0
            audio_chunk = buffer[-WINDOW_SAMPLES:].flatten()

            # Transcribe in executor to not block the event loop
            text = await loop.run_in_executor(None, transcribe_realtime, audio_chunk)
            
            if not text:
                continue
            
            logger.info(f"[Transcript] {text}")
            agent.system_state.conversation_history.append(text)

            # Analyze emotion
            emotion_result = await agent.chains['emotion'].arun(input={"text": text})
            emotion = emotion_result.get("text_emotion", "neutral")
            logger.info(f"[Emotion] {emotion}")

            # Send light effect to projector
            await light_control_tool.set_light_effect(emotion)

        except queue.Empty:
            await asyncio.sleep(0.1)
            continue
        except Exception as e:
            logger.error(f"Error in emotion analysis loop: {e}", exc_info=True)
            await asyncio.sleep(1)


@app.on_event("startup")
async def startup_event():
    # Initialize chains and other resources
    get_chains()
    logger.info("Application startup: Initialized LangChain chains.")
    
    # Initialize the agent with necessary tools
    agent.initialize(light_control_tool)
    
    # Start the microphone listener thread
    start_mic_thread()
    
    # Start the background task for real-time analysis
    asyncio.create_task(real_time_emotion_analysis())
    
    # Set initial state
    await light_control_tool.set_light_effect("IDLE", is_mode=True)
    logger.info("Application ready. Set initial state to IDLE.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
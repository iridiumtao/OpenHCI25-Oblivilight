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

class BackendStatus(BaseModel):
    is_listening: bool
    is_processing: bool
    has_injected_context: bool
    conversation_history_length: int
    active_websocket_connections: int

# --- WebSocket Endpoint ---
@app.websocket("/ws/projector")
async def websocket_endpoint(websocket: WebSocket):
    """
    Establish a persistent WebSocket connection with the projector frontend.

    This connection is used by the backend to push commands to the frontend,
    primarily for controlling the visual light effects. The frontend client should
    connect to this endpoint upon loading and listen for incoming messages.

    **Message Format (Server -> Client):**

    The server sends JSON objects with a `type` and a `payload`.

    1.  **Set Emotion-based Light Effect:**
        ```json
        {
          "type": "SET_EMOTION",
          "payload": {
            "emotion": "<emotion_label>"
          }
        }
        ```
        - `emotion_label` can be one of: `"happy"`, `"sad"`, `"angry"`, `"surprised"`, `"neutral"`.

    2.  **Set System Mode:**
        ```json
        {
          "type": "SET_MODE",
          "payload": {
            "mode": "<mode_name>"
          }
        }
        ```
        - `mode_name` can be one of: `"SLEEP"`, `"IDLE"`.

    The client does not need to send any messages to the server; it only needs to
    keep the connection alive to receive commands.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive by waiting for messages (even if none are expected)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
# --- API Endpoints ---
@app.get("/api/status", response_model=BackendStatus)
async def get_status():
    """
    Get the current operational status of the backend.

    This endpoint provides a snapshot of the system's state, which is useful for
    debugging and monitoring the application's health.

    **Example using curl:**
    ```bash
    curl -X GET "http://localhost:8000/api/status"
    ```

    **Example successful response:**
    ```json
    {
      "is_listening": true,
      "is_processing": false,
      "has_injected_context": false,
      "conversation_history_length": 5,
      "active_websocket_connections": 1
    }
    ```
    """
    logger.info("Serving backend status.")
    return {
        "is_listening": agent.system_state.is_listening,
        "is_processing": agent.system_state.is_processing,
        "has_injected_context": agent.system_state.injected_context is not None,
        "conversation_history_length": len(agent.system_state.conversation_history),
        "active_websocket_connections": len(manager.active_connections),
    }

@app.post("/api/device/signal", status_code=200)
async def device_signal(payload: DeviceSignal):
    """
    Receive a signal from the hardware device to trigger a core action.

    This is the primary way for the physical device (e.g., Arduino) to communicate
    its state changes to the backend. The backend will then trigger the corresponding
    workflow, such as starting a summary or forgetting a memory.

    - **signal (str)**: The type of signal being sent. Must be one of:
      `"FORGET_8S"`, `"FORGET_30S"`, `"SLEEP_TRIGGER"`, `"WAKE_UP"`.

    **Example using curl:**
    ```bash
    # To trigger the 'wake up' and start listening sequence
    curl -X POST "http://localhost:8000/api/device/signal" \
         -H "Content-Type: application/json" \
         -d '{"signal": "WAKE_UP"}'

    # To trigger the end-of-day summary process
    curl -X POST "http://localhost:8000/api/device/signal" \
         -H "Content-Type: application/json" \
         -d '{"signal": "SLEEP_TRIGGER"}'
    ```

    **Example successful response:**
    ```json
    {
      "status": "ok",
      "message": "Signal 'WAKE_UP' received and is being processed."
    }
    ```
    """
    valid_signals = ["FORGET_8S", "FORGET_30S", "SLEEP_TRIGGER", "WAKE_UP"]
    if payload.signal not in valid_signals:
        raise HTTPException(status_code=400, detail="Invalid signal type.")

    logger.info(f"Received signal: {payload.signal}")
    
    # Delegate signal handling to the agent
    asyncio.create_task(agent.handle_signal(payload.signal))
    
    return {"status": "ok", "message": f"Signal '{payload.signal}' received and is being processed."}

@app.get("/api/memory/{uuid}", status_code=200)
async def get_memory(uuid: str):
    """
    Retrieve a specific daily memory (diary entry) by its UUID.

    This endpoint is used by the web application to display the contents of a
    past memory to the user.

    - **uuid (str)**: The unique identifier for the memory, generated upon creation.

    **Example using curl:**
    ```bash
    # Replace 'your_uuid_here' with an actual UUID from the datastore
    curl -X GET "http://localhost:8000/api/memory/your_uuid_here"
    ```

    **Example successful response:**
    ```json
    {
        "created_at": "2023-10-27T10:00:00.123456",
        "full_summary": "Today was a day of quiet reflection...",
        "short_summary": "A peaceful day of thought.",
        "transcript": "I felt calm today when the sun came out..."
    }
    ```
    """
    try:
        memory_data = read_memory(uuid)
        return memory_data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Memory not found.")

@app.put("/api/memory/{uuid}", status_code=200)
async def put_memory(uuid: str, payload: UpdateSummary):
    """
    Update the full summary of a specific memory.

    This allows users to edit and refine the AI-generated diary summary through
    the web interface.

    - **uuid (str)**: The UUID of the memory to update.
    - **full_summary (str)**: The new, user-edited text for the full summary.

    **Example using curl:**
    ```bash
    # Replace 'your_uuid_here' with an actual UUID
    curl -X PUT "http://localhost:8000/api/memory/your_uuid_here" \
         -H "Content-Type: application/json" \
         -d '{"full_summary": "I had a different perspective on today after some thought..."}'
    ```

    **Example successful response:**
    ```json
    {
        "created_at": "2023-10-27T10:00:00.123456",
        "updated_at": "2023-10-27T11:30:00.654321",
        "full_summary": "I had a different perspective on today after some thought...",
        "short_summary": "A peaceful day of thought.",
        "transcript": "I felt calm today when the sun came out..."
    }
    ```
    """
    try:
        updated_memory = update_memory(uuid, {"full_summary": payload.full_summary})
        return updated_memory
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Memory not found.")
        
@app.post("/api/session/inject-context", status_code=200)
async def inject_context(payload: InjectContext):
    """
    Inject a past memory's context into the current conversation session.

    This enables the RAG (Retrieval-Augmented Generation) workflow. The web app
    sends the text of a past memory, and the backend's conversation chain will
    use this text as context for its responses, allowing the user to "continue"
    a past conversation.

    - **context (str)**: The text content of the past memory to inject.

    **Example using curl:**
    ```bash
    curl -X POST "http://localhost:8000/api/session/inject-context" \
         -H "Content-Type: application/json" \
         -d '{"context": "That day I was thinking about the upcoming trip and feeling excited."}'
    ```

    **Example successful response:**
    ```json
    {
      "status": "success",
      "message": "Context injected."
    }
    ```
    """
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
    WINDOW_SEC = 10
    STEP_SEC = 9
    TRIM_OLD_AUDIO = True
    MAX_BUFFER_SEC = 12
    SAMPLE_RATE = 16_000
    
    WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_SEC)
    STEP_SAMPLES = int(SAMPLE_RATE * STEP_SEC)
    MAX_BUFFER_SAMPLES = int(SAMPLE_RATE * MAX_BUFFER_SEC)
    
    frames_since_last_transcription = 0
    loop = asyncio.get_running_loop()
    was_listening_before = False
    
    logger.info("Starting real-time emotion analysis loop...")
    while True:
        # State change check: from not listening to listening
        if agent.system_state.is_listening and not was_listening_before:
            logger.info("Wake up detected in analysis loop. Clearing buffers.")
            # Clear the internal numpy buffer
            buffer = np.zeros((0, 1), dtype=np.float32)
            frames_since_last_transcription = 0
            # Clear the shared audio queue to discard any stale audio
            while not audio_q.empty():
                try:
                    audio_q.get_nowait()
                except queue.Empty:
                    break
        
        was_listening_before = agent.system_state.is_listening

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
            emotion_result = await agent.chains['emotion_analysis'].ainvoke({"text": text})
            emotion = emotion_result.get("text_emotion", "neutral")
            logger.info(f"[Emotion] {emotion}")

            # Check for sleep trigger
            if emotion == 'sleep':
                logger.info("Sleep intention detected. Triggering daily summary.")
                # process_daily_summary handles its own light effect ("SLEEP")
                await agent.process_daily_summary()
            else:
                # Send light effect to projector for other emotions
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
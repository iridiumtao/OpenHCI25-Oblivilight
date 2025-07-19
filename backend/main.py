import asyncio
import logging
import os
from typing import List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.core.agent import agent
from backend.core.chains import get_chains
from backend.core.tools import (
    read_memory,
    update_memory,
    LightControlTool,
)
from backend.services.audio_service import start_mic_thread

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handles application startup and shutdown events.
    """
    # --- Startup Logic ---
    logger.info("Application startup: Initializing resources...")
    
    # Initialize chains and other blocking resources
    get_chains()
    
    # Initialize the agent with necessary tools
    agent.initialize(light_control_tool)
    
    # Start the microphone listener thread
    start_mic_thread()
    
    # Start the agent's main processing loop as a background task
    # This task will run for the entire lifespan of the application
    agent_task = asyncio.create_task(agent.run_real_time_emotion_analysis())
    
    # Set initial state to IDLE
    await light_control_tool.set_light_effect("IDLE", is_mode=True)
    
    logger.info("Application is ready and running.")
    
    yield
    
    # --- Shutdown Logic ---
    # This block will be executed when the application shuts down.
    logger.info("Application shutdown: Cleaning up resources...")
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        logger.info("Agent's processing loop successfully cancelled.")
    logger.info("Application has been shut down gracefully.")


# --- App Initialization ---
load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Oblivilight Backend", lifespan=lifespan)

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
        - `emotion_label` can be one of: <happy|sad|warm|optimistic|anxious|peaceful|depressed|lonely|angry|neutral>.

    2.  **Set System Mode:**
        ```json
        {
          "type": "SET_MODE",
          "payload": {
            "mode": "<mode_name>"
          }
        }
        ```
        - `mode_name` can be one of: `"SLEEP"`, `"IDLE"`, `"FORGET"`.

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
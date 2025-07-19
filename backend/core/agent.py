import asyncio
from typing import Optional, List
from datetime import datetime


from backend.core.chains import get_chains
from backend.core.tools import create_memory, generate_card_image, LightControlTool
# Temporarily switching to Yating TTS for testing
from backend.services.tts_service import text_to_speech_and_play_yating as text_to_speech_and_play
import logging
import os

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

class SystemState:
    """
    Manages the global state of the backend application.
    This class is intended to be a singleton.
    """
    def __init__(self):
        self.is_listening: bool = False
        self.is_processing: bool = False  # Lock for tasks like forgetting or summarizing
        self.injected_context: Optional[str] = None
        self.conversation_history: List[str] = []
        self.full_audio_path: Optional[str] = None

    def reset_session(self):
        """Resets the state for a new user session."""
        self.is_listening = False
        self.is_processing = False
        self.injected_context = None
        self.conversation_history = []
        self.full_audio_path = None
        print("System state has been reset for a new session.")

# Singleton instance
system_state = SystemState()

# --- Main Agent Class ---

class Agent:
    def __init__(self):
        self.system_state = system_state
        self.chains = get_chains()
        self.light_control_tool = None # Will be set from main.py

    def initialize(self, light_control_tool: "LightControlTool"):
        """Initializes the agent with tools that need external context."""
        self.light_control_tool = light_control_tool
        logger.info("Agent initialized with all tools.")

    async def handle_signal(self, signal: str):
        """Main entry point for handling signals from the device."""
        if self.system_state.is_processing:
            logger.warning(f"Agent is busy processing. Signal '{signal}' ignored.")
            return

        logger.info(f"Agent handling signal: {signal}")
        if signal == "WAKE_UP":
            logger.info("Wake-up signal received. Resetting conversation history.")
            self.system_state.conversation_history = []
            self.system_state.is_listening = True
            await self.light_control_tool.set_light_effect("neutral") # Or a specific wake-up light
        elif signal == "SLEEP_TRIGGER":
            await self.process_daily_summary()
        elif signal in ["FORGET_8S", "FORGET_30S"]:
            await self.process_forget_memory(signal)
        else:
            logger.warning(f"Unknown signal received: {signal}")

    async def process_forget_memory(self, signal: str):
        """Handles the logic for forgetting the last part of the conversation."""
        self.system_state.is_processing = True
        logger.info("Processing 'forget memory' flow...")

        # Assuming an average speaking rate of ~3 Chinese characters per second for estimation.
        # FORGET_8S: 10s * 3 chars/s ≈ 30 chars
        # FORGET_30S: 30s * 3 chars/s = 60 chars
        chars_to_forget = 60 if signal == "FORGET_30S" else 30

        if not self.system_state.conversation_history:
            logger.info("Conversation history is empty. Nothing to forget.")
            self.system_state.is_processing = False
            return

        full_text = "".join(self.system_state.conversation_history)

        logger.info(f"Full conversation text (char count: {len(full_text)}): {full_text}")

        remaining_text = ""
        if len(full_text) > chars_to_forget:
            remaining_text = full_text[:-chars_to_forget]
        


        # Update conversation history based on what remains.
        # We replace the history with a single entry containing the remaining text.
        self.system_state.conversation_history = [remaining_text] if remaining_text else []

        # 防止給予TTS過多的上下文，專注於最新的內容
        if len(remaining_text) > 90:
            remaining_text = remaining_text[:90]

        logger.info(f"Remaining conversation after forgetting: {remaining_text}")

        # Always generate confirmation from the LLM, even if the remaining conversation is empty.
        # The prompt is designed to handle this gracefully.
        confirmation_result = await self.chains['forget_confirm'].ainvoke(
            {"conversation": remaining_text}
        )
        confirmation_message = confirmation_result

        logger.info(f"LLM forget confirmation: {confirmation_message}")

        # Play the confirmation message using the new TTS service
        try:
            # Running in a separate thread to avoid blocking the async event loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, text_to_speech_and_play, confirmation_message)
        except Exception as e:
            logger.error(f"Error playing TTS confirmation: {e}", exc_info=True)

        self.system_state.is_processing = False
        logger.info("'Forget memory' flow finished.")


    async def process_daily_summary(self):
        """Handles the end-of-day summary, storage, and card generation."""
        if self.system_state.is_processing:
            logger.warning("Daily summary process already active. Ignoring new trigger.")
            return

        self.system_state.is_listening = False
        self.system_state.is_processing = True
        await self.light_control_tool.set_light_effect("SLEEP", is_mode=True)
        logger.info("Processing 'daily summary' flow...")

        full_transcript = " ".join(self.system_state.conversation_history)

        if not full_transcript.strip():
            logger.warning("No conversation recorded. Skipping summary.")
            self.system_state.reset_session()
            await self.light_control_tool.set_light_effect("IDLE", is_mode=True)
            return

        # 1. Get full summary
        logger.info("Generating full summary...")
        full_summary = await self.chains['summary_full'].ainvoke({"conversation": full_transcript})

        # 2. Get short summary
        logger.info("Generating short summary...")
        short_summary = await self.chains['summary_short'].ainvoke({"full_summary": full_summary})

        # 3. Create memory in datastore
        memory_data = {
            "full_summary": full_summary,
            "short_summary": short_summary,
            "transcript": full_transcript,
        }
        memory_uuid = create_memory(memory_data)
        logger.info(f"Memory saved with UUID: {memory_uuid}")

        # 4. Generate QR code card
        # Assuming the frontend URL structure is known
        qr_data = f"http://localhost:3000/memory/{memory_uuid}" # Example URL
        card_path = f"datastore/card_{memory_uuid}.png"
        generate_card_image(
            date_str=datetime.now().strftime("%Y-%m-%d"),
            short_summary=short_summary,
            qr_data=qr_data,
            output_path=card_path
        )
        
        logger.info("Daily summary flow finished. Resetting session.")
        self.system_state.reset_session()
        await self.light_control_tool.set_light_effect("IDLE", is_mode=True)


# Singleton instance of the Agent
agent = Agent() 
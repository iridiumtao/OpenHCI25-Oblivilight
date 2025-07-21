import asyncio
from typing import Optional, List
from datetime import datetime
import numpy as np
import queue

from backend.core.chains import get_chains
from backend.core.state import system_state
from backend.core.tools import create_memory, CardAndPrinterTool, LightControlTool
from backend.services.tts_service import speak
from backend.services.stt_service import transcribe_realtime
from backend.services.audio_service import audio_q
import logging
import os

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# --- Main Agent Class ---

class Agent:
    def __init__(self):
        self.system_state = system_state
        self.chains = get_chains()
        self.light_control_tool = None # Will be set from main.py
        self.card_printer_tool = CardAndPrinterTool(card_output_dir="datastore")
        logger.info("Agent initialized.")

    def initialize(self, light_control_tool: "LightControlTool"):
        """Initializes the agent with tools that need external context."""
        self.light_control_tool = light_control_tool
        logger.info("Agent initialized with all tools.")

    async def run_real_time_emotion_analysis(self):
        """
        The main background task for the agent. It continuously processes audio 
        for emotion analysis when the system is in a listening state.
        """
        buffer = np.zeros((0, 1), dtype=np.float32)
        # Configuration based on whisper_realtime.py
        WINDOW_SEC = 8
        STEP_SEC = 3
        TRIM_OLD_AUDIO = True
        MAX_BUFFER_SEC = 12
        SAMPLE_RATE = 16_000

        WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_SEC)
        STEP_SAMPLES = int(SAMPLE_RATE * STEP_SEC)
        MAX_BUFFER_SAMPLES = int(SAMPLE_RATE * MAX_BUFFER_SEC)

        frames_since_last_transcription = 0
        loop = asyncio.get_running_loop()
        was_listening_before = False

        logger.info("Starting agent's real-time processing loop...")
        while True:
            # State change check: from not listening to listening
            if self.system_state.is_listening and not was_listening_before:
                logger.info("Wake up detected in agent loop. Clearing buffers.")
                # Clear the internal numpy buffer
                buffer = np.zeros((0, 1), dtype=np.float32)
                frames_since_last_transcription = 0
                # Clear the shared audio queue to discard any stale audio
                while not audio_q.empty():
                    try:
                        audio_q.get_nowait()
                    except queue.Empty:
                        break

            was_listening_before = self.system_state.is_listening

            if not self.system_state.is_listening or self.system_state.is_processing:
                await asyncio.sleep(0.5)  # Wait if not listening or if busy
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
                if (
                    len(buffer) < WINDOW_SAMPLES
                    or frames_since_last_transcription < STEP_SAMPLES
                ):
                    continue

                frames_since_last_transcription = 0
                audio_chunk = buffer[-WINDOW_SAMPLES:].flatten()

                # Transcribe in executor to not block the event loop
                text = await loop.run_in_executor(None, transcribe_realtime, audio_chunk)

                if not text:
                    continue

                logger.info(f"[Transcript] {text}")
                self.system_state.conversation_history.append(text)

                # Analyze emotion
                emotion_result = await self.chains["emotion_analysis"].ainvoke(
                    {"text": text}
                )
                emotion = emotion_result.get("text_emotion", "neutral")
                logger.info(f"[Emotion] {emotion}")

                # Check for sleep trigger
                if emotion == "sleep":
                    logger.info("Sleep intention detected. Triggering daily summary.")
                    # process_daily_summary handles its own light effect ("SLEEP")
                    await self.process_daily_summary()
                else:
                    # Send light effect to projector for other emotions
                    await self.light_control_tool.set_light_effect(emotion)

            except queue.Empty:
                await asyncio.sleep(0.1)
                continue
            except Exception as e:
                logger.error(f"Error in agent's processing loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def handle_signal(self, signal: str):
        """Main entry point for handling signals from the device."""
        # Handle forget signal with its own lock to prevent race conditions
        if signal in ["FORGET", "FORGET_10S", "FORGET_8S", "FORGET_30S"]:
            # Only process FORGET if the system is in a listening (wake-up) state.
            if not self.system_state.is_listening:
                logger.warning(
                    f"Forget signal '{signal}' received but agent is not in listening state. Ignoring."
                )
                return

            if self.system_state.is_forgetting:
                logger.warning(f"Agent is already forgetting. Signal '{signal}' ignored.")
                return
            # This is the main entry point for forget, so we let it through
            # and let process_forget_memory handle the state changes.
            await self.process_forget_memory(signal)
            return

        if self.system_state.is_processing:
            logger.warning(f"Agent is busy processing. Signal '{signal}' ignored.")
            return

        logger.info(f"Agent handling signal: {signal}")
        if signal == "WAKE_UP":
            logger.info("Wake-up signal received. Resetting conversation history.")
            self.system_state.conversation_history = []
            self.system_state.is_listening = True
            await self.light_control_tool.set_light_effect("IDLE", is_mode=True)
        elif signal == "SLEEP":
            await self.process_daily_summary()
        elif signal == "REWIND":
            logger.info("Rewind signal received. Broadcasting to frontend.")
            await self.light_control_tool.set_light_effect("REWIND", is_mode=True)
            # You can add more logic here if the backend needs to do something
            # for rewind, e.g., fetching past memories.
        # The FORGET signal is handled above with its own lock logic.
        else:
            logger.warning(f"Unknown signal received: {signal}")

    async def process_forget_memory(self, signal: str):
        """Handles the logic for forgetting the last part of the conversation."""
        # Set locks to prevent other operations and concurrent forgetting
        self.system_state.is_forgetting = True
        self.system_state.is_processing = True
        
        try:
            await self.light_control_tool.set_light_effect("FORGET", is_mode=True)
            logger.info("Processing 'forget memory' flow...")
    
            # Assuming an average speaking rate of ~3 Chinese characters per second for estimation.
            # FORGET_8S: 10s * 3 chars/s ≈ 30 chars
            # FORGET_30S: 30s * 3 chars/s = 60 chars
            chars_to_forget = 90 if signal == "FORGET_30S" else 30
    
            if not self.system_state.conversation_history:
                logger.info("Conversation history is empty. Nothing to forget.")
                # No need to return here, the logic below will handle it
                # and the state will be reset in the finally block.
    
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
                remaining_text = remaining_text[-90:]
    
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
                await loop.run_in_executor(None, speak, confirmation_message)
            except Exception as e:
                logger.error(f"Error playing TTS confirmation: {e}", exc_info=True)
        finally:
            # Release locks
            self.system_state.is_processing = False
            self.system_state.is_forgetting = False
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

        memory_uuid = "uuid"
        short_summary = ""

        if False:

            # 1. Get full summary from LLM
            logger.info("Generating full summary...")
            full_summary = await self.chains['summary_full'].ainvoke({"conversation": full_transcript})

            # 2. Get short summary from LLM
            logger.info("Generating short summary...")
            short_summary = await self.chains['summary_short'].ainvoke({"full_summary": full_summary})

            # 3. Save memory to datastore
            memory_data = {
                "full_summary": full_summary,
                "short_summary": short_summary,
                "transcript": full_transcript,
            }
            memory_uuid = create_memory(memory_data)
            logger.info(f"Memory saved with UUID: {memory_uuid}")

        # 4. Generate card, save it, and trigger the print job
        # The tool now handles both image generation and sending the print command
        logger.info("Generating card and triggering print job...")
        qr_data = f"http://localhost:3000/memory/{memory_uuid}" # Example URL, should be configurable
        card_path = self.card_printer_tool.generate_and_print_card(
            date_str=datetime.now().strftime("%Y-%m-%d"),
            short_summary=short_summary,
            qr_data=qr_data
        )

        if card_path:
            logger.info(f"Card generation and print trigger process completed. Image at: {card_path}")
        else:
            logger.error("Card generation or printing failed.")

        # 5. Reset session for the next day
        logger.info("Resetting session...")
        self.system_state.reset_session()

        # 6. Set light to idle after finishing
        logger.info("'Daily summary' flow finished.")


# Singleton instance of the Agent
agent = Agent() 
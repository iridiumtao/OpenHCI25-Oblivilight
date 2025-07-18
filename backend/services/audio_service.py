import queue
import sys
import time
from threading import Thread
import logging

import numpy as np
import sounddevice as sd

# --- Configuration ---
SAMPLE_RATE = 16_000
FRAME_MS = 250
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)

logger = logging.getLogger(__name__)

# --- Audio Queue ---
# This queue will hold audio chunks (numpy arrays) from the mic stream.
# The main application logic will consume from this queue.
audio_q: "queue.Queue[np.ndarray]" = queue.Queue()

def _audio_callback(indata: np.ndarray, frames: int, time_info, status) -> None:
    """This is called (from a separate thread) for each audio block."""
    if status:
        logger.warning(f"Sounddevice status: {status}")
    audio_q.put(indata.copy())

def _mic_thread_target() -> None:
    """
    The target function for the microphone listener thread.
    This function runs in a separate thread and continuously puts
    audio data into the `audio_q`.
    """
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=FRAME_SAMPLES,
            callback=_audio_callback,
        ):
            logger.info("🎙️  Microphone listener started successfully.")
            # The InputStream keeps the thread alive, so we just sleep.
            while True:
                time.sleep(10)
    except Exception as e:
        logger.critical(f"🚨 A critical error occurred in the microphone thread: {e}", exc_info=True)
        logger.critical("   The application might not be able to process real-time audio.")
        # Optional: You could try to restart the stream here.
        # For now, we'll let the thread die and log the error.

def start_mic_thread() -> None:
    """Creates and starts the microphone listener daemon thread."""
    mic_thread = Thread(target=_mic_thread_target, daemon=True)
    mic_thread.start()
    logger.info("🎤 Microphone listening thread initiated.") 
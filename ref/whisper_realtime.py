import asyncio
import os
import sys
import queue
import time
import difflib
from threading import Thread

import numpy as np
import sounddevice as sd
import torch
import whisper

# ------------------- CONFIG --------------------
SAMPLE_RATE = 16_000
FRAME_MS = 250
WINDOW_SEC = 3  # transcription window length (context)
STEP_SEC = 0.8   # how often to run ASR (stride)
TRIM_OLD_AUDIO = True  # enable dropping very old audio
MAX_BUFFER_SEC = 5    # keep at most this many seconds of audio if trimming enabled
LANGUAGE = "zh"  # change to "en" etc. if needed
WHISPER_MODEL = "small"  # tiny / small / medium / large

# ----------------- DEVICE PICK -----------------

def _pick_device() -> str:
    if torch.backends.mps.is_available():
        try:
            _ = torch.tensor([1.0], device="mps")
            return "mps"
        except Exception:
            pass
    return "cpu"


def _densify(module: torch.nn.Module):
    for name, param in list(module.named_parameters(recurse=False)):
        if param.is_sparse:
            dense = param.to_dense().clone()
            setattr(module, name, torch.nn.Parameter(dense, requires_grad=False))
    for name, buf in list(module.named_buffers(recurse=False)):
        if buf.is_sparse:
            module.register_buffer(name, buf.to_dense().clone())
    for child in module.children():
        _densify(child)


DEVICE = _pick_device()
print(f"Loading Whisper-{WHISPER_MODEL} on {DEVICE} …", flush=True)
model = whisper.load_model(WHISPER_MODEL, device="cpu")
_densify(model)
try:
    model.to(DEVICE)
except Exception as e:
    print("⚠️  Falling back to CPU –", e)
    DEVICE = "cpu"

# -------------- AUDIO STREAM -------------------
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)
audio_q: "queue.Queue[np.ndarray]" = queue.Queue()


def _audio_cb(indata, frames, time_info, status):
    if status:
        print("Audio status:", status, file=sys.stderr)
    audio_q.put(indata.copy())


def start_mic():
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=FRAME_SAMPLES,
        callback=_audio_cb,
    ):
        while True:
            time.sleep(0.1)


# -------------- ASR WORKER ---------------------
async def stt_worker():
    buffer = np.zeros((0, 1), dtype=np.float32)
    WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_SEC)
    STEP_SAMPLES = int(SAMPLE_RATE * STEP_SEC)
    MAX_BUFFER_SAMPLES = int(SAMPLE_RATE * MAX_BUFFER_SEC)
    last_text = ""
    frames_since_last = 0
    loop = asyncio.get_running_loop()

    while True:
        frame = await loop.run_in_executor(None, audio_q.get)
        buffer = np.vstack((buffer, frame))
        frames_since_last += frame.shape[0]

        # keep buffer size bounded to save RAM or trim old audio
        if TRIM_OLD_AUDIO and len(buffer) > MAX_BUFFER_SAMPLES:
            buffer = buffer[-MAX_BUFFER_SAMPLES:]
        elif not TRIM_OLD_AUDIO and len(buffer) > WINDOW_SAMPLES * 2:
            buffer = buffer[-WINDOW_SAMPLES:]

        if len(buffer) < WINDOW_SAMPLES or frames_since_last < STEP_SAMPLES:
            continue

        frames_since_last = 0  # reset counter

        audio_chunk = buffer[-WINDOW_SAMPLES:].flatten()

        def _transcribe(chunk):
            return model.transcribe(
                chunk,
                language=LANGUAGE,
                fp16=False,
                no_speech_threshold=0.3,
            )

        result = await loop.run_in_executor(None, _transcribe, audio_chunk)
        text = result["text"].strip()
        if not text:
            continue

        # word-level diff to avoid tiny fragments
        prev_words = last_text.split()
        curr_words = text.split()
        prefix_len = 0
        for pw, cw in zip(prev_words, curr_words):
            if pw == cw:
                prefix_len += 1
            else:
                break
        new_segment = " ".join(curr_words[prefix_len:])
        if not new_segment:
            continue

        print(f"[Transcript] {new_segment}")
        last_text = text


# -------------- MAIN ---------------------------

def main():
    mic_thread = Thread(target=start_mic, daemon=True)
    mic_thread.start()
    print("🎙️  Whisper real-time transcription started. Speak…\n")

    async def runner():
        await stt_worker()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main() 
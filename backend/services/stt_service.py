import os
import torch
import whisper
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration for Local Whisper ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
LANGUAGE = os.getenv("APP_LANGUAGE", "zh")

# --- Device Picking and Model Loading ---

def _pick_device() -> str:
    """Picks the best available device for Torch (mps, cuda, cpu)."""
    if torch.backends.mps.is_available():
        try:
            torch.tensor([1.0], device="mps")
            return "mps"
        except Exception:
            print("⚠️  MPS device found, but failed to use. Falling back to CPU.")
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

def _densify(module: torch.nn.Module):
    """Recursively converts sparse parameters to dense for MPS compatibility."""
    for name, param in list(module.named_parameters(recurse=False)):
        if param.is_sparse:
            dense = param.to_dense().clone()
            setattr(module, name, torch.nn.Parameter(dense, requires_grad=False))
    for name, buf in list(module.named_buffers(recurse=False)):
        if buf.is_sparse:
            module.register_buffer(name, buf.to_dense().clone())
    for child in module.children():
        _densify(child)

# --- Load Models and Clients ---

DEVICE = _pick_device()
local_model = None
cloud_client = None

try:
    print(f"Loading local Whisper-{WHISPER_MODEL} model on CPU...")
    # Load on CPU first to avoid potential MPS issues during download
    local_model = whisper.load_model(WHISPER_MODEL, device="cpu")
    if DEVICE != "cpu":
        print(f"Moving local model to {DEVICE}...")
        _densify(local_model) # Densify for MPS if needed
        local_model.to(DEVICE)
    print(f"✅ Local Whisper model loaded successfully on {DEVICE}.")
except Exception as e:
    print(f"🚨 Failed to load local Whisper model: {e}")
    print("   Real-time transcription will not be available.")

try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not found in .env file. Cloud services will be unavailable.")
    else:
        cloud_client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully.")
except Exception as e:
    print(f"🚨 Failed to initialize OpenAI client: {e}")

# --- Service Functions ---

def transcribe_realtime(audio_chunk: np.ndarray) -> str:
    """
    Transcribes a short audio chunk using the local Whisper model.
    Expects a numpy array of float32 audio data.
    """
    if local_model is None:
        raise RuntimeError("Local Whisper model is not loaded or failed to load.")
    
    if not isinstance(audio_chunk, np.ndarray):
        raise TypeError(f"audio_chunk must be a numpy array, but got {type(audio_chunk)}")

    # Model expects a flat numpy array of float32
    audio_data = audio_chunk.flatten().astype(np.float32)

    result = local_model.transcribe(
        audio_data,
        language=LANGUAGE,
        fp16=(DEVICE != "cpu"), # FP16 is not supported on CPU
        no_speech_threshold=0.3,
    )
    return result.get("text", "").strip()

def transcribe_full(audio_file_path: str) -> str:
    """
    Transcribes a full audio file using the cloud Whisper API.
    """
    if cloud_client is None:
        raise RuntimeError("OpenAI client is not initialized. Check OPENAI_API_KEY.")
        
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found at: {audio_file_path}")

    with open(audio_file_path, "rb") as audio_file:
        transcription = cloud_client.audio.transcriptions.create(
            model="gpt-4o-transcribe", 
            file=audio_file,
            response_format="text"
        )
    return transcription 
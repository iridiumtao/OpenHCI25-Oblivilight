import os
import torch
import whisper
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import json
import logging

# --- New Imports for Google Cloud STT ---
try:
    from google.cloud import speech
    from google.oauth2 import service_account
except ImportError:
    speech = None
    service_account = None


# Load environment variables from .env file
load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# --- Load STT Provider Setting ---
STT_PROVIDER = "local" # Default value
try:
    # Use an absolute path or a path relative to the project root
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    with open(config_path, "r") as f:
        settings = json.load(f)
        STT_PROVIDER = settings.get("stt_provider", "local")
    logger.info(f"STT Provider set to: '{STT_PROVIDER}'")
except FileNotFoundError:
    logger.warning(f"Configuration file not found at {config_path}. Defaulting to 'local' STT provider.")
except json.JSONDecodeError:
    logger.error("Failed to decode settings.json. Defaulting to 'local' STT provider.")


# --- Configuration ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
LANGUAGE = os.getenv("APP_LANGUAGE", "zh")
SAMPLE_RATE = 16_000 # The sample rate the agent uses

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

DEVICE = ""
local_model = None
cloud_client = None
google_speech_client = None

if STT_PROVIDER == "local":
    DEVICE = _pick_device()
    try:
        logger.info(f"Loading local Whisper-{WHISPER_MODEL} model on CPU...")
        # Load on CPU first to avoid potential MPS issues during download
        local_model = whisper.load_model(WHISPER_MODEL, device="cpu")
        if DEVICE != "cpu":
            logger.info(f"Moving local model to {DEVICE}...")
            _densify(local_model) # Densify for MPS if needed
            local_model.to(DEVICE)
        logger.info(f"✅ Local Whisper model loaded successfully on {DEVICE}.")
    except Exception as e:
        logger.error(f"🚨 Failed to load local Whisper model: {e}")
        logger.error("   Real-time transcription will not be available.")
elif STT_PROVIDER == "google":
    if not speech:
        logger.error("🚨 google-cloud-speech is not installed. Please run 'pip install google-cloud-speech'.")
    else:
        try:
            # This will automatically find the credentials from the environment variable
            google_speech_client = speech.SpeechClient()
            logger.info("✅ Google Cloud Speech client initialized successfully.")
        except Exception as e:
            logger.error(f"🚨 Failed to initialize Google Cloud Speech client: {e}")
            logger.error("   Make sure GOOGLE_APPLICATION_CREDENTIALS is set correctly.")


try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("⚠️  OPENAI_API_KEY not found in .env file. Cloud services will be unavailable.")
    else:
        cloud_client = OpenAI(api_key=api_key)
        logger.info("✅ OpenAI client initialized successfully.")
except Exception as e:
    logger.error(f"🚨 Failed to initialize OpenAI client: {e}")

# --- Service Functions ---

def transcribe_realtime(audio_chunk: np.ndarray) -> str:
    """
    Transcribes a short audio chunk using the configured STT provider.
    Expects a numpy array of float32 audio data.
    """
    if STT_PROVIDER == "local":
        return _transcribe_realtime_local(audio_chunk)
    elif STT_PROVIDER == "google":
        return _transcribe_realtime_google(audio_chunk)
    else:
        logger.error(f"Invalid STT_PROVIDER '{STT_PROVIDER}' in settings.json. Defaulting to no-op.")
        return ""

def _transcribe_realtime_local(audio_chunk: np.ndarray) -> str:
    """Uses local Whisper model."""
    if local_model is None:
        logger.error("Local Whisper model is not loaded or failed to load.")
        return ""

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

def _transcribe_realtime_google(audio_chunk: np.ndarray) -> str:
    """Uses Google Cloud Speech-to-Text API."""
    if google_speech_client is None:
        logger.error("Google Cloud Speech client is not initialized.")
        return ""

    if not isinstance(audio_chunk, np.ndarray):
        raise TypeError(f"audio_chunk must be a numpy array, but got {type(audio_chunk)}")

    # Convert float32 numpy array to int16 bytes, as required by Google's API
    # for LINEAR16 encoding.
    int16_audio = (audio_chunk * 32767).astype(np.int16)
    content = int16_audio.tobytes()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE,
        language_code="cmn-Hant-TW", # e.g., zh-TW
        model="latest_long", # Good for general purpose, non-telephony audio
    )

    try:
        response = google_speech_client.recognize(config=config, audio=audio)
        if response.results:
            return response.results[0].alternatives[0].transcript.strip()
        return ""
    except Exception as e:
        logger.error(f"Error calling Google STT API: {e}", exc_info=True)
        return ""


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
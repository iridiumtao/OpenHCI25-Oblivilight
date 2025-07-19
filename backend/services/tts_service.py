import os
import requests
from pathlib import Path
import openai
from playsound import playsound
import logging
import base64

logger = logging.getLogger(__name__)

#    - "OPENAI": Uses OpenAI's TTS (default).
#    - "YATING": Uses Yating's TTS.
TTS_PROVIDER = "OPENAI"


def text_to_speech_and_play(text: str, voice: str = "nova"):
    """
    Converts text to speech using OpenAI's TTS API and plays it directly.
    Uses SSML (Speech Synthesis Markup Language) to control the voice's properties.
    """
    if not text.strip():
        logger.warning("TTS Service: Received empty text. Nothing to play.")
        return

    # Using SSML to control speech properties. This is a more reliable method
    # than prepending instructions. The <prosody> tag helps in controlling
    # the rate, making the speech sound calmer and more gentle.
    # Note: While SSML is standard, OpenAI's support for it is not fully documented.
    # This approach is based on standard TTS practices.
    ssml_input = f"""
<speak>
  <prosody rate="slow">
    {text}
  </prosody>
</speak>
"""

    try:
        # It's good practice to use a temporary directory for generated audio files.
        # For this project, we'll place it within the datastore directory.
        temp_audio_dir = Path(__file__).parent.parent / "datastore" / "temp_audio"
        temp_audio_dir.mkdir(exist_ok=True)
        speech_file_path = temp_audio_dir / "forget_confirmation.mp3"

        logger.info(f"TTS Service: Generating audio for text: '{text[:30]}...'")
        
        # Using the OpenAI Python client to stream the audio
        client = openai.OpenAI()
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input=ssml_input
        )

        # Write the binary audio content to a file
        response.stream_to_file(str(speech_file_path))

        logger.info(f"TTS Service: Playing audio file at {speech_file_path}")
        # Using playsound to play the generated mp3
        playsound(str(speech_file_path))

        # Optional: Clean up the audio file after playing
        # os.remove(speech_file_path)

    except Exception as e:
        # Catching potential errors from the API or file system
        logger.error(f"TTS Service: An error occurred: {e}", exc_info=True)


def text_to_speech_and_play_yating(text: str):
    """
    Converts text to speech using Yating's v3 TTS API via requests and plays it.
    This method directly calls the HTTP API for better stability.
    """
    if not text.strip():
        logger.warning("Yating TTS: Received empty text. Nothing to play.")
        return

    yating_api_key = os.getenv("YATING_API_KEY")
    if not yating_api_key:
        logger.error("Yating TTS: YATING_API_KEY environment variable not set.")
        return

    url = "https://tts.api.yating.tw/v3/speeches/synchronize"
    headers = {
        "key": f"{yating_api_key}",
        "Content-Type": "application/json"
    }
    # Per v3 documentation, we use tts-base-zh-en model and select a voice
    # Voice 'zh_en_female_1' is Yating's voice. Speed 0.9 for a gentler tone.
    payload = {
        "input": {
            "text": text,
            "type": "text"
        },
        "voice": {
            "model": "female_2",
            "lang": "zh_tw"
        },
        "audioConfig": {
            "encoding": "MP3",
            "maxLength": 600000,
            "uploadFile": False
        }
    }

    try:
        logger.info(f"Yating TTS (v3): Sending request for text: '{text[:30]}...'")
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        
        response_data = response.json()
        audio_content_base64 = response_data.get("audioFile", {}).get("audioContent")

        if audio_content_base64:
            temp_audio_dir = Path(__file__).parent.parent / "datastore" / "temp_audio"
            temp_audio_dir.mkdir(exist_ok=True)
            speech_file_path = temp_audio_dir / "yating_v3_confirmation.mp3"

            # Decode the Base64 string into bytes
            audio_bytes = base64.b64decode(audio_content_base64)
            
            # Write the audio bytes to a file
            with open(speech_file_path, "wb") as f:
                f.write(audio_bytes)

            logger.info(f"Yating TTS (v3): Playing audio file at {speech_file_path}")
            playsound(str(speech_file_path))
        else:
            logger.error(f"Yating TTS (v3): 'audioContent' not found in API response. Response: {response_data}")

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"Yating TTS (v3): HTTP error occurred: {http_err} - {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Yating TTS (v3): A network error occurred: {e}", exc_info=True)
    except (KeyError, TypeError, base64.binascii.Error) as e:
        logger.error(f"Yating TTS (v3): Failed to parse or decode API response: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Yating TTS (v3): An unexpected error occurred: {e}", exc_info=True)


def speak(text: str):
    """
    Dynamically selects and uses the configured TTS service to speak the text.
    The selection is based on the `TTS_PROVIDER` global variable.

    """
    provider = TTS_PROVIDER

    if provider == "YATING":
        logger.info(f"Routing to Yating TTS for: '{text[:30]}...'")
        text_to_speech_and_play_yating(text)
    else:
        if provider != "OPENAI":
            logger.warning(f"Unknown TTS_PROVIDER '{provider}'. Defaulting to OpenAI.")
        logger.info(f"Routing to OpenAI TTS for: '{text[:30]}...'")
        text_to_speech_and_play(text) 
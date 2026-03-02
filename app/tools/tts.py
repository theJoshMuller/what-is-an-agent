# app/tools/tts.py
from pathlib import Path
import requests

FILES_DIR = Path("files")

VOICE_MAP = {
    "en": "af_heart",
    "fr": "ff_siwis",
    "es": "ef_dora",
    "pt": "pf_dora",
    "it": "if_sara",
    "hi": "hf_alpha",
}

LANGUAGE_LABELS = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "it": "Italian",
    "hi": "Hindi",
}

SCHEMA = {
    "type": "function",
    "function": {
        "name": "tts_generate_audio",
        "description": (
            "Convert text to speech using Kokoro TTS and save the audio to a file. "
            "Supported languages: en (English), fr (French), es (Spanish), "
            "pt (Portuguese), it (Italian), hi (Hindi)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to synthesize"
                },
                "language": {
                    "type": "string",
                    "enum": list(VOICE_MAP.keys()),
                    "description": "Language code: en, fr, es, pt, it, hi"
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename inside ./files/ (e.g. greeting.wav)"
                }
            },
            "required": ["text", "language", "filename"]
        }
    }
}


def execute(args: dict) -> dict:
    from app import config

    FILES_DIR.mkdir(exist_ok=True)
    text = args.get("text", "")
    language = args.get("language", "en")
    filename = Path(args.get("filename", "output.wav")).name  # strip any path prefix

    if language not in VOICE_MAP:
        return {
            "result": "",
            "error": f"Unsupported language '{language}'. Supported: {', '.join(VOICE_MAP.keys())}"
        }

    voice = VOICE_MAP[language]
    host = config.get("tts.host", "localhost")
    port = config.get("tts.port", 8880)
    url = f"http://{host}:{port}/v1/audio/speech"

    try:
        response = requests.post(url, json={
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "response_format": "wav",
        }, timeout=30)

        if response.status_code != 200:
            return {"result": "", "error": f"TTS API error {response.status_code}: {response.text[:200]}"}

        path = FILES_DIR / filename
        with open(path, "wb") as f:
            f.write(response.content)

        return {
            "result": f"Audio saved to files/{filename} ({len(response.content)} bytes). Voice: {voice}.",
            "error": None,
            "audio_file": str(path.absolute()),
        }
    except requests.exceptions.ConnectionError:
        return {
            "result": "",
            "error": f"Cannot connect to Kokoro TTS at {host}:{port}. See https://github.com/remsky/Kokoro-FastAPI to set up TTS."
        }
    except Exception as e:
        return {"result": "", "error": str(e)}

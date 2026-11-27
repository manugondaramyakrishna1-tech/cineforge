"""Local text-to-speech helper powered by pyttsx3 and installed OS voices."""
from pathlib import Path
import pyttsx3


def list_voices(language=None):
    """Return installed voices, optionally filtering by language code (e.g. te)."""
    engine = pyttsx3.init()
    try:
        voices = engine.getProperty("voices") or []
        result = []
        for voice in voices:
            langs = getattr(voice, "languages", []) or []
            langs_text = " ".join(str(x).lower() for x in langs)
            name_text = (getattr(voice, "name", "") or "").lower()
            if language is None or language.lower() in langs_text or language.lower() in name_text:
                result.append({"id": voice.id, "name": voice.name, "languages": langs_text})
        return result
    finally:
        engine.stop()


def synthesize(text: str, output: Path, rate: int = 165, volume: float = 1.0, voice_id=None):
    if not text.strip():
        raise ValueError("Narration text is empty.")
    engine = pyttsx3.init()
    try:
        engine.setProperty("rate", rate)
        engine.setProperty("volume", max(0.0, min(1.0, volume)))
        if voice_id:
            available = {v.id for v in (engine.getProperty("voices") or [])}
            if voice_id not in available:
                raise ValueError("Selected voice is not installed on this system.")
            engine.setProperty("voice", voice_id)
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        engine.save_to_file(text, str(output))
        engine.runAndWait()
    finally:
        engine.stop()
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("Voice engine produced no file; check OS voice support and installed language voices.")
    return output

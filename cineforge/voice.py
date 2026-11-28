"""Local text-to-speech helper powered by pyttsx3 and installed OS voices.

Voice discovery is optional: CineForge should remain usable when no system TTS
backend (such as eSpeak on Linux) is installed.
"""
from pathlib import Path
import pyttsx3


def _init_engine():
    try:
        return pyttsx3.init()
    except Exception as exc:
        raise RuntimeError(
            "Local text-to-speech is unavailable. On Linux/Codespaces install "
            "the system package espeak-ng (and libespeak where required), then "
            "restart CineForge. Other CineForge features can still be used."
        ) from exc


def list_voices(language=None):
    """Return installed voices, optionally filtering by language code (e.g. te).

    Returns an empty list if the OS speech backend is unavailable.
    """
    try:
        engine = _init_engine()
    except RuntimeError:
        return []
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
        try:
            engine.stop()
        except Exception:
            pass


def synthesize(text: str, output: Path, rate: int = 165, volume: float = 1.0, voice_id=None):
    if not text.strip():
        raise ValueError("Narration text is empty.")
    engine = _init_engine()
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
        try:
            engine.stop()
        except Exception:
            pass
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("Voice engine produced no file; check OS voice support and installed language voices.")
    return output

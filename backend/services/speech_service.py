import logging
import os
import wave

import numpy as np

logger = logging.getLogger(__name__)

try:
    import whisper
except Exception as error:
    whisper = None
    logger.warning("Whisper not available: %s", error)

model = None


def load_model():
    global model
    if whisper and model is None:
        try:
            model = whisper.load_model("base")
            logger.info("Whisper base model loaded successfully")
        except Exception as error:
            logger.warning("Error loading Whisper model: %s", error)
            model = None
    return model


load_model()


def speech_model_available() -> bool:
    return load_model() is not None


def transcribe_audio(file_path: str) -> str:
    active_model = load_model()
    if not active_model:
        logger.warning("Whisper model not available, returning empty transcription")
        return ""

    try:
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            logger.warning("Audio file is missing or empty: %s", file_path)
            return ""

        audio_input = file_path
        if file_path.lower().endswith(".wav"):
            with wave.open(file_path, "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                sample_width = wav_file.getsampwidth()
                channel_count = wav_file.getnchannels()
                frame_count = wav_file.getnframes()
                raw_audio = wav_file.readframes(frame_count)

            if sample_width != 2:
                logger.warning("Unsupported WAV sample width: %s", sample_width)
                return ""

            audio = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
            if channel_count > 1:
                audio = audio.reshape(-1, channel_count).mean(axis=1)

            if sample_rate != 16000 and len(audio) > 0:
                duration = len(audio) / sample_rate
                target_length = max(1, int(round(duration * 16000)))
                source_axis = np.linspace(0, duration, num=len(audio), endpoint=False)
                target_axis = np.linspace(0, duration, num=target_length, endpoint=False)
                audio = np.interp(target_axis, source_axis, audio).astype(np.float32)

            audio_input = audio

        result = active_model.transcribe(audio_input, language="en")
        return result.get("text", "").strip()
    except Exception as error:
        logger.error("Error transcribing audio: %s", error, exc_info=True)
        return ""

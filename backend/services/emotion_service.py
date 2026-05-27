import logging

from services.config_service import env_flag

logger = logging.getLogger(__name__)

EMOTION_DETECTION_ENABLED = env_flag("ENABLE_EMOTION_DETECTION", default=True)


def _load_emotion_predictors():
    if not EMOTION_DETECTION_ENABLED:
        raise RuntimeError("Emotion detection is disabled in this environment.")

    from models.emotion_model import predict_emotion, predict_emotion_from_bytes

    return predict_emotion, predict_emotion_from_bytes

def detect_emotion(image_path):
    predict_emotion, _ = _load_emotion_predictors()
    return predict_emotion(image_path)


def detect_emotion_bytes(image_bytes: bytes):
    _, predict_emotion_from_bytes = _load_emotion_predictors()
    return predict_emotion_from_bytes(image_bytes)

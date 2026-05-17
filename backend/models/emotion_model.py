import logging
import os
from collections import deque

os.environ["TORCH_HOME"] = "./torch_cache"
os.environ["TORCHVISION_DISABLE_DOWNLOADS"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models

logger = logging.getLogger(__name__)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.getenv("EMOTION_MODEL_PATH", os.path.join(BASE_DIR, "best_model.pth"))
device = torch.device("cpu")

model = models.resnet18(weights=None)
model.fc = nn.Sequential(
    nn.Linear(model.fc.in_features, 128),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(128, 3),
)

if os.path.exists(MODEL_PATH):
    try:
        state = torch.load(MODEL_PATH, map_location=device)
        model.load_state_dict(state)
        logger.info("Emotion model loaded successfully")
    except Exception as error:
        logger.warning("Emotion model load error: %s", error)

model.to(device)
model.eval()

LABELS = ["Disappointed", "interested", "neutral"]
DISPLAY_MAPPING = {
    "Disappointed": "Nervous",
    "interested": "Confident",
    "neutral": "Normal",
}
PREDICTION_HISTORY = deque(maxlen=5)
TEMPERATURE = 1.15


def _imagenet_normalize(img_rgb: np.ndarray) -> torch.Tensor:
    img_norm = img_rgb.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_norm = (img_norm - mean) / std
    img_norm = np.transpose(img_norm, (2, 0, 1))
    return torch.tensor(img_norm, dtype=torch.float32).unsqueeze(0).to(device)


def _apply_clahe(img_bgr: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    merged = cv2.merge((l_channel, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def preprocess_variants(img_array: np.ndarray) -> list[torch.Tensor]:
    resized = cv2.resize(img_array, (224, 224))
    enhanced = _apply_clahe(resized)
    flipped = cv2.flip(enhanced, 1)

    variants = []
    for variant in (resized, enhanced, flipped):
        rgb = cv2.cvtColor(variant, cv2.COLOR_BGR2RGB)
        variants.append(_imagenet_normalize(rgb))
    return variants


def detect_and_extract_face(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.08,
        minNeighbors=6,
        minSize=(40, 40),
    )
    if len(faces) == 0:
        return img, False

    x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
    pad_x = int(0.22 * w)
    pad_y = int(0.25 * h)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(img.shape[1], x + w + pad_x)
    y2 = min(img.shape[0], y + h + pad_y)
    return img[y1:y2, x1:x2], True


def _softmax_with_temperature(logits: torch.Tensor) -> np.ndarray:
    calibrated = logits / TEMPERATURE
    return torch.softmax(calibrated, dim=1)[0].cpu().numpy()


def _normalize_prediction(probabilities: np.ndarray):
    top_two = np.sort(probabilities)[-2:]
    margin = float(top_two[-1] - top_two[-2]) if len(top_two) == 2 else float(top_two[-1])
    entropy = float(-np.sum(probabilities * np.log(probabilities + 1e-10)))
    confidence = float(probabilities.max())
    return confidence, margin, entropy


def _smoothed_probabilities(probabilities: np.ndarray) -> np.ndarray:
    PREDICTION_HISTORY.append(probabilities)
    stacked = np.stack(PREDICTION_HISTORY, axis=0)
    return stacked.mean(axis=0)


def predict_emotion(image_path):
    img = cv2.imread(image_path)
    return predict_emotion_from_image(img)


def predict_emotion_from_bytes(image_bytes: bytes):
    if not image_bytes:
        return {"emotion": "Normal", "confidence": 0.0, "status": "image_bytes_empty"}
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(array, cv2.IMREAD_COLOR)
    return predict_emotion_from_image(img)


def predict_emotion_from_image(img):
    if img is None:
        return {"emotion": "Normal", "confidence": 0.0, "status": "image_read_error"}

    try:
        face_roi, face_detected = detect_and_extract_face(img)
        if not face_detected:
            return {
                "emotion": "Normal",
                "confidence": 0.15,
                "status": "no_face_detected",
                "face_detected": False,
            }

        variants = preprocess_variants(face_roi)
        logits_sum = None
        with torch.no_grad():
            for tensor in variants:
                logits = model(tensor)
                logits_sum = logits if logits_sum is None else logits_sum + logits

        averaged_logits = logits_sum / len(variants)
        probabilities = _softmax_with_temperature(averaged_logits)
        probabilities = _smoothed_probabilities(probabilities)

        pred_index = int(np.argmax(probabilities))
        confidence, margin, entropy = _normalize_prediction(probabilities)
        predicted_label = LABELS[pred_index]
        display_emotion = DISPLAY_MAPPING.get(predicted_label, "Normal")

        if confidence >= 0.56 and margin >= 0.12 and entropy <= 1.02:
            return {
                "emotion": display_emotion,
                "confidence": round(confidence, 4),
                "status": "ensemble_prediction",
                "face_detected": True,
                "margin": round(margin, 4),
                "entropy": round(entropy, 4),
                "raw_label": predicted_label,
            }

        return {
            "emotion": "Normal",
            "confidence": round(min(confidence, 0.55), 4),
            "status": "low_confidence_default",
            "face_detected": True,
            "margin": round(margin, 4),
            "entropy": round(entropy, 4),
            "raw_label": predicted_label,
        }
    except Exception as error:
        logger.error("Emotion detection error: %s", error, exc_info=True)
        return {"emotion": "Normal", "confidence": 0.0, "status": f"error: {error}"}

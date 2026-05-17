from models.emotion_model import predict_emotion, predict_emotion_from_bytes

def detect_emotion(image_path):
    return predict_emotion(image_path)


def detect_emotion_bytes(image_bytes: bytes):
    return predict_emotion_from_bytes(image_bytes)

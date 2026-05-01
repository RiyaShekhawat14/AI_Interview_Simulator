from models.emotion_model import predict_emotion

def detect_emotion(image_path):
    emotion = predict_emotion(image_path)
    return emotion
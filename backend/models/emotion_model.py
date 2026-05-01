import torch
import torch.nn as nn
import cv2

# Simple CNN Model (dummy for now)
class EmotionCNN(nn.Module):
    def __init__(self):
        super(EmotionCNN, self).__init__()
        self.fc = nn.Linear(48*48, 3)  # 3 emotions

    def forward(self, x):
        x = x.view(x.size(0), -1)
        return self.fc(x)

# Load model
model = EmotionCNN()
model.eval()

# Emotion labels
emotion_labels = ["Happy", "Neutral", "Nervous"]

def predict_emotion(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (48, 48))

    tensor = torch.tensor(resized, dtype=torch.float32).unsqueeze(0).unsqueeze(0)

    with torch.no_grad():
        output = model(tensor)
        _, predicted = torch.max(output, 1)

    return emotion_labels[predicted.item()]
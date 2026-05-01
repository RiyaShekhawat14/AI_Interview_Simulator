from services.emotion_service import detect_emotion

@router.post("/detect-emotion")
async def detect_emotion_api(file: UploadFile = File(...)):
    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    emotion = detect_emotion(file_path)

    import os
    os.remove(file_path)

    return {"emotion": emotion}
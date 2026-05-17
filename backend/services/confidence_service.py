def analyze_confidence(answer_text):
    words = len(answer_text.split())

    if words < 20:
        return "Low"
    elif words < 60:
        return "Medium"
    else:
        return "High"
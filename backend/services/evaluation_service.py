from difflib import SequenceMatcher

try:
    from sentence_transformers import SentenceTransformer, util
except Exception:
    SentenceTransformer = None
    util = None

model = SentenceTransformer("all-MiniLM-L6-v2") if SentenceTransformer else None


def evaluate_answer(user_answer: str, reference_answer: str) -> dict:
    if not user_answer or not user_answer.strip():
        return {"score": 0, "feedback": "Answer was empty.", "similarity": 0.0}

    if model and util:
        emb_user = model.encode(user_answer, convert_to_tensor=True)
        emb_ref = model.encode(reference_answer, convert_to_tensor=True)
        similarity = util.cos_sim(emb_user, emb_ref).item()
    else:
        similarity = SequenceMatcher(
            None, user_answer.lower().strip(), reference_answer.lower().strip()
        ).ratio()

    score = int(max(0, min(100, round(similarity * 100))))

    if score >= 80:
        feedback = "Strong answer with good relevance."
    elif score >= 60:
        feedback = "Good answer, but add more concrete examples."
    elif score >= 40:
        feedback = "Partially relevant answer, improve structure and clarity."
    else:
        feedback = "Answer is weakly aligned. Focus on role-specific examples."

    return {"score": score, "feedback": feedback, "similarity": round(similarity, 4)}
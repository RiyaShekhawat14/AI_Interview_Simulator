from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')

def evaluate_answer(user_answer, expected_answer):
    emb1 = model.encode(user_answer, convert_to_tensor=True)
    emb2 = model.encode(expected_answer, convert_to_tensor=True)

    similarity = util.cos_sim(emb1, emb2).item()

    if similarity > 0.75:
        return "Excellent answer"
    elif similarity > 0.5:
        return "Good but can improve"
    else:
        return "Weak answer, revise concepts"
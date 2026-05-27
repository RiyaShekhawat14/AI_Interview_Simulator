import os

from services.ollama_service import call_ollama_with_model_fallback


def _fallback_evaluation(question, code, language):
    stripped = (code or "").strip()
    if not stripped:
        return {
            "evaluation": (
                "Verdict: Incomplete\n"
                "Score: 15/100\n"
                "Feedback: No code was submitted. Start by outlining the approach, then write a working solution."
            )
        }

    line_count = len(stripped.splitlines())
    mentions_function = any(token in stripped for token in ["def ", "function ", "class ", "return "])
    question_hint = "time complexity and edge cases"
    if line_count >= 3 and mentions_function:
        verdict = "Partially Correct"
        score = 68
        feedback = (
            f"Verdict: {verdict}\n"
            f"Score: {score}/100\n"
            "Feedback: A structured solution was submitted, but the local fallback evaluator cannot fully execute it. "
            f"Explain the approach for '{question}', add {question_hint}, and walk through one example in {language}."
        )
    else:
        verdict = "Incomplete"
        score = 42
        feedback = (
            f"Verdict: {verdict}\n"
            f"Score: {score}/100\n"
            "Feedback: The answer looks too short or incomplete. Add a clearer algorithm, handle edge cases, "
            f"and explain complexity for the {language} solution."
        )

    return {"evaluation": feedback}


def evaluate_code(question, code, language):
    prompt = f"""
You are a technical interview evaluator.

Interview question:
{question}

Candidate code answer in {language}:
{code}

Evaluate whether this solution correctly answers the question. Include:
- a short verdict (Correct / Incorrect / Incomplete)
- any obvious syntax or logic issues
- a brief score out of 100
- concise feedback and suggestions for improvement

Respond in plain text.
"""

    try:
        evaluation, _ = call_ollama_with_model_fallback(
            prompt,
            temperature=0.5,
            num_predict=220,
        )
        return {"evaluation": evaluation}
    except Exception:
        return _fallback_evaluation(question, code, language)

import os
import requests

LLAMA_API_URL = os.getenv("LLAMA_API_URL", "http://127.0.0.1:11434/api/generate")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "mistral:latest")
LLAMA_FALLBACK_MODEL = os.getenv("LLAMA_FALLBACK_MODEL", "llama3:8b")
DEFAULT_OLLAMA_URLS = [
    "http://127.0.0.1:11434/api/generate",
    "http://127.0.0.1:11435/api/generate",
]
LLM_DISABLED = False
LLAMA_TIMEOUT_SECONDS = int(os.getenv("LLAMA_TIMEOUT_SECONDS", "45"))


def _call_llama(prompt, model=LLAMA_MODEL, temperature=0.5, num_predict=220, timeout=None):
    global LLM_DISABLED
    if LLM_DISABLED:
        raise Exception("Ollama temporarily disabled after a connection failure.")

    timeout = timeout or LLAMA_TIMEOUT_SECONDS
    urls = [LLAMA_API_URL]
    if not os.getenv("LLAMA_API_URL"):
        urls.extend([url for url in DEFAULT_OLLAMA_URLS if url not in urls])

    last_error = None
    for url in urls:
        try:
            response = requests.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": num_predict,
                    },
                },
                timeout=timeout,
            )

            if response.status_code != 200:
                last_error = Exception(
                    f"Ollama status {response.status_code} at {url}: {response.text[:120]}"
                )
                continue

            result = response.json()
            output = (result.get("response") or result.get("generated_text") or result.get("result") or "").strip()
            if output:
                return output
            last_error = Exception(f"Empty Llama response from {url}")
        except requests.RequestException as error:
            last_error = error

    LLM_DISABLED = True
    raise Exception(last_error or "Unable to connect to Ollama on any configured port.")


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
        evaluation = _call_llama(prompt)
        return {"evaluation": evaluation}
    except Exception:
        if LLAMA_FALLBACK_MODEL and LLAMA_FALLBACK_MODEL != LLAMA_MODEL:
            try:
                evaluation = _call_llama(prompt, model=LLAMA_FALLBACK_MODEL)
                return {"evaluation": evaluation}
            except Exception:
                pass
        return _fallback_evaluation(question, code, language)

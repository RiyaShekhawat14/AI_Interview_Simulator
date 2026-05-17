import os
import random
import requests

LLAMA_API_URL = os.getenv("LLAMA_API_URL", "http://127.0.0.1:11434/api/generate")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "mistral:latest")
LLAMA_FALLBACK_MODEL = os.getenv("LLAMA_FALLBACK_MODEL", "llama3:8b")
LLAMA_TIMEOUT_SECONDS = int(os.getenv("LLAMA_TIMEOUT_SECONDS", "45"))
DEFAULT_OLLAMA_URLS = [
    "http://127.0.0.1:11434/api/generate",
    "http://127.0.0.1:11435/api/generate",
]
LLM_DISABLED = False

GENERAL_FALLBACK_QUESTIONS = [
    "Tell me about yourself and your recent work.",
    "What project are you most proud of?",
    "How do you debug a production issue?",
    "Describe a time you improved system performance.",
    "How do you handle conflicting priorities on a team?",
    "What trade-offs do you consider in system design?",
    "Tell me about a challenging bug you fixed.",
]

DSA_FALLBACK_QUESTIONS = [
    "Given an array of integers, return the two indices whose values add up to a target.",
    "Design an LRU cache with O(1) get and put operations.",
    "Find the first non-repeating character in a string efficiently.",
    "Detect whether a linked list contains a cycle and explain the complexity.",
    "Merge overlapping intervals from a list of start and end pairs.",
]

_last_fallback_question = None


def _fallback_question(category: str, asked_questions: list[str] | None = None) -> str:
    global _last_fallback_question
    pool = DSA_FALLBACK_QUESTIONS if category == "dsa" else GENERAL_FALLBACK_QUESTIONS
    asked_set = set(asked_questions or [])
    choices = [
        question
        for question in pool
        if question != _last_fallback_question and question not in asked_set
    ]
    next_question = random.choice(choices or pool)
    _last_fallback_question = next_question
    return next_question


def _clean_question(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    prefixes = ['Question:', 'Interviewer:', '"', "'"]
    updated = True
    while updated:
        updated = False
        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                updated = True
    cleaned = cleaned.strip(' "\'')
    if cleaned and not cleaned.endswith(("?", ".")):
        cleaned = f"{cleaned}?"
    return cleaned


def reset_ollama_circuit() -> None:
    global LLM_DISABLED
    LLM_DISABLED = False


def _call_llama(
    prompt: str,
    model: str = LLAMA_MODEL,
    temperature: float = 0.7,
    num_predict: int = 60,
    timeout: int | None = None,
) -> str:
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

            payload = response.json()
            text = (
                payload.get("response")
                or payload.get("generated_text")
                or payload.get("result")
                or ""
            ).strip()
            if text:
                return _clean_question(text.splitlines()[0].strip())
            last_error = Exception(f"Empty Llama response from {url}")
        except requests.RequestException as error:
            last_error = error

    LLM_DISABLED = True
    raise Exception(last_error or "Unable to connect to Ollama on any configured port.")


def check_ollama() -> str:
    reset_ollama_circuit()
    return _call_llama(
        "Reply with one short sentence confirming you are available for interview question generation.",
        temperature=0.0,
        num_predict=20,
        timeout=max(4, LLAMA_TIMEOUT_SECONDS),
    )


def generate_question_result(
    resume_text: str,
    role: str,
    company: str,
    last_answer: str = "",
    asked_questions: list[str] | None = None,
    question_category: str = "general",
) -> dict:
    resume_excerpt = (resume_text or "").strip()
    if len(resume_excerpt) < 20:
        resume_excerpt = (
            "Candidate has software engineering, problem solving, and collaboration experience."
        )

    resume_hint = " ".join(resume_excerpt[:320].split())
    answer_hint = " ".join((last_answer or "No previous answer.").strip()[:160].split())

    if question_category == "dsa":
        prompt = (
            f"Technical interviewer for {company}. Role: {role}. "
            f"Resume: {resume_hint}. Last answer: {answer_hint}. "
            "Ask one DSA coding question only. No explanation."
        )
    else:
        prompt = (
            f"Hiring manager for {company}. Role: {role}. "
            f"Resume: {resume_hint}. Last answer: {answer_hint}. "
            "Ask one short interview question only. No explanation."
        )

    source = "fallback"
    model = "rule-based fallback"
    error_message = ""

    try:
        question = _call_llama(
            prompt,
            num_predict=38 if question_category == "dsa" else 18,
        )
        source = "ollama"
        model = LLAMA_MODEL
    except Exception as primary_error:
        error_message = str(primary_error)
        if LLAMA_FALLBACK_MODEL and LLAMA_FALLBACK_MODEL != LLAMA_MODEL:
            try:
                reset_ollama_circuit()
                question = _call_llama(
                    prompt,
                    model=LLAMA_FALLBACK_MODEL,
                    num_predict=38 if question_category == "dsa" else 18,
                )
                source = "ollama-fallback-model"
                model = LLAMA_FALLBACK_MODEL
                error_message = ""
            except Exception as fallback_error:
                error_message = str(fallback_error)
                question = _fallback_question(question_category, asked_questions)
        else:
            question = _fallback_question(question_category, asked_questions)

    if asked_questions and question in set(asked_questions):
        question = _fallback_question(question_category, asked_questions)
        source = "fallback"
        model = "rule-based fallback"

    return {
        "question": question,
        "source": source,
        "model": model,
        "error": error_message,
        "category": question_category,
    }


def generate_question(
    resume_text: str,
    role: str,
    company: str,
    last_answer: str = "",
    asked_questions: list[str] | None = None,
    question_category: str = "general",
) -> str:
    return generate_question_result(
        resume_text=resume_text,
        role=role,
        company=company,
        last_answer=last_answer,
        asked_questions=asked_questions,
        question_category=question_category,
    )["question"]

import os
import random

from services.ollama_service import (
    LLAMA_API_URL,
    LLAMA_MODEL,
    LLAMA_TIMEOUT_SECONDS,
    call_ollama_with_model_fallback,
)

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
    "Two Sum: Given an integer array nums and an integer target, return the indices of the two numbers such that they add up to target. Assume exactly one valid answer exists and each element may be used at most once.",
    "Longest Substring Without Repeating Characters: Given a string s, return the length of the longest substring that contains no repeated characters. Explain the sliding-window approach and its complexity.",
    "Merge Intervals: Given an array of intervals where intervals[i] = [start, end], merge all overlapping intervals and return the condensed result sorted by start time.",
    "Top K Frequent Elements: Given an integer array nums and an integer k, return the k most frequent elements. Aim for a solution better than O(n log n) when possible.",
    "LRU Cache Design: Implement an LRU cache that supports get(key) and put(key, value) in O(1) average time, evicting the least recently used item when capacity is exceeded.",
]

_last_fallback_question = None
QUESTION_GENERATION_TIMEOUT_SECONDS = float(
    os.getenv("QUESTION_GENERATION_TIMEOUT_SECONDS", str(min(8, LLAMA_TIMEOUT_SECONDS)))
)
DSA_GENERATION_TIMEOUT_SECONDS = float(
    os.getenv("DSA_GENERATION_TIMEOUT_SECONDS", str(min(10, max(QUESTION_GENERATION_TIMEOUT_SECONDS, 8))))
)
HEALTH_CHECK_TIMEOUT_SECONDS = float(
    os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "3")
)


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

def check_ollama() -> str:
    timeout = min(HEALTH_CHECK_TIMEOUT_SECONDS, max(1.0, LLAMA_TIMEOUT_SECONDS))
    text, _ = call_ollama_with_model_fallback(
        "Reply with one short sentence confirming you are available for interview question generation.",
        temperature=0.0,
        num_predict=20,
        timeout=timeout,
    )
    return _clean_question(text.splitlines()[0].strip())


def _question_generation_timeout(question_category: str) -> float:
    if question_category == "dsa":
        return max(4.0, DSA_GENERATION_TIMEOUT_SECONDS)
    return max(3.0, QUESTION_GENERATION_TIMEOUT_SECONDS)


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
        question, model = call_ollama_with_model_fallback(
            prompt,
            temperature=0.7,
            num_predict=38 if question_category == "dsa" else 18,
            timeout=_question_generation_timeout(question_category),
        )
        question = _clean_question(question.splitlines()[0].strip())
        source = "ollama-fallback-model" if model != LLAMA_MODEL else "ollama"
    except Exception as primary_error:
        error_message = str(primary_error)
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

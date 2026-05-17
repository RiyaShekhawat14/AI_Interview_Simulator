from collections import Counter
import os
import re
import requests
from typing import Any

LLAMA_API_URL = os.getenv("LLAMA_API_URL", "http://127.0.0.1:11434/api/generate")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "mistral:latest")
LLAMA_FALLBACK_MODEL = os.getenv("LLAMA_FALLBACK_MODEL", "llama3:8b")
DEFAULT_OLLAMA_URLS = [
    "http://127.0.0.1:11434/api/generate",
    "http://127.0.0.1:11435/api/generate",
]
LLM_DISABLED = False
LLAMA_TIMEOUT_SECONDS = int(os.getenv("LLAMA_TIMEOUT_SECONDS", "45"))

FILLER_WORDS = [
    r"\bum\b",
    r"\buh\b",
    r"\blike\b",
    r"\byou know\b",
    r"\bkinda\b",
    r"\bsorta\b",
    r"\bbasically\b",
    r"\bliterally\b",
    r"\bactually\b",
    r"\byeah\b",
    r"\berr\b",
]


def _call_llama(prompt: str, model: str = LLAMA_MODEL, temperature: float = 0.5, num_predict: int = 350, timeout: int | None = None) -> str:
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
                last_error = Exception(f"Ollama status {response.status_code} at {url}: {response.text[:120]}")
                continue

            payload = response.json()
            text = (payload.get("response") or payload.get("generated_text") or payload.get("result") or "").strip()
            if text:
                return text
            last_error = Exception(f"Empty Llama response from {url}")
        except requests.RequestException as error:
            last_error = error

    LLM_DISABLED = True
    raise Exception(last_error or "Unable to connect to Ollama on any configured port.")


def _call_llama_with_fallback(prompt: str, temperature: float = 0.4, num_predict: int = 350) -> str:
    try:
        return _call_llama(prompt, model=LLAMA_MODEL, temperature=temperature, num_predict=num_predict)
    except Exception as primary_error:
        if LLAMA_FALLBACK_MODEL and LLAMA_FALLBACK_MODEL != LLAMA_MODEL:
            try:
                return _call_llama(prompt, model=LLAMA_FALLBACK_MODEL, temperature=temperature, num_predict=num_predict)
            except Exception:
                pass
        raise primary_error


def _count_filler_words(text: str) -> int:
    lowered = text.lower()
    return sum(len(re.findall(pattern, lowered)) for pattern in FILLER_WORDS)


def _phase_label(response: dict[str, Any]) -> str:
    return "DSA" if response.get("phase") == "dsa" else "General"


def _score_response(response: dict[str, Any]) -> int:
    answer_text = (response.get("answer") or "").strip()
    word_count = len(answer_text.split())
    filler_count = _count_filler_words(answer_text)
    emotion_confidence = float(response.get("emotion_confidence", 0.0) or 0.0)

    score = 35
    score += min(word_count, 120) * 0.35
    score -= min(filler_count * 2, 10)

    if response.get("phase") == "dsa":
        score = 45
        score += min(len(answer_text), 600) / 20
        evaluation_text = str(response.get("evaluation", {}).get("evaluation", "")).lower()
        if "correct" in evaluation_text:
            score += 20
        if "incomplete" in evaluation_text or "incorrect" in evaluation_text:
            score -= 8
        if "syntax" in evaluation_text or "logic" in evaluation_text:
            score -= 6

    if response.get("emotion") in {"Confident", "Interested"}:
        score += 4 * max(emotion_confidence, 0.4)
    elif response.get("emotion") in {"Nervous", "Disappointed"}:
        score -= 3 * max(emotion_confidence, 0.3)

    return max(0, min(100, int(round(score))))


def _fallback_corrected_answer(question: str, answer: str, response: dict[str, Any]) -> str:
    if response.get("phase") == "dsa":
        return (
            "Explain the algorithm clearly, mention time and space complexity, and walk through "
            "one example before or after presenting the final solution."
        )

    if len(answer.split()) < 20:
        return (
            f"For '{question}', give a structured STAR-style response with context, your actions, "
            "the technical choices you made, and a measurable result."
        )

    return (
        "Strengthen the answer by making it more specific: describe the problem, your role, "
        "the exact steps you took, and the outcome with numbers when possible."
    )


def _fallback_improvement(response: dict[str, Any]) -> str:
    if response.get("phase") == "dsa":
        return "Explain the algorithm before coding, then mention complexity and edge cases."
    return "Use a clearer structure with situation, action, impact, and one concrete example."


def _fallback_corrected_code(response: dict[str, Any]) -> str:
    question = (response.get("question") or "").lower()
    language = (response.get("language") or "python").lower()

    if "two indices" in question or "two numbers" in question or "target" in question:
        snippets = {
            "python": """def two_sum(nums, target):
    seen = {}
    for index, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], index]
        seen[num] = index
    return []""",
            "javascript": """function twoSum(nums, target) {
  const seen = new Map();
  for (let index = 0; index < nums.length; index += 1) {
    const complement = target - nums[index];
    if (seen.has(complement)) {
      return [seen.get(complement), index];
    }
    seen.set(nums[index], index);
  }
  return [];
}""",
            "java": """import java.util.*;

class Solution {
    public int[] twoSum(int[] nums, int target) {
        Map<Integer, Integer> seen = new HashMap<>();
        for (int index = 0; index < nums.length; index++) {
            int complement = target - nums[index];
            if (seen.containsKey(complement)) {
                return new int[]{seen.get(complement), index};
            }
            seen.put(nums[index], index);
        }
        return new int[0];
    }
}""",
        }
        return snippets.get(language, snippets["python"])

    if "non-repeating character" in question:
        snippets = {
            "python": """from collections import Counter

def first_non_repeating_char(text):
    counts = Counter(text)
    for char in text:
        if counts[char] == 1:
            return char
    return None""",
            "javascript": """function firstNonRepeatingChar(text) {
  const counts = new Map();
  for (const char of text) {
    counts.set(char, (counts.get(char) || 0) + 1);
  }
  for (const char of text) {
    if (counts.get(char) === 1) {
      return char;
    }
  }
  return null;
}""",
        }
        return snippets.get(language, snippets["python"])

    return (
        "Provide a clean working solution here with edge-case handling, then explain the complexity "
        "and one sample walkthrough."
    )


def _generate_ai_review(response: dict[str, Any]) -> dict[str, str]:
    question = response.get("question", "")
    answer = response.get("answer", "")
    phase = _phase_label(response)
    code_eval = response.get("evaluation", {}).get("evaluation", "")
    language = response.get("language", "")

    if response.get("phase") == "dsa":
        prompt = f"""
You are an expert technical interview coach.

Interview phase: {phase}
Programming language: {language}
Question: {question}
Candidate code answer:
{answer}

Code evaluation context:
{code_eval}

Return exactly four sections in plain text:
Corrected Answer: <2-4 sentence explanation of the ideal solution and reasoning>
Corrected Code: <only the corrected code in {language}>
Improvement: <one concise sentence>
Highlights: <one concise sentence about what the candidate did well>
"""
    else:
        prompt = f"""
You are an expert interview coach.

Interview phase: {phase}
Question: {question}
Candidate answer:
{answer}

Code evaluation context:
{code_eval}

Return exactly three sections in plain text:
Corrected Answer: <improved ideal answer in 2-5 sentences>
Improvement: <one concise sentence>
Highlights: <one concise sentence about what the candidate did well>
"""

    try:
        review = _call_llama_with_fallback(
            prompt,
            temperature=0.3,
            num_predict=420 if response.get("phase") == "dsa" else 220,
        )
        corrected = ""
        corrected_code = ""
        improvement = ""
        highlight = ""
        current_section = ""

        for line in review.splitlines():
            stripped = line.rstrip()
            lowered = stripped.lower().strip()
            if lowered.startswith("corrected answer:"):
                current_section = "corrected_answer"
                corrected = stripped.split(":", 1)[1].strip()
                continue
            if lowered.startswith("corrected code:"):
                current_section = "corrected_code"
                corrected_code = stripped.split(":", 1)[1].strip()
                continue
            if lowered.startswith("improvement:"):
                current_section = "improvement"
                improvement = stripped.split(":", 1)[1].strip()
                continue
            if lowered.startswith("highlights:"):
                current_section = "highlight"
                highlight = stripped.split(":", 1)[1].strip()
                continue

            if not stripped.strip():
                continue

            if current_section == "corrected_answer":
                corrected = f"{corrected}\n{stripped}".strip()
            elif current_section == "corrected_code":
                corrected_code = f"{corrected_code}\n{stripped}".strip()
            elif current_section == "improvement":
                improvement = f"{improvement} {stripped.strip()}".strip()
            elif current_section == "highlight":
                highlight = f"{highlight} {stripped.strip()}".strip()

        return {
            "corrected_answer": corrected or _fallback_corrected_answer(question, answer, response),
            "corrected_code": corrected_code or (_fallback_corrected_code(response) if response.get("phase") == "dsa" else ""),
            "improvement": improvement or _fallback_improvement(response),
            "highlight": highlight or "The answer addressed the question directly.",
        }
    except Exception:
        return {
            "corrected_answer": _fallback_corrected_answer(question, answer, response),
            "corrected_code": _fallback_corrected_code(response) if response.get("phase") == "dsa" else "",
            "improvement": _fallback_improvement(response),
            "highlight": "The answer stayed on topic and can be strengthened with more detail.",
        }


def _emotion_summary(responses: list[dict[str, Any]]) -> tuple[str, dict[str, int], float]:
    emotions = [response.get("emotion", "Normal") for response in responses]
    counts = dict(Counter(emotions))
    dominant = max(counts, key=counts.get) if counts else "Normal"
    avg_confidence = 0.0
    if responses:
        avg_confidence = round(
            sum(float(response.get("emotion_confidence", 0.0) or 0.0) for response in responses) / len(responses),
            2,
        )
    return dominant, counts, avg_confidence


def _confidence_band(overall_score: int, avg_emotion_confidence: float) -> str:
    composite = overall_score * 0.7 + avg_emotion_confidence * 100 * 0.3
    if composite >= 80:
        return "High"
    if composite >= 60:
        return "Moderate"
    return "Needs Improvement"


def _communication_band(responses: list[dict[str, Any]]) -> str:
    if not responses:
        return "Needs Improvement"

    total_words = sum(len((response.get("answer") or "").split()) for response in responses if response.get("phase") != "dsa")
    filler_total = sum(_count_filler_words(response.get("answer", "")) for response in responses if response.get("phase") != "dsa")
    avg_words = total_words / max(1, len([r for r in responses if r.get("phase") != "dsa"]))

    if avg_words >= 45 and filler_total <= 6:
        return "Strong"
    if avg_words >= 25:
        return "Good"
    return "Needs Improvement"


def generate_interview_report(
    responses: list[dict[str, Any]],
    role: str,
    company: str,
    started_at: float | None = None,
    finished_at: float | None = None,
) -> dict[str, Any]:
    if not responses:
        return {
            "overall_score": 0,
            "assessment": "No interview responses were recorded.",
            "emotion_summary": "No emotion data available.",
            "confidence_report": "Low confidence due to missing answers.",
            "communication_report": "No communication data available.",
            "strengths": [],
            "weaknesses": ["Complete the interview to unlock feedback."],
            "recommendations": ["Answer at least five questions for a meaningful report."],
            "responses": [],
            "emotion_breakdown": {},
            "response_count": 0,
            "code_challenges_completed": 0,
            "duration_seconds": 0,
        }

    enriched_responses = []
    strengths = []
    weaknesses = []
    recommendations = []
    total_score = 0

    for response in responses:
        review = _generate_ai_review(response)
        score = _score_response(response)
        total_score += score

        feedback = review["highlight"]
        if response.get("phase") == "dsa":
            feedback = response.get("evaluation", {}).get("evaluation", "") or review["highlight"]

        enriched_responses.append(
            {
                "question": response.get("question", ""),
                "answer": response.get("answer", ""),
                "phase": response.get("phase", "general"),
                "language": response.get("language", ""),
                "emotion": response.get("emotion", "Normal"),
                "emotion_confidence": float(response.get("emotion_confidence", 0.0) or 0.0),
                "score": score,
                "feedback": feedback,
                "improvement": review["improvement"],
                "corrected_answer": review["corrected_answer"],
                "corrected_code": review.get("corrected_code", ""),
                "evaluation": response.get("evaluation", {}),
            }
        )

        if score >= 75:
            strengths.append(review["highlight"])
        else:
            weaknesses.append(review["improvement"])
            recommendations.append(review["corrected_answer"])

    overall_score = int(round(total_score / len(responses)))
    dominant_emotion, emotion_breakdown, avg_emotion_confidence = _emotion_summary(responses)
    confidence_band = _confidence_band(overall_score, avg_emotion_confidence)
    communication_band = _communication_band(responses)

    assessment = (
        f"You completed a {role} interview for {company} with an overall score of {overall_score}/100. "
        f"The strongest pattern was {dominant_emotion.lower()} energy, and your responses show "
        f"{confidence_band.lower()} confidence with {communication_band.lower()} communication."
    )

    duration_seconds = 0
    if started_at and finished_at and finished_at >= started_at:
        duration_seconds = int(round(finished_at - started_at))

    return {
        "overall_score": overall_score,
        "assessment": assessment,
        "emotion_summary": f"Dominant emotion: {dominant_emotion}. Average emotion confidence: {avg_emotion_confidence:.2f}.",
        "confidence_report": f"Confidence level: {confidence_band}. This combines speaking depth and emotion stability across the interview.",
        "communication_report": f"Communication level: {communication_band}. Filler-word pressure and answer depth were both considered.",
        "strengths": strengths[:5] or ["You stayed engaged and completed the interview flow."],
        "weaknesses": weaknesses[:5] or ["Keep improving answer specificity and structure."],
        "recommendations": recommendations[:5] or ["Practice more role-specific storytelling and DSA explanations."],
        "responses": enriched_responses,
        "emotion_breakdown": emotion_breakdown,
        "response_count": len(responses),
        "code_challenges_completed": len([response for response in responses if response.get("phase") == "dsa"]),
        "duration_seconds": duration_seconds,
        "role": role,
        "company": company,
    }

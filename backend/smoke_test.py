import importlib
import os
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _assert_status(name: str, response, expected_status: int = 200) -> None:
    if response.status_code != expected_status:
        raise RuntimeError(f"{name} failed with status {response.status_code}: {response.text}")


def main() -> int:
    os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
    os.environ.setdefault(
        "ALLOWED_ORIGINS",
        "https://ai-interview-simulator-clkdysjhl-riyashekhawat14s-projects.vercel.app,https://ai-interview-simulator-pc8iy5enf-riyashekhawat14s-projects.vercel.app",
    )
    os.environ.setdefault("HEALTH_CHECK_TIMEOUT_SECONDS", "3")

    app_module = importlib.import_module("backend.main")
    email = f"smoke-{int(time.time())}@example.com"

    with TestClient(app_module.app) as client:
        _assert_status("GET /", client.get("/"))

        health_started = time.monotonic()
        health = client.get("/health")
        health_elapsed = time.monotonic() - health_started
        _assert_status("GET /health", health)
        if health_elapsed > 8:
            raise RuntimeError(f"Health check took too long: {health_elapsed:.2f}s")

        preflight = client.options(
            "/auth/register",
            headers={
                "Origin": "https://ai-interview-simulator-clkdysjhl-riyashekhawat14s-projects.vercel.app",
                "Access-Control-Request-Method": "POST",
            },
        )
        _assert_status("OPTIONS /auth/register", preflight)
        allowed_origin = preflight.headers.get("access-control-allow-origin")
        if allowed_origin != "https://ai-interview-simulator-clkdysjhl-riyashekhawat14s-projects.vercel.app":
            raise RuntimeError(f"Unexpected CORS allow-origin: {allowed_origin}")

        register = client.post(
            "/auth/register",
            json={
                "email": email,
                "full_name": "Smoke Test User",
                "password": "password123",
            },
        )
        _assert_status("POST /auth/register", register)

        token = register.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        _assert_status("GET /auth/me", client.get("/auth/me", headers=headers))

        start = client.post(
            "/interview/start",
            data={
                "role": "Software Engineer",
                "company": "OpenAI",
                "resume_text": "Backend and frontend engineer with production API experience.",
            },
            headers=headers,
        )
        _assert_status("POST /interview/start", start)

        session_id = start.json()["session_id"]
        next_question = client.post(
            "/interview/next",
            data={"session_id": session_id},
            headers=headers,
        )
        _assert_status("POST /interview/next", next_question)

        first_step = next_question.json()
        if first_step.get("phase") != "general":
            raise RuntimeError(f"Expected general phase first, got {first_step}")

        latest_step = first_step
        for index in range(4):
            latest_step = client.post(
                "/interview/next",
                data={
                    "session_id": session_id,
                    "last_answer": f"General answer {index + 1}",
                },
                headers=headers,
            )
            _assert_status(f"POST /interview/next general #{index + 2}", latest_step)

        fifth_transition = client.post(
            "/interview/next",
            data={
                "session_id": session_id,
                "last_answer": "General answer 5",
            },
            headers=headers,
        )
        _assert_status("POST /interview/next transition to dsa", fifth_transition)
        dsa_step = fifth_transition.json()
        if dsa_step.get("phase") != "dsa" or dsa_step.get("type") != "code":
            raise RuntimeError(f"Expected DSA IDE step after 5 general questions, got {dsa_step}")

        first_code = client.post(
            "/interview/submit-code",
            data={
                "session_id": session_id,
                "code": "def solve(nums):\n    return nums\n",
                "language": "python",
            },
            headers=headers,
        )
        _assert_status("POST /interview/submit-code #1", first_code)

        second_dsa = client.post(
            "/interview/next",
            data={"session_id": session_id},
            headers=headers,
        )
        _assert_status("POST /interview/next dsa #2", second_dsa)
        second_dsa_step = second_dsa.json()
        if second_dsa_step.get("phase") != "dsa" or second_dsa_step.get("type") != "code":
            raise RuntimeError(f"Expected second DSA IDE step, got {second_dsa_step}")

        second_code = client.post(
            "/interview/submit-code",
            data={
                "session_id": session_id,
                "code": "def solve(value):\n    return value\n",
                "language": "python",
            },
            headers=headers,
        )
        _assert_status("POST /interview/submit-code #2", second_code)

        completed = client.post(
            "/interview/next",
            data={"session_id": session_id},
            headers=headers,
        )
        _assert_status("POST /interview/next complete", completed)
        completed_step = completed.json()
        if completed_step.get("phase") != "complete":
            raise RuntimeError(f"Expected interview completion after 2 DSA questions, got {completed_step}")

        report = client.post(
            "/interview/report",
            data={"session_id": session_id},
            headers=headers,
        )
        _assert_status("POST /interview/report", report)

        _assert_status("GET /reports/latest", client.get("/reports/latest", headers=headers))
        _assert_status("GET /reports/history", client.get("/reports/history", headers=headers))

        payload = {
            "email": email,
            "session_phase": completed_step.get("phase"),
            "report_id": report.json().get("report_id"),
            "overall_score": report.json().get("overall_score"),
        }
        print("Smoke test passed:", payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Smoke test failed: {error}", file=sys.stderr)
        raise SystemExit(1)

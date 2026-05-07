import json
import logging
import re
import traceback

import ollama

logger = logging.getLogger(__name__)

MODEL = "phi4-mini:latest"
DIFF_PREVIEW_LEN = 3000
_MAX_RETRIES = 2

_JSON_FENCE_RE = re.compile(r"```(?:json)?", re.IGNORECASE)


def check_ollama() -> tuple[bool, str]:
    try:
        result = ollama.list()
        if hasattr(result, "models"):
            tags = [m.model for m in result.models]
        else:
            tags = [m.get("model", m.get("name", "")) for m in result.get("models", [])]

        if not any(MODEL in t for t in tags):
            return False, f"Model not found — run: ollama pull {MODEL}"
        return True, "Connected"
    except Exception as exc:
        return False, f"Cannot reach Ollama — run: ollama serve ({exc})"


def analyze_commit_mismatch(message: str, diff: str) -> dict:
    diff_preview = diff[:DIFF_PREVIEW_LEN] if diff else "(empty diff)"

    prompt = f"""You are a senior software engineer reviewing a commit that has been flagged as MISALIGNED.
This means the commit message does not sufficiently describe the actual code changes.
Your job is to explain WHY it is misaligned and provide a better commit message.

COMMIT MESSAGE
--------------
{message}

CODE DIFF
---------
{diff_preview}

INSTRUCTIONS
------------
1. The commit has already been determined to be misaligned — do NOT say it is fine or correct.
2. In "issue", briefly explain what is wrong or missing in the commit message compared to the diff.
3. In "suggested_message", write a clear, specific commit message that accurately describes the diff.
   The suggested message MUST be different from the original commit message.

Respond with STRICT JSON only — no markdown, no preamble, no explanation outside the JSON:
{{
  "issue": "<why the message does not match the diff>",
  "suggested_message": "<a better, more specific commit message>"
}}"""

    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            raw = _generate(prompt)
            result = _extract_json(raw)

            issue = result.get("issue", "").strip()
            suggested = result.get("suggested_message", "").strip()

            if not issue:
                issue = "Commit message does not clearly describe the code changes."
            if not suggested or suggested.strip() == message.strip():
                suggested = f"(improve): {message} — add details about what was changed and why"

            return {"issue": issue, "suggested_message": suggested}

        except Exception as exc:
            last_exc = exc
            logger.warning(
                "analyze_commit_mismatch attempt %d/%d failed: %s: %s",
                attempt, _MAX_RETRIES, type(exc).__name__, exc,
            )
            traceback.print_exc()

    error_detail = f"{type(last_exc).__name__}: {last_exc}"
    logger.error("analyze_commit_mismatch giving up after %d attempts: %s", _MAX_RETRIES, error_detail)

    return {
        "issue": f"LLM analysis failed: {error_detail}",
        "suggested_message": "",
        "llm_error": error_detail,
    }


def analyze_comment(comment: dict) -> dict:
    prompt = f"""You are a code-review analyst.

Return ONLY valid JSON:

{{
  "confused": true/false,
  "confusion_reason": "...",
  "change_predicted": true/false,
  "change_reason": "..."
}}

Rules:
- confused = reviewer does not understand something
- change_predicted = request for fix / refactor / bug

Comment:
{comment.get('message', '')}
"""
    result: dict = {}
    try:
        result = _extract_json(_generate(prompt))
    except Exception as exc:
        logger.warning("analyze_comment failed: %s: %s", type(exc).__name__, exc)
        traceback.print_exc()

    return {
        **comment,
        "confused":         bool(result.get("confused", False)),
        "confusion_reason": result.get("confusion_reason") or "",
        "change_predicted": bool(result.get("change_predicted", False)),
        "change_reason":    result.get("change_reason") or "",
    }


def _generate(prompt: str) -> str:
    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"temperature": 0.0, "num_predict": 400},
    )
    if hasattr(response, "response"):
        text = response.response
    else:
        text = response["response"]

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Ollama returned an empty response — model may have run out of context or memory.")

    return text.strip()


def _extract_json(text: str) -> dict:
    text = _JSON_FENCE_RE.sub("", text).strip("` \n")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output: {text[:300]!r}")
    return json.loads(match.group())
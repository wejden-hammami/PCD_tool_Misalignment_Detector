import json
import re

import ollama

MODEL = "phi4-mini:latest"
DIFF_PREVIEW_LEN = 3000

_JSON_FENCE_RE = re.compile(r"```(?:json)?", re.IGNORECASE)


def check_ollama() -> tuple[bool, str]:
    try:
        tags = [m["model"] for m in ollama.list().get("models", [])]
        if not any(MODEL in t for t in tags):
            return False, f"Model not found — run: ollama pull {MODEL}"
        return True, "Connected"
    except Exception as exc:
        return False, f"Cannot reach Ollama — run: ollama serve ({exc})"


def analyze_commit_mismatch(message: str, diff: str) -> dict:
    diff_preview = diff if diff else "(empty diff)"

    prompt = f"""You are a senior engineer reviewing a commit for message quality.

Compare the commit message to the actual code changes and decide whether
the message correctly describes what was done.

COMMIT MESSAGE
--------------
{message}

CODE DIFF 
-------------------------------------
{diff_preview}

INSTRUCTIONS
------------
1. If the message correctly describes the diff, return an empty "issue".
2. If there is a mismatch, describe it briefly in "issue".
3. Always provide a "suggested_message" that fits the diff precisely.

Respond with STRICT JSON only — no markdown, no preamble:
{{
  "issue": "<short description of mismatch, or empty string>",
  "suggested_message": "<better commit message>"
}}"""

    try:
        return _extract_json(_generate(prompt))
    except Exception as exc:
        return {
            "issue": f"LLM analysis unavailable: {exc}",
            "suggested_message": message,
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
    try:
        result = _extract_json(_generate(prompt))
    except Exception:
        result = {}

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
    return response["response"].strip()


def _extract_json(text: str) -> dict:
    text = _JSON_FENCE_RE.sub("", text).strip("` \n")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in model output: {text[:200]!r}")
    return json.loads(match.group())
import base64
import json
import re
import requests
from urllib.parse import quote

DEFAULT_BASE = "https://review.opendev.org"




def _get(url: str, timeout: int = 15) -> requests.Response:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r


def _parse_gerrit(text: str) -> dict | list:
    return json.loads(re.sub(r"^\)\]\}'\s*", "", text, count=1))


def _encode_change_id(change_id: str) -> str:
    if "~" in change_id:
        return "%7E".join(quote(p, safe="") for p in change_id.split("~"))
    return quote(change_id, safe="")


def _resolve_to_number(change_id: str, base_url: str) -> str:
    if not re.fullmatch(r"I[0-9a-fA-F]{5,}", change_id):
        return change_id

    url = f"{base_url}/changes/?q=change:{change_id}&n=1"
    try:
        results = _parse_gerrit(_get(url).text)
        if results:
            return str(results[0]["_number"])
    except Exception as exc:
        raise ValueError(
            f"Could not resolve Change-Id '{change_id}' to a numeric change number.\n"
            f"Make sure the change exists on {base_url} and is visible anonymously.\n"
            f"Error: {exc}"
        ) from exc

    raise ValueError(
        f"No change found for Change-Id '{change_id}' on {base_url}.\n"
        "Try using the numeric change number (e.g. 933890) instead."
    )



def _parse_diff(raw: str) -> str:
    lines = [
        line for line in raw.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    return "\n".join(lines)




def _fetch_revisions(change_id: str, base_url: str) -> tuple[str, dict]:
    resolved = _resolve_to_number(change_id.strip(), base_url)
    encoded = _encode_change_id(resolved)
    url = f"{base_url}/changes/{encoded}/detail?o=ALL_REVISIONS&o=ALL_COMMITS"

    try:
        data = _parse_gerrit(_get(url).text)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise ValueError(
            f"Gerrit returned HTTP {status} for change '{change_id}'.\n"
            f"• 404 → change not found or not visible anonymously on {base_url}\n"
            f"• 401/403 → authentication required\n"
        ) from exc

    revisions = data.get("revisions", {})
    if not revisions:
        raise ValueError(
            f"Change '{change_id}' has no revisions. "
            "It may be abandoned or the response is malformed."
        )
    return encoded, revisions


def get_latest_patchset(change_id: str, base_url: str = DEFAULT_BASE) -> dict:
    return list_patchsets(change_id, base_url)[-1]


def list_patchsets(change_id: str, base_url: str = DEFAULT_BASE) -> list[dict]:
    encoded, revisions = _fetch_revisions(change_id, base_url)
    patchsets = [
        {
            "patchset": rev["_number"],
            "sha":      sha,
            "message":  rev.get("commit", {}).get("message", "").strip(),
        }
        for sha, rev in revisions.items()
    ]
    return sorted(patchsets, key=lambda p: p["patchset"])


def get_patch_diff(change_id: str, commit: dict, base_url: str = DEFAULT_BASE) -> str:
    sha = commit.get("sha", "")
    if not sha:
        raise ValueError("Commit dict has no 'sha' key.")

    encoded = _encode_change_id(_resolve_to_number(change_id.strip(), base_url))
    url = f"{base_url}/changes/{encoded}/revisions/{sha}/patch"

    try:
        resp = _get(url)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise ValueError(
            f"Could not fetch diff for change '{change_id}' patchset sha '{sha[:7]}' "
            f"(HTTP {status}).\nURL: {url}"
        ) from exc

    raw = resp.text.strip()
    try:
        decoded = base64.b64decode(raw).decode("utf-8", errors="replace")
    except Exception:
        decoded = raw

    return _parse_diff(decoded)
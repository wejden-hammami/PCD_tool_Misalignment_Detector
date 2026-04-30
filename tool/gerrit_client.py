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
    
    cleaned = re.sub(r"^\)\]\}'\s*", "", text, count=1)
    return json.loads(cleaned)


def _encode_change_id(change_id: str) -> str:

    if "~" in change_id:
        parts = change_id.split("~")
        return "%7E".join(quote(p, safe="") for p in parts)
    return quote(change_id, safe="")


def _resolve_to_number(change_id: str, base_url: str) -> str:

    if re.fullmatch(r"I[0-9a-fA-F]{5,}", change_id):
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
    return change_id




def list_patchsets(change_id: str, base_url: str = DEFAULT_BASE) -> list[dict]:

    resolved = _resolve_to_number(change_id.strip(), base_url)
    encoded  = _encode_change_id(resolved)
    url      = f"{base_url}/changes/{encoded}/detail?o=ALL_REVISIONS&o=ALL_COMMITS"

    try:
        data = _parse_gerrit(_get(url).text)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise ValueError(
            f"Gerrit returned HTTP {status} for change '{change_id}'.\n"
            f"• 404 → change not found or not visible anonymously on {base_url}\n"
            f"• 401/403 → authentication required\n"
            f"Tried URL: {url}"
        ) from exc

    revisions = data.get("revisions", {})
    if not revisions:
        raise ValueError(
            f"Change '{change_id}' has no revisions. "
            "It may be abandoned or the response is malformed."
        )

    patchsets = []
    for commit_sha, rev in revisions.items():
        commit_info = rev.get("commit", {})
        patchsets.append({
            "patchset": rev["_number"],
            "sha":      commit_sha,                              
            "message":  commit_info.get("message", "").strip(),
        })

    return sorted(patchsets, key=lambda p: p["patchset"])


def get_patchset_commit(
    change_id: str,
    patchset_or_dict,
    base_url: str = DEFAULT_BASE,
) -> dict:
  
  
    if isinstance(patchset_or_dict, dict):
        return {
            "message": patchset_or_dict.get("message", "").strip(),
            "sha":     patchset_or_dict.get("sha", ""),
        }

    patchset = int(patchset_or_dict)
    resolved = _resolve_to_number(change_id.strip(), base_url)
    encoded  = _encode_change_id(resolved)

    detail_url = f"{base_url}/changes/{encoded}/detail?o=ALL_REVISIONS&o=ALL_COMMITS"
    try:
        data = _parse_gerrit(_get(detail_url).text)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise ValueError(
            f"Could not fetch detail for change '{change_id}' (HTTP {status})."
        ) from exc

    for commit_sha, rev in data.get("revisions", {}).items():
        if rev["_number"] == patchset:
            commit_info = rev.get("commit", {})
            return {
                "message": commit_info.get("message", "").strip(),
                "sha":     commit_sha,
            }

    raise ValueError(f"Patchset {patchset} not found in change '{change_id}'.")


def get_patch_diff(
    change_id: str,
    patchset_or_dict,
    base_url: str = DEFAULT_BASE,
) -> str:

    if isinstance(patchset_or_dict, dict):
        sha = patchset_or_dict.get("sha", "")
        if not sha:
            raise ValueError("Patchset dict has no 'sha' key.")
    else:
        commit = get_patchset_commit(change_id, int(patchset_or_dict), base_url)
        sha = commit["sha"]

    resolved = _resolve_to_number(change_id.strip(), base_url)
    encoded  = _encode_change_id(resolved)

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
        return base64.b64decode(raw).decode("utf-8", errors="replace")
    except Exception:
        return raw
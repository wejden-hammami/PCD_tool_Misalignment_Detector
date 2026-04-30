import re
import pandas as pd
from datetime import datetime



_BOT_NAMES = {
    "bot", "github-actions", "ci", "dependabot", "coderabbitai", "copilot",
    "claassistant", "drahtbot", "drahbot", "acts-project-service",
    "codecov-commenter", "coveralls", "istio-policy-bot", "lightdash-bot",
    "metamaskbot", "modularbot", "nf-core-bot", "pulumi-bot",
    "pytorchmergebot", "raycastbot", "scrutinizer-notifier", "slangbot",
    "strapi-cla", "wolfssl-bot", "owidbot", "zwave-js-bot", "pyvista-bot",
    "robobun", "autogpt-agent", "parseplatformorg", "istio-testing",
    "msftgits", "platform-cane891", "vs-mobiletools-engineering-service2",
    "opgitgovernance", "zuul", "jenkins", "automation", "openstack-gerrit",
    "infra-root", "release", "propose", "sync", "recheck",
    "cinder-jenkins", "nova-jenkins", "neutron-jenkins", "check", "gate",
}


def is_human(actor: str) -> bool:
    if not actor:
        return False
    lower = actor.lower()
    if lower in _BOT_NAMES:
        return False
    if lower.endswith("[bot]"):
        return False
    if "bot" in lower:
        return False
    if lower.endswith("-ci"):
        return False
    return True



_PATTERN = re.compile(
    r'\[([^\]]+)\]\s+([^—]+?)\s+—\s+(\w+):\s+(.*?)(?=\[|$)',
    re.DOTALL,
)


def parse_timeline(timeline_str: str) -> list[dict]:
    if not isinstance(timeline_str, str):
        return []

    events = []
    for m in _PATTERN.finditer(timeline_str):
        ts_str, actor, event_type, message = m.groups()
        actor = actor.strip()

        if event_type.strip().lower() != "commented":
            continue
        if not is_human(actor):
            continue

        try:
            ts = datetime.fromisoformat(ts_str.strip())
        except Exception:
            ts = None

        events.append({
            "timestamp":     ts,
            "timestamp_str": ts_str.strip(),
            "actor":         actor,
            "event_type":    event_type.strip(),
            "message":       message.strip(),
        })

    return events




def build_df(enriched: list[dict]) -> pd.DataFrame:
    rows = [
        {
            "repo":             c.get("repo", ""),
            "pr_number":        c.get("pr_number", ""),
            "actor":            c.get("actor", ""),
            "timestamp":        c.get("timestamp"),
            "timestamp_str":    c.get("timestamp_str", ""),
            "message":          c.get("message", ""),
            "confused":         bool(c.get("confused", False)),
            "confusion_reason": c.get("confusion_reason", ""),
            "change_predicted": bool(c.get("change_predicted", False)),
            "change_reason":    c.get("change_reason", ""),
        }
        for c in enriched
    ]
    return pd.DataFrame(rows)


def build_commit_df(commits: list[dict]) -> pd.DataFrame:

    rows = [
        {
            "sha":               c.get("sha", c.get("patchset", "")),
            "message":           c.get("message", ""),
            "score":             float(c.get("score", 0.0)),
            "status":            c.get("status", "ALIGNED"),
            "issue":             c.get("issue", ""),
            "suggested_message": c.get("suggested_message", ""),
        }
        for c in commits
    ]
    return pd.DataFrame(rows)
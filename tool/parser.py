import re
from datetime import datetime

import pandas as pd

_BOT_NAMES = frozenset({
    "acts-project-service", "autogpt-agent", "automation", "bot",
    "check", "cinder-jenkins", "ci", "claassistant", "codecov-commenter",
    "copilot", "coveralls", "dependabot", "drahtbot", "drahbot",
    "gate", "github-actions", "infra-root", "istio-policy-bot",
    "istio-testing", "jenkins", "lightdash-bot", "metamaskbot", "modularbot",
    "msftgits", "neutron-jenkins", "nf-core-bot", "nova-jenkins",
    "openstack-gerrit", "opgitgovernance", "owidbot", "parseplatformorg",
    "platform-cane891", "propose", "pulumi-bot", "pytorchmergebot",
    "raycastbot", "recheck", "release", "robobun", "scrutinizer-notifier",
    "slangbot", "strapi-cla", "sync", "vs-mobiletools-engineering-service2",
    "wolfssl-bot", "wolfssl-bot", "wolfssl-bot",
    "zuul", "zwave-js-bot", "pyvista-bot",
})

_TIMELINE_RE = re.compile(
    r'\[([^\]]+)\]\s+([^—]+?)\s+—\s+(\w+):\s+(.*?)(?=\[|$)',
    re.DOTALL,
)


def is_human(actor: str) -> bool:
    if not actor:
        return False
    lower = actor.lower()
    return not (
        lower in _BOT_NAMES
        or lower.endswith("[bot]")
        or lower.endswith("-ci")
        or "bot" in lower
    )


def parse_timeline(timeline_str: str) -> list[dict]:
    if not isinstance(timeline_str, str):
        return []

    events = []
    for m in _TIMELINE_RE.finditer(timeline_str):
        ts_str, actor, event_type, message = m.groups()
        actor = actor.strip()

        if event_type.strip().lower() != "commented" or not is_human(actor):
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
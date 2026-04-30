import requests
from datetime import datetime

BASE = "https://api.github.com"




def _get(path: str, token: str = "", params: dict = None) -> requests.Response:
    headers = {
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return requests.get(
        BASE + path,
        headers=headers,
        params=params or {},
        timeout=15,
    )


def _ok(r: requests.Response) -> bool:
    return r.status_code == 200




def check_token(token: str) -> tuple[bool, str]:
    r = _get("/user", token)
    if r.status_code == 200:
        return True, r.json().get("login", "unknown")
    if r.status_code == 401:
        return False, "Invalid or expired token"
    return False, f"GitHub error {r.status_code}"




def list_repos(token: str) -> list[str]:
    repos = []
    for page in range(1, 4):
        r = _get("/user/repos", token, {"per_page": 100, "page": page, "sort": "updated"})
        if not _ok(r):
            break
        data = r.json()
        if not data:
            break
        repos += [repo["full_name"] for repo in data]
    return repos




def get_repo(token: str, full_repo: str) -> tuple[bool, str]:
    r = _get(f"/repos/{full_repo}", token)
    if r.status_code == 200:
        return True, ""
    if r.status_code == 404:
        return False, f"Repository '{full_repo}' not found"
    if r.status_code == 403:
        return False, "Access denied — add a token with repo scope"
    return False, f"GitHub error {r.status_code}"



def list_open_prs(token: str, full_repo: str) -> list[dict]:
    r = _get(f"/repos/{full_repo}/pulls", token, {"state": "open", "per_page": 100})

    if r.status_code == 404:
        raise RuntimeError(f"Repository '{full_repo}' not found.")
    if r.status_code == 403:
        raise RuntimeError("Access denied. Add a GitHub token for private repos.")
    if not _ok(r):
        raise RuntimeError(f"GitHub returned HTTP {r.status_code}: {r.text[:200]}")

    return [{"number": pr["number"], "title": pr["title"]} for pr in r.json()]




def list_pr_commits(token: str, repo: str, pr_number: int) -> list[dict]:

    commits = []
    for page in range(1, 6):         
        r = _get(
            f"/repos/{repo}/pulls/{pr_number}/commits",
            token,
            {"per_page": 100, "page": page},
        )
        if not _ok(r):
            break
        batch = r.json()
        if not batch:
            break
        for c in batch:
            commits.append({
                "sha":     c["sha"],
                "message": c["commit"]["message"].strip(),
            })

    if not commits:
        raise RuntimeError(
            f"No commits returned for PR #{pr_number} in {repo}. "
            "Check the PR number and token permissions."
        )
    return commits



def get_commit_diff(token: str, repo: str, sha: str) -> str:

    r = _get(f"/repos/{repo}/commits/{sha}", token)

    if not _ok(r):
        raise RuntimeError(f"Could not fetch commit {sha[:7]}: HTTP {r.status_code}")

    files = r.json().get("files", [])
    if not files:
        return ""

    return "\n".join(f.get("patch", "") or "" for f in files)




def fetch_new_comments(token, full_repo, pr_number, since=None):
    params = {"per_page": 100}
    if since:
        params["since"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    comments = []
    r1 = _get(f"/repos/{full_repo}/issues/{pr_number}/comments", token, params)
    r2 = _get(f"/repos/{full_repo}/pulls/{pr_number}/comments",  token, params)

    if _ok(r1):
        for c in r1.json():
            comments.append(_normalize(c, full_repo, pr_number))
    if _ok(r2):
        for c in r2.json():
            comments.append(_normalize(c, full_repo, pr_number))

    comments.sort(key=lambda x: x["timestamp_str"])
    return comments


def _normalize(raw, repo, pr):
    user = raw.get("user") or {}
    return {
        "repo":          repo,
        "pr_number":     pr,
        "comment_id":    raw["id"],
        "actor":         user.get("login", "unknown"),
        "message":       raw.get("body", ""),
        "timestamp_str": raw["created_at"],
        "timestamp":     datetime.fromisoformat(raw["created_at"].replace("Z", "+00:00")),
    }
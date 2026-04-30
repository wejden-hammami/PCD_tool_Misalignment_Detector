import html
import streamlit as st
import pandas as pd

from styles import CSS
from ollama_client import check_ollama, analyze_commit_mismatch, MODEL
from charts import (
    commit_similarity_distribution,
    commit_quality_pie,
    commit_trend,
    commit_alignment_distribution,
)
from parser import build_commit_df
from github_client import (
    check_token,
    list_open_prs,
    list_pr_commits,
    get_commit_diff,
)
from gerrit_client import list_patchsets, get_patch_diff, get_patchset_commit
from codet5_similarity import compute_similarity
from feedback import init_db, save_feedback

st.set_page_config(
    page_title="Misalignment Detector",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={},
)
st.markdown(CSS, unsafe_allow_html=True)

init_db()

THRESHOLD = 0.3



def render_commit_card(item: dict, source: str = "github"):
    score  = item.get("score", 0.0)
    status = item.get("status", "ALIGNED")
    sha    = item.get("sha") or f"PS-{item.get('patchset', '?')}"
    msg    = html.escape(item.get("message", ""))
    issue  = html.escape(item.get("issue", ""))
    sugg   = html.escape(item.get("suggested_message", ""))
    diff   = item.get("diff", "")

    if status == "MISALIGNED":
        card_cls  = "commit-card commit-score-low"
        score_cls = "card-score score-low"
        badge     = '<span class="badge badge-confused">MISALIGNED</span>'
    elif status == "ERROR":
        card_cls  = "commit-card commit-score-error"
        score_cls = "card-score score-error"
        badge     = '<span class="badge badge-error">FETCH ERROR</span>'
    else:
        card_cls  = "commit-card commit-score-ok"
        score_cls = "card-score score-ok"
        badge     = '<span class="badge badge-clear">ALIGNED</span>'

    issue_block = f'<div class="card-issue">! {issue}</div>' if issue else ""
    sugg_block  = (
        f'<div class="card-suggestion">Suggested: {sugg}</div>'
        if sugg and status == "MISALIGNED" else ""
    )

    sha_display = sha[:7] if len(sha) > 7 else sha

    st.markdown(f"""
<div class="{card_cls}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <code class="card-sha">{sha_display}</code>
    <span class="{score_cls}">score: {score:.3f}</span>
  </div>
  <div style="margin-bottom:6px">{badge}</div>
  <div class="card-message">{msg}</div>
  {issue_block}
  {sugg_block}
</div>""", unsafe_allow_html=True)

    if diff:
        with st.expander("View diff", expanded=(status == "MISALIGNED")):
            lines    = diff.splitlines()
            coloured = []
            for line in lines:
                escaped = html.escape(line)
                if line.startswith("+") and not line.startswith("+++"):
                    coloured.append(f'<span class="diff-added">{escaped}</span>')
                elif line.startswith("-") and not line.startswith("---"):
                    coloured.append(f'<span class="diff-removed">{escaped}</span>')
                elif line.startswith("@@"):
                    coloured.append(f'<span class="diff-hunk">{escaped}</span>')
                else:
                    coloured.append(f'<span class="diff-neutral">{escaped}</span>')

            st.markdown(
                '<pre class="diff-block">' + "\n".join(coloured) + "</pre>",
                unsafe_allow_html=True,
            )


def render_kpis(rows: list[dict]):
    total      = len(rows)
    misaligned = sum(1 for r in rows if r.get("status") == "MISALIGNED")
    errors     = sum(1 for r in rows if r.get("status") == "ERROR")
    aligned    = total - misaligned - errors
    avg_score  = (
        f"{sum(r.get('score', 0) for r in rows if r.get('status') != 'ERROR') / max(total - errors, 1):.3f}"
        if total else "-"
    )

    cols = st.columns(5)
    for col, val, lbl, clr in [
        (cols[0], total,      "Commits",      "#4f46e5"),
        (cols[1], aligned,    "Aligned",      "#16a34a"),
        (cols[2], misaligned, "Misaligned",   "#ef4444"),
        (cols[3], errors,     "Fetch Errors", "#9ca3af"),
        (cols[4], avg_score,  "Avg Score",    "#f59e0b"),
    ]:
        col.markdown(f"""
<div class="metric-box">
  <div class="metric-number" style="color:{clr}">{val}</div>
  <div class="metric-label">{lbl}</div>
</div>""", unsafe_allow_html=True)


def render_charts(df: pd.DataFrame):
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(commit_alignment_distribution(df), use_container_width=True)
    with c2:
        st.plotly_chart(commit_quality_pie(df), use_container_width=True)
    st.plotly_chart(commit_similarity_distribution(df), use_container_width=True)
    st.plotly_chart(commit_trend(df), use_container_width=True)


def analyze_commits(raw_commits: list[dict], repo_name: str, run_key: str):

    if run_key in st.session_state:
        return st.session_state[run_key]

    results  = []
    token    = st.session_state.get("gh_token", "")
    progress = st.progress(0, text="Starting analysis...")

    for i, commit in enumerate(raw_commits):
        progress.progress(
            int(i / len(raw_commits) * 100),
            text=f"Analyzing {i+1}/{len(raw_commits)} — {commit.get('sha', commit.get('patchset', ''))[:7]}...",
        )
        try:
            if "patchset" in commit:
                diff = get_patch_diff(repo_name, commit)
            else:
                diff = get_commit_diff(token, repo_name, commit["sha"])

            message = commit.get("message", "")
            score   = compute_similarity(message, diff)
            status  = "MISALIGNED" if score < THRESHOLD else "ALIGNED"

            issue     = ""
            suggested = ""
            if status == "MISALIGNED":
                llm_result = analyze_commit_mismatch(message, diff)
                issue      = llm_result.get("issue", "")
                suggested  = llm_result.get("suggested_message", message)

            results.append({
                **commit,
                "diff":              diff,
                "score":             score,
                "status":            status,
                "issue":             issue,
                "suggested_message": suggested,
            })

        except Exception as e:
            st.warning(f"Skipped {str(commit.get('sha', commit.get('patchset', '?')))[:7]}: {e}")
            results.append({
                **commit,
                "score": 0.0, "status": "ERROR",
                "issue": str(e), "suggested_message": "",
            })

    progress.progress(100, text="Done")
    st.session_state[run_key] = results
    return results


if "mode" not in st.session_state:
    st.session_state["mode"] = "GitHub"

with st.sidebar:
    st.markdown("## Ollama")
    ollama_ok, ollama_msg = check_ollama()
    st.markdown(
        f'<p class="{"status-ok" if ollama_ok else "status-err"}">'
        f'{"+" if ollama_ok else "x"} {ollama_msg}'
        + (f" — <strong>{MODEL}</strong>" if ollama_ok else "") + "</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    if st.session_state["mode"] == "GitHub":
        st.markdown("## GitHub Access")
        st.text_input(
            "Personal Access Token",
            type="password",
            placeholder="github_pat_...",
            key="gh_token",
            help="Required — GitHub's API needs a token to list pull requests and fetch diffs.",
        )
        token_val = st.session_state.get("gh_token", "")
        if token_val:
            ok, msg = check_token(token_val)
            if ok:
                st.markdown(f'<p class="status-ok">+ Authenticated as <strong>{msg}</strong></p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p class="status-err">x {msg}</p>', unsafe_allow_html=True)
        else:
            st.warning("A token is required to use the GitHub tab.")
        st.divider()

    st.markdown("## Settings")
    THRESHOLD = st.slider(
        "Misalignment threshold",
        min_value=0.0, max_value=1.0, value=THRESHOLD, step=0.05,
        help="Commits with similarity score below this are flagged as MISALIGNED",
    )


st.markdown("# Misalignment Detector")
st.markdown(
    "<p style='color:#6b7280;font-size:14px;margin-top:-10px'>"
    "Commit message vs code diff alignment "
    "</p>",
    unsafe_allow_html=True,
)

if not ollama_ok:
    st.warning(f"Ollama not ready: {ollama_msg} — LLM explanations will be skipped.")


[tab_main] = st.tabs(["Misalignment Detector"])

with tab_main:

    mode = st.radio(
        "Source", ["GitHub", "Gerrit"], horizontal=True,
        key="mode",
    )

    if mode == "GitHub":
        token = st.session_state.get("gh_token", "")

        if not token:
            st.error(
                "A GitHub Personal Access Token is required to use this tab. "
                "Please add one in the sidebar."
            )
            st.stop()

        repo = st.text_input("Repository (owner/repo)", placeholder="e.g. django/django", key="gh_repo")

        if repo and "/" in repo:
            pr_cache = f"prs_{repo}"
            if pr_cache not in st.session_state:
                with st.spinner("Loading open PRs..."):
                    st.session_state[pr_cache] = list_open_prs(token, repo)

            prs = st.session_state[pr_cache]

            if not prs:
                st.info("No open PRs found for this repo, or the token does not have access to it.")
            else:
                pr_map   = {f"#{p['number']} - {p['title']}": p["number"] for p in prs}
                pr_label = st.selectbox("Pull Request", list(pr_map.keys()), key="gh_pr_select")
                pr_num   = pr_map[pr_label]
                run_key  = f"results_{repo}_PR{pr_num}"

                if st.session_state.get("_last_run") != run_key:
                    st.session_state.pop(run_key, None)
                    st.session_state["_last_run"] = run_key

                if st.button("Analyze Commits", type="primary", use_container_width=True, key="gh_run"):
                    st.session_state.pop(run_key, None)

                with st.spinner("Fetching commits..."):
                    raw_commits = list_pr_commits(token, repo, int(pr_num))

                if not raw_commits:
                    st.warning("No commits found for this PR.")
                else:
                    st.caption(f"Found {len(raw_commits)} commits ")
                    results = analyze_commits(raw_commits, repo, run_key)

                    st.markdown("---")
                    st.markdown("### Overview")
                    render_kpis(results)

                    df = build_commit_df(results)
                    if not df.empty:
                        st.markdown("---")
                        st.markdown("### Visualizations")
                        render_charts(df)

                    st.markdown("---")
                    st.markdown(
                        f"### Commits "
                        f"<span style='font-size:14px;color:#6b7280'>({len(results)} total)</span>",
                        unsafe_allow_html=True,
                    )
                    for item in results:
                        render_commit_card(item, source="github")
                        col_a, col_b, _ = st.columns([1, 1, 6])
                        with col_a:
                            if st.button("👍Correct", key=f"ok_{item.get('sha', '')}"):
                                save_feedback(repo, "commit", item.get("message", ""), item.get("score", 0), 1)
                                st.toast("Feedback saved")
                        with col_b:
                            if st.button("👎Wrong", key=f"bad_{item.get('sha', '')}"):
                                save_feedback(repo, "commit", item.get("message", ""), item.get("score", 0), 0)
                                st.toast("Feedback saved")

                    with st.expander("Raw data table"):
                        st.dataframe(df, use_container_width=True)

        elif repo:
            st.caption("Enter repo as owner/repo, e.g. torvalds/linux")

    elif mode == "Gerrit":
        change = st.text_input("Change ID", placeholder="e.g. 933890 or I1234abcd...", key="gerrit_change")

        if change:
            run_key = f"results_gerrit_{change}"

            if st.button("Analyze Patchsets", type="primary", use_container_width=True, key="gerrit_run"):
                st.session_state.pop(run_key, None)

            try:
                with st.spinner("Fetching patchsets..."):
                    raw_commits = list_patchsets(change)

                if not raw_commits:
                    st.warning("No patchsets found for this change ID.")
                else:
                    st.caption(f"Found {len(raw_commits)} patchsets ")
                    results = analyze_commits(raw_commits, change, run_key)

                    st.markdown("---")
                    st.markdown("### Overview")
                    render_kpis(results)

                    df = build_commit_df(results)
                    if not df.empty:
                        st.markdown("---")
                        st.markdown("### Visualizations")
                        render_charts(df)

                    st.markdown("---")
                    st.markdown(
                        f"### Patchsets "
                        f"<span style='font-size:14px;color:#6b7280'>({len(results)} total)</span>",
                        unsafe_allow_html=True,
                    )
                    for item in results:
                        render_commit_card(item, source="gerrit")

                    with st.expander("Raw data table"):
                        st.dataframe(df, use_container_width=True)

            except Exception as e:
                st.error(f"Gerrit error: {e}")
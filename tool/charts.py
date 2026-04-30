import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e6edf3",
    title_font_family="JetBrains Mono",
    xaxis=dict(gridcolor="#21262d"),
    yaxis=dict(gridcolor="#21262d"),
    margin=dict(l=20, r=20, t=40, b=20),
)




def commit_alignment_distribution(df: pd.DataFrame):

    if df.empty or "status" not in df.columns:
        return _empty("No data")

    counts = df["status"].value_counts().reset_index()
    counts.columns = ["status", "count"]

    fig = px.bar(
        counts,
        x="status",
        y="count",
        color="status",
        title="Commit Alignment Distribution",
        color_discrete_map={
            "ALIGNED":    "#3fb950",
            "MISALIGNED": "#f85149",
            "ERROR":      "#8b949e",
        },
        text="count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(**_LAYOUT)
    return fig


def commit_similarity_distribution(df: pd.DataFrame):

    if df.empty or "score" not in df.columns:
        return _empty("No score data")

    fig = px.histogram(
        df,
        x="score",
        nbins=20,
        title="Similarity Score Distribution",
        color_discrete_sequence=["#58a6ff"],
    )
    
    fig.add_vline(x=0.3, line_dash="dash", line_color="#f85149",
                  annotation_text="threshold (0.3)", annotation_position="top right")
    fig.update_layout(**_LAYOUT)
    return fig


def commit_quality_pie(df: pd.DataFrame):

    if df.empty or "status" not in df.columns:
        return _empty("No data")

    good   = len(df[df["status"] == "ALIGNED"])
    bad    = len(df[df["status"] == "MISALIGNED"])
    errors = len(df[df["status"] == "ERROR"])

    labels = ["Aligned", "Misaligned", "Fetch Error"]
    values = [good, bad, errors]
    colors = ["#3fb950", "#f85149", "#8b949e"]

    filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    if not filtered:
        return _empty("No data")
    labels, values, colors = zip(*filtered)

    fig = go.Figure(data=[go.Pie(
        labels=list(labels),
        values=list(values),
        hole=0.55,
        marker_colors=list(colors),
    )])
    fig.update_layout(title="Commit Quality Overview", **_LAYOUT)
    return fig


def commit_trend(df: pd.DataFrame):

    if df.empty or "score" not in df.columns:
        return _empty("No trend data")

    df = df.reset_index(drop=True).copy()
    df["index"] = range(len(df))
    df["label"] = df.get("sha", df.index.astype(str)).apply(
        lambda x: x[:7] if isinstance(x, str) and len(x) > 7 else str(x)
    )

    fig = px.line(
        df,
        x="index",
        y="score",
        hover_data=["label"] if "label" in df.columns else None,
        title="Alignment Trend Across Commits",
        markers=True,
        color_discrete_sequence=["#58a6ff"],
    )
    fig.add_hline(y=0.3, line_dash="dash", line_color="#f85149",
                  annotation_text="threshold", annotation_position="bottom right")
    fig.update_layout(**_LAYOUT)
    return fig



def signals_by_repo_pr(df: pd.DataFrame):
    if df.empty:
        return _empty("No data")

    rd = df.groupby(["repo", "pr_number"]).agg(
        total=("message", "count"),
        confused=("confused", "sum"),
        change=("change_predicted", "sum"),
    ).reset_index()
    rd["not_confused"] = rd["total"] - rd["confused"]
    rd["label"] = rd["repo"] + " #" + rd["pr_number"].astype(str)

    fig = go.Figure([
        go.Bar(x=rd["label"], y=rd["not_confused"], name="not confused", marker_color="#3fb950"),
        go.Bar(x=rd["label"], y=rd["confused"],     name="confused",     marker_color="#f85149"),
        go.Bar(x=rd["label"], y=rd["change"],       name="change",       marker_color="#f59e0b"),
    ])
    fig.update_layout(barmode="stack", title="Signals by Repo + PR", **_LAYOUT)
    return fig


def confused_actors(df: pd.DataFrame):
    if df.empty:
        return _empty("No data")

    df = df.copy()
    df["confused"] = df["confused"].astype(int)
    ad = df.groupby("actor").agg(
        total=("message", "count"),
        confused=("confused", "sum"),
    ).reset_index()
    ad["conf_pct"] = (ad["confused"] / ad["total"].replace(0, 1) * 100).round(1)
    ad = ad.sort_values("conf_pct").tail(10)

    fig = px.bar(ad, x="conf_pct", y="actor", orientation="h",
                 title="Most Confused Actors (%)", range_x=[0, 100])
    fig.update_layout(**_LAYOUT)
    return fig


def activity_over_time(df: pd.DataFrame):
    df_ts = df[df["timestamp"].notna()].copy()
    if df_ts.empty:
        return None

    df_ts["date"] = pd.to_datetime(df_ts["timestamp"]).dt.date
    tl = df_ts.groupby(["date", "confused"]).size().reset_index(name="count")
    tl["type"] = tl["confused"].map({True: "confused", False: "not_confused"})

    fig = px.bar(tl, x="date", y="count", color="type",
                 barmode="stack", title="Activity Over Time")
    fig.update_layout(**_LAYOUT)
    return fig




def _empty(msg: str):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False,
                       font=dict(color="#8b949e", size=14))
    fig.update_layout(**_LAYOUT)
    return fig
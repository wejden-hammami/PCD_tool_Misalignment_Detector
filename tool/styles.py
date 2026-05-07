CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

/* ───────────────────────────────
   BASE
─────────────────────────────── */

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: #f7f7fb;
    color: #111827;
}

h1, h2, h3 {
    font-family: 'Inter', sans-serif;
    color: #111827;
}

/* ───────────────────────────────
   CLEAN STREAMLIT
─────────────────────────────── */

#MainMenu,
footer,
header,
[data-testid="stToolbar"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"] {
    display: none !important;
}

/* ───────────────────────────────
   COMMIT CARDS
─────────────────────────────── */

.commit-card {
    background:    #ffffff;
    border:        1px solid #e5e7eb;
    border-left:   5px solid #8b5cf6;
    border-radius: 12px;
    padding:       14px 16px;
    margin:        8px 0;
    font-family:   'JetBrains Mono', monospace;
    font-size:     13px;
    color:         #111827;
    box-shadow:    0 2px 6px rgba(0,0,0,0.06);
    transition:    transform 0.15s ease, box-shadow 0.15s ease;
}

.commit-card:hover {
    transform:  translateY(-1px);
    box-shadow: 0 8px 20px rgba(139,92,246,0.15);
}

.commit-score-low {
    border-left-color: #ef4444;
    background:        #fff5f5;
}

.commit-score-ok {
    border-left-color: #8b5cf6;
    background:        #f5f3ff;
}

.commit-score-error {
    border-left-color: #9ca3af;
    background:        #f3f4f6;
    opacity: 0.85;
}

.commit-card .card-sha {
    color:     #4f46e5;
    font-size: 12px;
}

.commit-card .card-score {
    font-family: 'JetBrains Mono', monospace;
    font-size:   12px;
}

.commit-card .card-score.score-low   { color: #ef4444; }
.commit-card .card-score.score-ok    { color: #16a34a; }
.commit-card .card-score.score-error { color: #9ca3af; }

.commit-card .card-message {
    font-size:   13px;
    color:       #111827;
    line-height: 1.5;
    white-space: pre-wrap;
    margin-top:  6px;
}

.commit-card .card-issue {
    color:      #ef4444;
    font-size:  12px;
    margin-top: 8px;
}

.commit-card .card-suggestion {
    color:      #4f46e5;
    font-size:  12px;
    margin-top: 4px;
}

/* ───────────────────────────────
   DIFF VIEWER
─────────────────────────────── */

.diff-block {
    background:    #f8fafc;
    border:        1px solid #e2e8f0;
    border-radius: 6px;
    padding:       12px;
    font-size:     12px;
    line-height:   1.5;
    overflow-x:    auto;
    font-family:   'JetBrains Mono', monospace;
    white-space:   pre;
}

.diff-added   { color: #16a34a; }
.diff-removed { color: #dc2626; }
.diff-hunk    { color: #2563eb; }
.diff-neutral { color: #6b7280; }

/* ───────────────────────────────
   COMMENT CARDS
─────────────────────────────── */

.comment-card {
    background:    #ffffff;
    border:        1px solid #e5e7eb;
    border-radius: 12px;
    padding:       14px 16px;
    margin:        8px 0;
    color:         #111827;
}

.comment-card.confused { border-left: 4px solid #ef4444; background: #fff5f5; }
.comment-card.change   { border-left: 4px solid #f59e0b; background: #fffbeb; }
.comment-card.both     { border-left: 4px solid #8b5cf6; background: #f5f3ff; }

/* ───────────────────────────────
   ALERTS
─────────────────────────────── */

.confusion-alert {
    background:    #fff5f5;
    border-left:   4px solid #ef4444;
    padding:       12px;
    border-radius: 10px;
    color:         #111827;
}

.change-alert {
    background:    #fffbeb;
    border-left:   4px solid #f59e0b;
    padding:       12px;
    border-radius: 10px;
    color:         #111827;
}

/* ───────────────────────────────
   BADGES
─────────────────────────────── */

.badge {
    padding:       3px 10px;
    border-radius: 999px;
    font-size:     11px;
    font-weight:   500;
    display:       inline-block;
}

.badge-confused { background: #fee2e2; color: #991b1b; }
.badge-clear    { background: #dcfce7; color: #166534; }
.badge-change   { background: #fef3c7; color: #92400e; }
.badge-nochange { background: #e5e7eb; color: #374151; }
.badge-error    { background: #e5e7eb; color: #374151; }

/* ───────────────────────────────
   METRICS
─────────────────────────────── */

.metric-box {
    background:    #ffffff;
    border:        1px solid #e5e7eb;
    border-radius: 12px;
    padding:       16px;
    text-align:    center;
}

.metric-number {
    font-size:   1.8rem;
    font-weight: 600;
}

.metric-label {
    font-size: 11px;
    color:     #6b7280;
}

/* ───────────────────────────────
   STATUS TEXT (sidebar)
─────────────────────────────── */

.status-ok {
    color:       #16a34a;
    font-family: 'JetBrains Mono', monospace;
}

.status-err {
    color:       #ef4444;
    font-family: 'JetBrains Mono', monospace;
}

</style>
"""
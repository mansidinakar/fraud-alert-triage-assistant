import html
import os
import re

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
HEADERS = {"X-API-Key": os.getenv("API_TOKEN", "")}
LABELS = {
    "escalate": "Escalate",
    "request_info": "Request more info",
    "close_false_positive": "Close as false positive",
}
CITE_RE = re.compile(r"\[([A-Za-z0-9_.]+)\]")

st.set_page_config(page_title="Fraud Alert Triage", layout="wide")
st.markdown(
    """
<style>
.badge{display:inline-block;padding:2px 12px;border-radius:999px;font-size:.85rem;font-weight:600;vertical-align:middle}
.b-escalate{background:#4A1D1D;color:#FF9B9B}
.b-request_info{background:#4A3A12;color:#FFD27A}
.b-close_false_positive{background:#123B27;color:#7FE0A8}
.b-unknown{background:#2A2F3A;color:#B8C0CC}
.card{background:#1A1D26;border:1px solid #2A2F3A;border-radius:10px;padding:12px 16px;margin-bottom:12px;line-height:1.55;overflow-wrap:anywhere}
.card h4{margin:0 0 6px 0;font-size:.9rem;color:#9DBBFF;font-weight:600}
.kv{display:flex;justify-content:space-between;gap:12px;padding:3px 0;border-bottom:1px solid #2A2F3A;font-size:.85rem}
.kv:last-child{border-bottom:none}
.kv span:first-child{color:#8B95A5;font-family:monospace;font-size:.78rem;min-width:0;word-break:break-all}
.kv span:last-child{text-align:right;font-weight:500;flex-shrink:0;color:#E6E8EE}
.kv.cited{background:#1B2438;box-shadow:inset 3px 0 0 #4C8DFF;padding-left:8px;border-radius:4px}
.kv.cited span:first-child{color:#B8CCFF}
.kv span.miss{color:#FFD27A;font-style:italic;font-weight:500}
.cite{background:#1F2F5C;color:#9DBBFF;border-radius:4px;padding:0 5px;font-size:.72rem;font-family:monospace;overflow-wrap:anywhere}
.fact{background:#1A1D26;border:1px solid #2A2F3A;border-radius:10px;padding:10px 14px}
.fact .l{font-size:.75rem;color:#8B95A5}
.fact .v{font-size:1.1rem;font-weight:600;color:#F2F4F8}
.muted{color:#8B95A5}
ul.tight{margin:0;padding-left:1.1rem}
ul.tight li{margin-bottom:.45rem;line-height:1.5;overflow-wrap:anywhere}
/* tight page */
.block-container,[data-testid="stMainBlockContainer"]{padding-top:3rem !important;padding-bottom:2rem !important}
.block-container h2,[data-testid="stMainBlockContainer"] h2{padding-top:0 !important;margin-top:0 !important}
[data-testid="stSidebarHeader"]{min-height:0;padding-bottom:0}
</style>
""",
    unsafe_allow_html=True,
)


def api_get(path, **params):
    r = requests.get(API_URL + path, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def as_text(x):
    if isinstance(x, dict):
        return " ".join(str(v) for v in x.values())
    return str(x)


def rich(text):
    """Escape first, then turn [dotted.path] citations into small chips."""
    clean = " ".join(as_text(text).split())
    return CITE_RE.sub(r'<span class="cite">\1</span>', html.escape(clean))


def bullets(items):
    if not items:
        return '<p class="muted">None listed.</p>'
    return '<ul class="tight">' + "".join(f"<li>{rich(i)}</li>" for i in items) + "</ul>"


def fmt(v, missing="none"):
    if v is None:
        return missing
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


CITED = set()


def kv_card(title, pairs, missing="none"):
    rows_html = []
    for k, v in pairs:
        cls = "kv cited" if k in CITED else "kv"
        vcls = ' class="miss"' if v is None else ""
        rows_html.append(
            f'<div class="{cls}"><span>{html.escape(str(k))}</span>'
            f'<span{vcls}>{html.escape(fmt(v, missing))}</span></div>'
        )
    st.markdown(
        f'<div class="card"><h4>{html.escape(title)}</h4>{"".join(rows_html)}</div>',
        unsafe_allow_html=True,
    )


def badge(sug):
    key = sug if sug in LABELS else "unknown"
    return f'<span class="badge b-{key}">{html.escape(LABELS.get(sug, "No suggestion"))}</span>'


def fact(col, label, value):
    col.markdown(
        f'<div class="fact"><div class="l">{html.escape(label)}</div>'
        f'<div class="v">{html.escape(value)}</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("## Fraud Alert Triage")
st.caption(
    "Summaries are AI-generated. Check each claim against the evidence on the right; "
    "history labels and counts are the known weak spots. You make the final call."
)
if st.session_state.pop("flash", False):
    st.success("Decision saved and logged.")

analyst = st.sidebar.text_input("Analyst ID", value="analyst_1", max_chars=40)
valid_analyst = bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", analyst))
if not valid_analyst:
    st.sidebar.error("Use letters, numbers, dot, dash or underscore only.")

try:
    q = api_get("/queue", limit=50)
except requests.RequestException:
    st.error("Cannot reach the triage API. Start it with: python3 -m uvicorn src.api:app --port 8000")
    st.stop()

st.sidebar.metric("Pending alerts", q["pending"])
if not q["items"]:
    st.success("Queue is empty.")
    st.stop()

options = {
    f"{i['alert_id']} · risk {i['risk_score']:.2f} · "
    f"{LABELS.get(i['suggested_disposition'], 'unknown')}": i["alert_id"]
    for i in q["items"]
}
alert_id = options[st.sidebar.selectbox("Queue (highest risk first)", list(options))]

d = api_get(f"/alerts/{alert_id}")
ev = d["evidence"]
tx, al = ev.get("transaction", {}), ev.get("alert", {})
t = d["triage"]
sug = t["suggested_disposition"] if t else None
if t:
    CITED.update(CITE_RE.findall(" ".join(as_text(v) for v in t["summary"].values())))

st.markdown(f"### Alert {alert_id} &nbsp; {badge(sug)}", unsafe_allow_html=True)
f1, f2, f3, f4 = st.columns(4)
fact(f1, "Amount", fmt(tx.get("amount")))
fact(f2, "Risk score", fmt(al.get("risk_score")))
card = f"{tx.get('card_type') or ''} {tx.get('card_class') or ''}".strip().title()
fact(f3, "Card", card or "not recorded")
fact(f4, "When", str(tx.get("occurred_at", ""))[:16].replace("T", " "))
st.write("")

left, right = st.columns([3, 2], gap="large")
with left:
    if t is None:
        st.info(d["triage_note"])
    else:
        s = t["summary"]
        st.markdown("#### Summary")
        st.markdown(f'<div class="card">{rich(s.get("summary", ""))}</div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        with a:
            st.markdown("#### Why escalate")
            st.markdown(bullets(s.get("reasons_to_escalate", [])), unsafe_allow_html=True)
        with b:
            st.markdown("#### Why it may be a false positive")
            st.markdown(bullets(s.get("reasons_for_false_positive", [])), unsafe_allow_html=True)
        st.markdown("#### How reliable is the history?")
        st.markdown(
            f'<div class="card">{rich(s.get("history_reliability", ""))}'
            f'<br><span class="muted">Model note: {rich(s.get("confidence_note", ""))}</span></div>',
            unsafe_allow_html=True,
        )
with right:
    st.markdown("#### Evidence")
    st.caption("Highlighted rows are cited in the summary. Amber means the value is missing.")
    kv_card("Transaction", [(f"transaction.{k}", v) for k, v in tx.items()], missing="not recorded")
    cust, h30 = ev.get("customer", {}), ev.get("history_30d", {})
    kv_card("Customer and history",
            [(f"customer.{k}", v) for k, v in cust.items()]
            + [(f"history_30d.{k}", v) for k, v in h30.items()])
    kv_card("Same device and email, 30 days",
            [(f"same_device_and_email_30d.{k}", v)
             for k, v in ev.get("same_device_and_email_30d", {}).items()])
    prior = ev.get("prior_alerts", []) or []
    lines = [
        (f"prior_alerts[{i}]",
         ", ".join(f"{k}={fmt(v)}" for k, v in p.items()) if isinstance(p, dict) else str(p))
        for i, p in enumerate(prior)
    ]
    kv_card("Prior alerts", lines or [("prior_alerts", "none")])
    with st.expander("Raw evidence packet"):
        st.json(ev, expanded=False)

st.divider()
st.markdown("#### Your decision")
if d["disposition"]:
    x = d["disposition"]
    st.success(f"Already decided by {x['analyst_id']}: {LABELS.get(x['decision'], x['decision'])}")
else:
    decision = st.radio("Decision", list(LABELS), format_func=LABELS.get, index=None,
                        horizontal=True, key=f"dec_{alert_id}", label_visibility="collapsed")
    needs_reason = decision is not None and sug is not None and decision != sug
    label = "Why do you disagree with the model? (required)" if needs_reason else "Note (optional)"
    reason = st.text_area(label, max_chars=500, key=f"why_{alert_id}")
    ready = valid_analyst and decision is not None and (not needs_reason or reason.strip() != "")
    if st.button("Submit decision", type="primary", disabled=not ready, key=f"go_{alert_id}"):
        r = requests.post(
            f"{API_URL}/alerts/{alert_id}/disposition",
            headers=HEADERS,
            json={"analyst_id": analyst, "decision": decision, "reason": reason},
            timeout=15,
        )
        if r.status_code == 201:
            st.session_state["flash"] = True
            st.rerun()
        else:
            ctype = r.headers.get("content-type", "")
            detail = r.json().get("detail") if ctype.startswith("application/json") else None
            st.error(detail if isinstance(detail, str) else "The decision was not accepted. Check the fields.")

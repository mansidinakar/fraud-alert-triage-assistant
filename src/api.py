import json, os, secrets, threading, uuid
from typing import Literal

import duckdb
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field

try:
    from src.evidence import build_packet
except ImportError:
    from evidence import build_packet

load_dotenv()
DB = os.getenv("TRIAGE_DB", "data/triage.duckdb")
API_TOKEN = os.getenv("API_TOKEN", "")
if len(API_TOKEN) < 20:
    raise RuntimeError("API_TOKEN is missing or too short; add a long random value to .env")

DOCS = os.getenv("ENABLE_DOCS") == "1"
app = FastAPI(
    title="Fraud Alert Triage Assistant",
    docs_url="/docs" if DOCS else None,
    redoc_url=None,
    openapi_url="/openapi.json" if DOCS else None,
)

CON = duckdb.connect(DB)
WRITE_LOCK = threading.Lock()
Decision = Literal["escalate", "request_info", "close_false_positive"]


def require_key(x_api_key: str = Header(default="")):
    if not secrets.compare_digest(x_api_key.encode(), API_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Unauthorized")


def rows(cur, sql, params=()):
    res = cur.execute(sql, list(params))
    cols = [d[0] for d in res.description]
    return [dict(zip(cols, r)) for r in res.fetchall()]


def scrub(node):
    if isinstance(node, dict):
        return {k: scrub(v) for k, v in node.items()
                if not (str(k).startswith("syn_") or k == "is_fraud")}
    if isinstance(node, list):
        return [scrub(v) for v in node]
    return node


class DispositionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analyst_id: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,40}$")
    decision: Decision
    reason: str = Field(default="", max_length=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/queue", dependencies=[Depends(require_key)])
def queue(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    cur = CON.cursor()
    base = ("from triage_outputs t join alerts a on a.alert_id = t.alert_id "
            "left join dispositions d on d.alert_id = t.alert_id where d.alert_id is null")
    pending = cur.execute("select count(*) " + base).fetchone()[0]
    items = rows(cur, "select a.alert_id, a.risk_score, t.suggested_disposition " + base +
                 " order by a.risk_score desc, a.alert_id limit ? offset ?", [limit, offset])
    return {"pending": pending, "items": items}


@app.get("/alerts/{alert_id}", dependencies=[Depends(require_key)])
def get_alert(alert_id: int = Path(ge=1)):
    cur = CON.cursor()
    alert = rows(cur, "select * from alerts where alert_id = ?", [alert_id])
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    t = rows(cur, "select summary_json, suggested_disposition, model_id, prompt_version, created_at "
                  "from triage_outputs where alert_id = ?", [alert_id])
    triage = None
    if t:
        triage = dict(t[0])
        triage["summary"] = json.loads(triage.pop("summary_json"))
    disp = rows(cur, "select analyst_id, decision, reason, decided_at "
                     "from dispositions where alert_id = ?", [alert_id])
    return {
        "alert": alert[0],
        "evidence": scrub(build_packet(alert_id, con=cur)),
        "triage": triage,
        "triage_note": None if triage else "No validated summary for this alert; showing evidence only.",
        "disposition": disp[0] if disp else None,
    }


def _event_id_clause(cur):
    col_type = [r[1] for r in cur.execute("describe audit_log").fetchall()
                if r[0] == "event_id"][0].upper()
    if "INT" in col_type:
        return "(select coalesce(max(event_id), 0) + 1 from audit_log)", []
    return "?", [str(uuid.uuid4())]


@app.post("/alerts/{alert_id}/disposition", status_code=201, dependencies=[Depends(require_key)])
def post_disposition(body: DispositionIn, alert_id: int = Path(ge=1)):
    cur = CON.cursor()
    with WRITE_LOCK:
        if not rows(cur, "select 1 from alerts where alert_id = ?", [alert_id]):
            raise HTTPException(status_code=404, detail="Alert not found")
        if rows(cur, "select 1 from dispositions where alert_id = ?", [alert_id]):
            raise HTTPException(status_code=409, detail="Alert already has a disposition")
        t = rows(cur, "select suggested_disposition from triage_outputs where alert_id = ?", [alert_id])
        overrode = bool(t) and body.decision != t[0]["suggested_disposition"]
        if overrode and not body.reason.strip():
            raise HTTPException(status_code=422,
                                detail="A reason is required when overriding the suggested disposition")
        ev_sql, ev_params = _event_id_clause(cur)
        cur.execute("begin")
        try:
            cur.execute("insert into dispositions (alert_id, analyst_id, decision, reason, decided_at) "
                        "values (?, ?, ?, ?, current_timestamp)",
                        [alert_id, body.analyst_id, body.decision, body.reason.strip()])
            cur.execute("insert into audit_log (event_id, alert_id, actor, action, logged_at) "
                        "values (" + ev_sql + ", ?, ?, ?, current_timestamp)",
                        ev_params + [alert_id, body.analyst_id, "disposition:" + body.decision])
            cur.execute("commit")
        except Exception:
            cur.execute("rollback")
            raise
    return {"alert_id": alert_id, "decision": body.decision, "overrode_suggestion": overrode}

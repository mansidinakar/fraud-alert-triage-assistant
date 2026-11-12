import hashlib, json
import duckdb

DB = "data/triage.duckdb"
RESULTS = "data/eval_results.jsonl"

by_alert = {}
for line in open(RESULTS):
    r = json.loads(line)
    if r.get("prompt_version") != "triage_v2":
        continue
    if r.get("status") != "ok" or not isinstance(r.get("output"), dict):
        continue
    packet_json = json.dumps(r["packet"], sort_keys=True)
    by_alert[int(r["alert_id"])] = (
        int(r["alert_id"]),
        json.dumps(r["output"]),
        r["output"].get("suggested_disposition"),
        r.get("model_id"),
        r["prompt_version"],
        hashlib.sha256(packet_json.encode()).hexdigest(),
    )

rows = list(by_alert.values())
con = duckdb.connect(DB)
con.executemany("delete from triage_outputs where alert_id = ?", [(r[0],) for r in rows])
con.executemany(
    "insert into triage_outputs "
    "(alert_id, summary_json, suggested_disposition, model_id, prompt_version, evidence_hash, created_at) "
    "values (?, ?, ?, ?, ?, ?, current_timestamp)",
    rows,
)
print("loaded:", len(rows))
print("rows in triage_outputs:", con.execute("select count(*) from triage_outputs").fetchone()[0])
print("matching alerts table:", con.execute(
    "select count(*) from triage_outputs t join alerts a using (alert_id)").fetchone()[0])
print("by disposition:", con.execute(
    "select suggested_disposition, count(*) from triage_outputs group by 1 order by 2 desc").fetchall())
con.close()

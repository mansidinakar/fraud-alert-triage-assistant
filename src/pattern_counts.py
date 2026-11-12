import csv, json, math, re
from collections import defaultdict

RESULTS = "data/eval_results.jsonl"
SCORED = "data/handscore_prescreen.csv"

def load_v2():
    out = {}
    for line in open(RESULTS):
        r = json.loads(line)
        if r.get("prompt_version") != "triage_v2":
            continue
        if r.get("status") != "ok" or not isinstance(r.get("output"), dict):
            continue
        out[r["alert_id"]] = r
    return out

def scored_ids():
    ids = set()
    for r in csv.DictReader(open(SCORED, newline="", encoding="utf-8-sig")):
        if (r.get("unsupported_claims") or "").strip() == "":
            continue
        try:
            ids.add(int(float(r["alert_id"])))
        except (ValueError, KeyError):
            pass
    return ids

def flat(x):
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return " ".join(flat(i) for i in x)
    if isinstance(x, dict):
        return " ".join(flat(v) for v in x.values())
    return str(x)

def reasons(o, key):
    v = o.get(key) or []
    if isinstance(v, str):
        v = [v]
    return [flat(i) for i in v]

CITE = re.compile(r"\[[^\]]*\]")
def strip_cites(s):
    return CITE.sub(" ", s)

NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
       "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
JUDGE = re.compile(r"\b(low|moderate|modest|small|routine)\b", re.I)
COMPARE = re.compile(r"\b(lowest|highest|matches|below all|above all)\b", re.I)
DUR = re.compile(r"\b\d+(\.\d+)?[- ](days?|hours?|hrs?|minutes?|mins?|seconds?|weeks?)\b", re.I)
PRIOR = re.compile(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+prior\s+alerts?\b", re.I)
SHARED = re.compile(r"coarse|shared|share |cannot attribute|can't attribute|not attributable", re.I)

KEYS = [
    ("coarse_on_small_group", "says 'coarse' when group_txn_count_to_date <= 500"),
    ("caveat_then_counts_as_escalate_reason", "coarse/shared caveat, yet an escalate reason cites history_30d (the customer's own history)"),
    ("judgment_word_in_reason", "low/moderate/modest/small/routine inside an escalate or false-positive reason"),
    ("computed_duration", "states a duration (days/hours/minutes...) other than the 30-day window"),
    ("usd_or_dollar_added", "adds USD or $ (packet has no currency)"),
    ("comparison_word", "uses lowest/highest/matches/below all/above all (needs manual check)"),
    ("prior_alert_count_mismatch", "'N prior alerts' where N differs from len(prior_alerts)"),
    ("device_mentioned_when_device_missing", "mentions device in a reason when device_type is missing"),
    ("near_duplicate_prior_alerts", "two or more prior alerts with identical risk_score"),
]

def patterns(r):
    o, p = r["output"], r["packet"]
    esc = reasons(o, "reasons_to_escalate")
    fp = reasons(o, "reasons_for_false_positive")
    hist = flat(o.get("history_reliability"))
    summ = flat(o.get("summary"))
    claims_nc = strip_cites(" ".join([summ, hist] + esc + fp))
    group = (p.get("customer") or {}).get("group_txn_count_to_date")
    tx = p.get("transaction") or {}
    priors = p.get("prior_alerts") or []
    res = {}
    res["coarse_on_small_group"] = (bool(re.search(r"coarse", claims_nc, re.I))
                                    and isinstance(group, int) and group <= 500)
    uses_hist = any("history_30d" in t for t in esc)
    res["caveat_then_counts_as_escalate_reason"] = bool(SHARED.search(strip_cites(hist))) and uses_hist
    res["judgment_word_in_reason"] = any(JUDGE.search(strip_cites(t)) for t in esc + fp)
    res["computed_duration"] = any(
        not re.match(r"30[- ]day", m.group(0), re.I) for m in DUR.finditer(claims_nc))
    res["usd_or_dollar_added"] = bool(re.search(r"\bUSD\b|\$", claims_nc))
    res["comparison_word"] = bool(COMPARE.search(claims_nc))
    wrong = False
    for m in PRIOR.finditer(claims_nc):
        w = m.group(1).lower()
        n = NUM[w] if w in NUM else int(w)
        if n != len(priors):
            wrong = True
    res["prior_alert_count_mismatch"] = wrong
    dev_missing = tx.get("device_type") in (None, "")
    res["device_mentioned_when_device_missing"] = dev_missing and bool(
        re.search(r"\bdevice\b", " ".join(esc + fp), re.I))
    scores = []
    for a in priors:
        if isinstance(a, dict) and a.get("risk_score") is not None:
            scores.append(round(float(a["risk_score"]), 6))
    res["near_duplicate_prior_alerts"] = len(scores) != len(set(scores))
    return res

def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)

def report(label, recs, summary):
    n = len(recs)
    counts = defaultdict(int)
    ids = defaultdict(list)
    for aid, r in sorted(recs.items()):
        for k, v in patterns(r).items():
            if v:
                counts[k] += 1
                ids[k].append(aid)
    repaired = sum(1 for r in recs.values() if r.get("attempts") == 2)
    print(f"\n== {label} (n={n}) ==")
    print(f"repair used on {repaired}/{n} alerts")
    summary[label] = {"n": n, "repair_used": repaired, "patterns": {}}
    for k, desc in KEYS:
        c = counts[k]
        lo, hi = wilson(c, n)
        print(f"{k}: {c}/{n} ({c/n:.0%}, 95% CI {lo:.0%}-{hi:.0%})  - {desc}")
        print("    alert_ids:", ids[k][:12], "..." if len(ids[k]) > 12 else "")
        summary[label]["patterns"][k] = c

v2 = load_v2()
sel = scored_ids()
sample = {a: v2[a] for a in sel if a in v2}
print("v2 alerts loaded:", len(v2), "| hand-scored ids:", len(sel), "| matched:", len(sample))
summary = {}
report("hand-scored sample", sample, summary)
report("all v2 alerts", v2, summary)
json.dump(summary, open("data/pattern_counts.json", "w"), indent=2)
print("\nSaved data/pattern_counts.json")

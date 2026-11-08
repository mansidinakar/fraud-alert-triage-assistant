import csv, math, sys

PATH = "data/handscore_prescreen.csv"

def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))

rows = list(csv.DictReader(open(PATH, newline="", encoding="utf-8-sig")))
scored = [r for r in rows if (r.get("unsupported_claims") or "").strip() != ""]
n = len(scored)
if n == 0:
    sys.exit("No scored rows found")

claims = sum(int(float(r["n_claims"])) for r in scored)
unsup = sum(int(float(r["unsupported_claims"])) for r in scored)
zero = sum(1 for r in scored if int(float(r["unsupported_claims"])) == 0)
mis = sum(1 for r in scored if (r.get("misleading_framing_Y_N") or "").strip().upper() == "Y")
mis_known = sum(1 for r in scored if (r.get("misleading_framing_Y_N") or "").strip().upper() in ("Y", "N"))

print(f"Scored cases: {n}")
print(f"Claim-level faithfulness: {1 - unsup / claims:.1%}  ({unsup} unsupported of {claims} claims)")
lo, hi = wilson(zero, n)
print(f"Summaries with zero unsupported claims: {zero}/{n} = {zero / n:.1%}  (95% CI {lo:.0%}-{hi:.0%})")
lo, hi = wilson(mis, mis_known)
print(f"Misleading framing: {mis}/{mis_known} = {mis / mis_known:.1%}  (95% CI {lo:.0%}-{hi:.0%})")

d = [(r.get("disposition_sensible_Y_N_unsure") or "").strip().lower() for r in scored]
d = [x for x in d if x in ("y", "n", "unsure")]
if d:
    print(f"\nDisposition judged on {len(d)} cases: "
          f"Y {d.count('y')} ({d.count('y')/len(d):.0%}), "
          f"unsure {d.count('unsure')} ({d.count('unsure')/len(d):.0%}), "
          f"N {d.count('n')} ({d.count('n')/len(d):.0%})")

keys = ["near-duplicate", "duration", "coarse", "device", "reversed", "lowest", "matches", "date"]
print("\nNotes mentioning:")
for k in keys:
    c = sum(1 for r in scored if k in (r.get("notes") or "").lower())
    print(f"  {k}: {c}")

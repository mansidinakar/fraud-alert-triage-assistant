import csv, os, random, sys

FIRST = "data/handscore_prescreen.csv"
SECOND = "data/rescore.csv"

def picks():
    random.seed(11)
    return sorted(random.sample(range(1, 101), 10))

if "--template" in sys.argv:
    if os.path.exists(SECOND):
        sys.exit(SECOND + " already exists; delete it first if you want a new template")
    with open(SECOND, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case", "unsupported_claims", "misleading_framing_Y_N"])
        for c in picks():
            w.writerow([c, "", ""])
    print("Cases to re-score:", picks())
    sys.exit()

first = {}
for r in csv.DictReader(open(FIRST, newline="", encoding="utf-8-sig")):
    try:
        first[int(float(r["case"]))] = r
    except (ValueError, KeyError):
        pass

pairs = []
for r in csv.DictReader(open(SECOND, newline="", encoding="utf-8-sig")):
    u2 = (r.get("unsupported_claims") or "").strip()
    m2 = (r.get("misleading_framing_Y_N") or "").strip().upper()
    if u2 == "" or m2 not in ("Y", "N"):
        continue
    c = int(float(r["case"]))
    u1 = int(float(first[c]["unsupported_claims"]))
    m1 = first[c]["misleading_framing_Y_N"].strip().upper()
    pairs.append((c, u1, int(float(u2)), m1, m2))

n = len(pairs)
if n == 0:
    sys.exit("No completed rows in data/rescore.csv")

print("case  unsupported(1st,2nd)  misleading(1st,2nd)")
for c, u1, u2, m1, m2 in pairs:
    flag = "" if (u1 == u2 and m1 == m2) else "  <-- differs"
    print(f"{c:>4}  {u1:>5} {u2:>5}          {m1:>3} {m2:>3}{flag}")

exact = sum(1 for p in pairs if p[1] == p[2])
within1 = sum(1 for p in pairs if abs(p[1] - p[2]) <= 1)
mad = sum(abs(p[1] - p[2]) for p in pairs) / n
agree = sum(1 for p in pairs if p[3] == p[4])
po = agree / n
p1 = sum(1 for p in pairs if p[3] == "Y") / n
p2 = sum(1 for p in pairs if p[4] == "Y") / n
pe = p1 * p2 + (1 - p1) * (1 - p2)
kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")

print(f"\nRe-scored cases: {n}")
print(f"Unsupported count: exact match {exact}/{n}, within 1: {within1}/{n}, mean abs diff {mad:.2f}")
print(f"Misleading Y/N: agree {agree}/{n} ({po:.0%}), Cohen's kappa {kappa:.2f}")

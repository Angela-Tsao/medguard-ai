"""Clinical scenario (regression) tests: realistic inputs a judge, pharmacist or teammate might type, with what the
app MUST show. Simulates a user who keeps every auto-matched medication and every unrecognized word.
Usage: python src/eval_scenarios.py            (current app)
       python src/eval_scenarios.py --before   (without the Nov 22 safety layer and rules R28/R29, i.e. before the fix)"""
import sys, csv
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from pipeline import detect, check, safety_layer, ENGINE
from medguard import ROOT

BEFORE = "--before" in sys.argv
if BEFORE:  # switch off what was added on Nov 22
    ENGINE.ddi = ENGINE.ddi[ENGINE.ddi.rule_id != "R29"]
    ENGINE.group_rules = ENGINE.group_rules[ENGINE.group_rules.rule_id != "R28"]

def split(x): return [s.strip() for s in str(x).split(";") if s.strip() and str(x) != "nan"]

rows = []
for r in csv.DictReader(open(ROOT / "data" / "scenario_tests.csv")):
    dets = detect(r["input"])
    unrec = []
    if not BEFORE:
        dets, unrec, _ = safety_layer(r["input"], dets)
    meds = [d["canonical"] for d in dets if not d["needs_review"]]
    alerts, na = check(meds)
    shown = " | ".join(f"{a['drugs']}" for a in alerts).lower()
    na_all = [x.lower() for x in na] + [u.lower() for u in unrec]
    everything = (shown + " | " + " ".join(meds) + " | " + " ".join(na_all)).lower()
    fails = []
    for a in split(r["must_alert"]):
        if a.lower() not in {x["drugs"].lower() for x in alerts}: fails.append(f"missing alert: {a}")
    for a in split(r["must_not_assessed"]):
        if a.lower() not in na_all: fails.append(f"not listed as Not assessed: {a}")
    for a in split(r["must_not_contain"]):
        if a.lower() in everything: fails.append(f"wrongly shows: {a}")
    for a in split(r["must_unrecognized"]):
        if a.lower() not in na_all: fails.append(f"silently dropped: {a}")
    rows.append({"id": r["id"], "source": r["source"], "input": r["input"], "pass": not fails, "problem": "; ".join(fails)})
df = pd.DataFrame(rows)
tag = "before_fix" if BEFORE else "current"
df.to_csv(ROOT / "results" / f"scenario_tests_{tag}.csv", index=False)
pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 70)
print(f"{tag}: {df['pass'].sum()} of {len(df)} scenarios pass")
print(df[["id", "pass", "problem"]].to_string(index=False))

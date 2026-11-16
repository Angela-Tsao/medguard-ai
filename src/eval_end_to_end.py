"""End-to-end alert evaluation: do the right safety alerts appear for a free-text medication list?

Gold alerts are produced by running the alert engine on the TRUE medication list, so this measures how
recognition errors propagate into missed or wrong alerts. (It does not test whether the knowledge base
itself is clinically correct; that is checked separately against the sources.)
Two settings: auto-confirm (worst case: user accepts everything) and the human confirmation step is
simulated by removing detections whose matched similarity < 80 (a user would see 'anxiety -> ?' and delete it).
"""
import random, json
from pathlib import Path
import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).parent))
from medguard import ROOT, IN_SCOPE, VOCAB
from pipeline import detect, check, METHODS
sys.path.insert(0, str(ROOT / "src"))
import gen_data as G

rng = random.Random(7)
scope = sorted(IN_SCOPE)
# deliberately include risky combinations so every alert type is exercised
SEED_COMBOS = [["oxycodone", "lorazepam"], ["gabapentin", "tramadol"], ["lisinopril", "spironolactone"],
               ["warfarin", "ciprofloxacin"], ["warfarin", "ibuprofen"], ["diphenhydramine", "oxybutynin"],
               ["zolpidem", "sertraline", "gabapentin"], ["warfarin", "amiodarone"], ["losartan", "spironolactone"]]
OPENERS = ["Here is everything I take: ", "Mom's pill box has ", "Home visit med review - ", "I am on ",
           "Bottles on the counter: ", "My daily meds are "]
STYLES = ["clean", "brand", "misspelled", "ocr_noise", "dose_attached"]

def make_list(i):
    meds = list(SEED_COMBOS[i % len(SEED_COMBOS)])
    meds += rng.sample([m for m in scope if m not in meds], rng.randint(1, 4))
    parts = []
    for m in meds:
        st = rng.choice(STYLES)
        s = G.surface_for(m, st) or G.surface_for(m, "clean")
        parts.append(s)
    text = rng.choice(OPENERS) + ", ".join(parts[:-1]) + " and " + parts[-1] + " " + rng.choice(
        ["every day.", "in the morning and at night.", "plus vitamins.", "as needed for pain.", ""])
    return text, sorted(set(meds))

def alert_keys(meds):
    a, _ = check(meds)
    return {x["key"] for x in a}

rows, examples = [], []
lists = [make_list(i) for i in range(30)]
for method in METHODS:
    for setting in ["auto-confirm", "low-confidence matches (<80% similarity) sent to user review"]:
        tp = fn = fp = 0
        for text, gold in lists:
            det = detect(text, method)
            if setting == "low-confidence matches (<80% similarity) sent to user review":
                det = [d for d in det if d["similarity"] >= 80]
            pred = sorted({d["canonical"] for d in det})
            g, p = alert_keys(gold), alert_keys(pred)
            tp += len(g & p); fn += len(g - p); fp += len(p - g)
            if method == METHODS[0] and setting == "auto-confirm":
                examples.append({"text": text, "gold_meds": gold, "pred_meds": pred,
                                 "missed_alerts": [str(k) for k in g - p], "extra_alerts": [str(k) for k in p - g]})
        rows.append({"method": method, "setting": setting, "lists": len(lists), "gold_alerts": tp + fn,
                     "alert_recall": tp / (tp + fn), "missed_alerts": fn, "false_alerts": fp})
res = pd.DataFrame(rows)
res.to_csv(ROOT / "results" / "end_to_end_alerts.csv", index=False)
json.dump(examples, open(ROOT / "results" / "end_to_end_examples.json", "w"), indent=1)
print(res.round(3).to_string())
for e in examples[:4]:
    print(e["text"], "\n  gold:", e["gold_meds"], "\n  pred:", e["pred_meds"])

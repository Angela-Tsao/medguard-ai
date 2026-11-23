"""Score the SEALED team test set once. No thresholds or models are changed here.

Each token gets a gold label:
  IN  = medication in our dictionary (has a canonical name)   -> should be found and mapped correctly
  OOV = medication NOT in our dictionary                      -> should be flagged, never auto-mapped to another drug
  NEU = supplement / drug class / product suffix              -> ignored
  O   = ordinary word                                         -> should not be flagged
"""
import sys, json, re
from pathlib import Path
import numpy as np, pandas as pd
from scipy.sparse import hstack, csr_matrix
sys.path.insert(0, str(Path(__file__).parent))
from medguard import tokenize, sentence_features, char_text, best_match, strip_dose, NAME2CANON, AlertEngine, ROOT
from pipeline import _M, ctx, is_common_word
sys.path.insert(0, str(ROOT / "data"))

TAG = sys.argv[1] if len(sys.argv) > 1 else "sealed_test_1"
gold_mod = __import__(f"{TAG}_gold")
GOLD, NEUTRAL = gold_mod.GOLD, gold_mod.NEUTRAL
SENTS = [l.strip() for l in open(ROOT / "data" / f"{TAG}.txt") if l.strip()]
assert len(SENTS) == len(GOLD)
engine = AlertEngine()
rng = np.random.default_rng(0)

def label_tokens(toks, gold):
    lab = ["O"] * len(toks)
    for i, t in enumerate(toks):
        if t.lower() in NEUTRAL:
            lab[i] = "NEU"
    used = set()
    for m in gold:
        surf, _, canon = m.partition("|")          # "surface|canonical" marks a labelled misspelling
        for i, t in enumerate(toks):
            if i not in used and t.lower() == surf.lower():
                used.add(i)
                c = canon or NAME2CANON.get(surf.lower())
                lab[i] = ("IN", c, bool(canon)) if c and c != "OOV" else ("OOV", surf)
                break
    return lab

def p_lr(toks):
    X = np.array(sentence_features(toks)); C = [char_text(toks, i) for i in range(len(toks))]
    return _M["lr"].predict_proba(hstack([_M["tfidf"].transform(C), csr_matrix(X)]).tocsr())[:, 1]
def p_lrc(toks):
    X = np.array(sentence_features(toks)); C = [char_text(toks, i) for i in range(len(toks))]
    D = _M["dv"].transform([ctx(toks, i) for i in range(len(toks))])
    return _M["lrc"].predict_proba(hstack([_M["tfidf"].transform(C), csr_matrix(X), D]).tocsr())[:, 1]
def p_rf(toks): return _M["rf"].predict_proba(np.array(sentence_features(toks)))[:, 1]
def p_gb(toks): return _M["gb"].predict_proba(np.array(sentence_features(toks)))[:, 1]
def p_fuzzy(toks): return np.array([best_match(t)[0] / 100 if any(c.isalpha() for c in t) and len(t) >= 3 else 0 for t in toks])
def p_exact(toks): return np.array([float(strip_dose(t) in NAME2CANON) for t in toks])

THR = _M["thr"]
METHODS = {
    "Exact match (baseline)": (p_exact, 0.5),
    "Fuzzy match (baseline)": (p_fuzzy, THR["fuzzy"][0]),
    "Logistic regression (selected)": (p_lr, THR["logreg"][0]),
    "Logistic regression + context": (p_lrc, THR["logreg_ctx"][0]),
    "Random forest": (p_rf, THR["rforest"][0]),
    "Gradient boosting": (p_gb, THR["gboost"][0]),
}

def alert_keys(meds):
    return {str(a["key"]) for a in engine.check(sorted(set(meds)))[0]} if meds else set()

rows, examples = [], []
for name, (fn, thr) in METHODS.items():
    per = []  # per-sentence counts for bootstrap
    for si, (s, g) in enumerate(zip(SENTS, GOLD)):
        toks = tokenize(s); lab = label_tokens(toks, g)
        flags = fn(toks) >= thr
        c = dict(in_total=0, in_auto_ok=0, in_review=0, in_wrong=0, in_missed=0,
                 oov_total=0, oov_auto_wrong=0, oov_review=0, oov_missed=0,
                 o_flag_auto=0, o_flag_review=0, med_flags=0, all_flags=0, typo_total=0, typo_ok=0)
        pred_meds, gold_meds = [], [l[1] for l in lab if isinstance(l, tuple) and l[0] == "IN"]
        for i, (t, l) in enumerate(zip(toks, lab)):
            flagged = bool(flags[i])
            if flagged:
                sim, canon, _ = best_match(t)
                review = is_common_word(t) or sim < 80
            if l == "NEU":
                continue
            if flagged:
                c["all_flags"] += 1
                if not review:
                    pred_meds.append(canon)
            if isinstance(l, tuple) and l[0] == "IN":
                c["in_total"] += 1
                if len(l) > 2 and l[2]:
                    c["typo_total"] += 1
                    if flagged and not review and canon == l[1]: c["typo_ok"] += 1
                if not flagged: c["in_missed"] += 1
                else:
                    c["med_flags"] += 1
                    if review: c["in_review"] += 1
                    elif canon == l[1]: c["in_auto_ok"] += 1
                    else: c["in_wrong"] += 1
            elif isinstance(l, tuple) and l[0] == "OOV":
                c["oov_total"] += 1
                if not flagged: c["oov_missed"] += 1
                else:
                    c["med_flags"] += 1
                    if review: c["oov_review"] += 1
                    else:
                        c["oov_auto_wrong"] += 1
                        if name.startswith("Logistic regression (sel"):
                            examples.append({"sentence": si + 1, "token": t, "mapped_to": canon, "similarity": sim, "kind": "OOV drug auto-mapped to a different drug"})
            else:  # ordinary word
                if flagged:
                    if review: c["o_flag_review"] += 1
                    else:
                        c["o_flag_auto"] += 1
                        if name.startswith("Logistic regression (sel"):
                            examples.append({"sentence": si + 1, "token": t, "mapped_to": canon, "similarity": sim, "kind": "ordinary word auto-mapped to a drug"})
            if isinstance(l, tuple) and l[0] == "IN" and not flagged and name.startswith("Logistic regression (sel"):
                examples.append({"sentence": si + 1, "token": t, "mapped_to": None, "similarity": None, "kind": "dictionary drug missed"})
        g_al, p_al = alert_keys(gold_meds), alert_keys(pred_meds)
        c.update(alert_gold=len(g_al), alert_tp=len(g_al & p_al), alert_fp=len(p_al - g_al))
        per.append(c)
    df = pd.DataFrame(per)
    tot = df.sum()
    def stats(d):
        t = d.sum()
        rec = t.in_auto_ok / t.in_total
        det_rec = (t.in_total - t.in_missed) / t.in_total
        prec = t.med_flags / t.all_flags if t.all_flags else 1.0
        return rec, det_rec, prec
    boots = np.array([stats(df.iloc[rng.integers(0, len(df), len(df))]) for _ in range(1000)])
    lo, hi = np.percentile(boots, 2.5, 0), np.percentile(boots, 97.5, 0)
    rec, det_rec, prec = stats(df)
    rows.append({"method": name, "in_dict_mentions": int(tot.in_total),
                 "found_and_mapped_correctly": rec, "fm_lo": lo[0], "fm_hi": hi[0],
                 "found_any": det_rec, "misspelled_mentions": int(tot.typo_total),
                 "misspelled_found_correctly": (tot.typo_ok / tot.typo_total) if tot.typo_total else float("nan"), "sent_to_review": int(tot.in_review), "mapped_wrong": int(tot.in_wrong), "missed": int(tot.in_missed),
                 "precision": prec, "prec_lo": lo[2], "prec_hi": hi[2],
                 "ordinary_word_auto_mapped": int(tot.o_flag_auto), "ordinary_word_to_review": int(tot.o_flag_review),
                 "oov_mentions": int(tot.oov_total), "oov_auto_mapped_wrong": int(tot.oov_auto_wrong),
                 "oov_to_review": int(tot.oov_review), "oov_missed": int(tot.oov_missed),
                 "alerts_expected": int(tot.alert_gold), "alerts_found": int(tot.alert_tp), "wrong_alerts": int(tot.alert_fp)})
res = pd.DataFrame(rows)
res.to_csv(ROOT / "results" / f"{TAG}_results.csv", index=False)
pd.DataFrame(examples).to_csv(ROOT / "results" / f"{TAG}_selected_model_errors.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(res.round(3).T.to_string())

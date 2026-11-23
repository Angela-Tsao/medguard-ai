"""Mention-level scoring for test sets where one medication name can be split across several words
(e.g. "metop ro-lol"). A mention counts as found if ANY of its words is flagged and mapped to the right drug.
No thresholds or models are changed here.  Usage: python3 src/eval_mentions.py sealed_test_4
"""
import sys, re
from pathlib import Path
import numpy as np, pandas as pd
from scipy.sparse import hstack, csr_matrix
sys.path.insert(0, str(Path(__file__).parent))
from medguard import tokenize, sentence_features, char_text, best_match, strip_dose, NAME2CANON, AlertEngine, ROOT
from pipeline import _M, ctx, is_common_word
sys.path.insert(0, str(ROOT / "data"))

TAG = sys.argv[1] if len(sys.argv) > 1 else "sealed_test_4"
GOLD = __import__(f"{TAG}_gold").GOLD
SENTS = [l.strip() for l in open(ROOT / "data" / f"{TAG}.txt") if l.strip()]
assert len(SENTS) == len(GOLD)
engine = AlertEngine(); rng = np.random.default_rng(0)
UNITS = {"mg", "mcg", "ml", "u", "iu", "units", "caps", "qhs", "bid", "odt", "mgs", "mill", "mgodt", "mgsyringe", "tab", "halftab", "milligrams"}
def neutral(t): return bool(re.search(r"\d", t)) or t.lower() in UNITS

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
METHODS = {"Exact match (baseline)": (p_exact, 0.5), "Fuzzy match (baseline)": (p_fuzzy, THR["fuzzy"][0]),
           "Logistic regression (selected)": (p_lr, THR["logreg"][0]), "Logistic regression + context": (p_lrc, THR["logreg_ctx"][0]),
           "Random forest": (p_rf, THR["rforest"][0]), "Gradient boosting": (p_gb, THR["gboost"][0])}

def variant(span, written, gold):
    if len(span) == 2 and " " in written and written.lower() not in NAME2CANON: return "split by a space"
    w = written.lower()
    if w in NAME2CANON: return "correct name or listed brand"
    if "-" in w: return "dropped letters / sound spelling"
    return "brand not in our name list"

def alert_keys(meds):
    return {str(a["key"]) for a in engine.check(sorted(set(meds)))[0]} if meds else set()

def norm(entry):
    if isinstance(entry, dict): return entry["mentions"], set(entry.get("neutral", []))
    return [entry], set()

rows, detail = [], []
for name, (fn, thr) in METHODS.items():
    per = []
    for si, (s, entry) in enumerate(zip(SENTS, GOLD)):
        mentions, neu = norm(entry)
        toks = tokenize(s); flags = fn(toks) >= thr
        res = {}
        for i, t in enumerate(toks):
            if flags[i]:
                sim, canon, _ = best_match(t); res[i] = (canon, is_common_word(t) or sim < 80, sim)
        all_span = {i for m in mentions for i in m[0]}
        other = [i for i in res if i not in all_span and i not in neu and not neutral(toks[i])]
        pred = sorted({res[i][0] for i in res if not res[i][1] and i not in neu and not neutral(toks[i])})
        gold_meds = [m[1] for m in mentions if not m[1].startswith("OOV:")]
        g_al = alert_keys(gold_meds); p_al = alert_keys(pred)
        sent = dict(ordinary_auto=sum(not res[i][1] for i in other), ordinary_review=sum(res[i][1] for i in other),
                    ordinary_words=", ".join(f"{toks[i]}->{res[i][0]}" for i in other),
                    alert_gold=len(g_al), alert_tp=len(g_al & p_al), alert_fp=len(p_al - g_al))
        items = mentions if mentions else [None]
        for k, m in enumerate(items):
            if m is None:
                r = dict(drug="(no medication)", oov=False, kind="none", variant="none", outcome="none", mapped_to="", span_flags=0)
            else:
                span, gold, written = m
                r = dict(drug=gold.replace("OOV:", ""), oov=gold.startswith("OOV:"), kind="oov" if gold.startswith("OOV:") else "in",
                         variant=variant(span, written, gold) if not gold.startswith("OOV:") else "not in our list")
                hits = [res[i] for i in span if i in res]; auto = [h for h in hits if not h[1]]
                if not hits: r["outcome"] = "missed"
                elif r["oov"]: r["outcome"] = "auto-mapped to another drug" if auto else "sent to review"
                elif any(h[0] == gold for h in auto): r["outcome"] = "found and mapped correctly"
                elif auto: r["outcome"] = "auto-mapped to another drug"
                else: r["outcome"] = "sent to review"
                r["mapped_to"] = ", ".join(sorted({h[0] for h in hits})); r["span_flags"] = sum(i in res for i in span)
            # sentence-level counts go on the first item only
            r.update(sent if k == 0 else dict(ordinary_auto=0, ordinary_review=0, ordinary_words="", alert_gold=0, alert_tp=0, alert_fp=0))
            per.append(r)
            if name.startswith("Logistic regression (sel"): detail.append({"sentence": si + 1, "written": "" if m is None else m[2], **r})
    df = pd.DataFrame(per)
    def stats(d):
        ind = d[d.kind == "in"]
        return ((ind.outcome == "found and mapped correctly").mean(), (ind.outcome != "missed").mean(),
                d.span_flags.sum() / max(1, d.span_flags.sum() + d.ordinary_auto.sum() + d.ordinary_review.sum()))
    drugs = df.drug.unique(); groups = {k: v for k, v in df.groupby("drug")}
    boots = np.array([stats(pd.concat([groups[d] for d in rng.choice(drugs, len(drugs))])) for _ in range(1000)])
    lo, hi = np.percentile(boots, 2.5, 0), np.percentile(boots, 97.5, 0)
    rec, any_rec, prec = stats(df); ind, oov = df[df.kind == "in"], df[df.kind == "oov"]
    row = {"method": name, "in_dict_mentions": len(ind), "found_and_mapped_correctly": rec, "fm_lo": lo[0], "fm_hi": hi[0],
           "found_any": any_rec, "sent_to_review": int((ind.outcome == "sent to review").sum()),
           "mapped_wrong": int((ind.outcome == "auto-mapped to another drug").sum()), "missed": int((ind.outcome == "missed").sum()),
           "precision": prec, "prec_lo": lo[2], "prec_hi": hi[2],
           "ordinary_word_auto_mapped": int(df.ordinary_auto.sum()), "ordinary_word_to_review": int(df.ordinary_review.sum()),
           "oov_mentions": len(oov), "oov_auto_mapped_wrong": int((oov.outcome == "auto-mapped to another drug").sum()),
           "oov_to_review": int((oov.outcome == "sent to review").sum()), "oov_missed": int((oov.outcome == "missed").sum()),
           "alerts_expected": int(df.alert_gold.sum()), "alerts_found": int(df.alert_tp.sum()), "wrong_alerts": int(df.alert_fp.sum())}
    for v, g in ind.groupby("variant"):
        row[f"correct: {v} (n={len(g)})"] = (g.outcome == "found and mapped correctly").mean()
    rows.append(row)
res = pd.DataFrame(rows)
res.to_csv(ROOT / "results" / f"{TAG}_results.csv", index=False)
pd.DataFrame(detail).to_csv(ROOT / "results" / f"{TAG}_selected_model_detail.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(res.round(3).T.to_string())

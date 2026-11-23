"""End-to-end pipeline used by the app: text -> detected medication tokens -> canonical names -> alerts."""
import pickle, re
from pathlib import Path
import numpy as np
from scipy.sparse import hstack, csr_matrix
import sys
sys.path.insert(0, str(Path(__file__).parent))
from medguard import (tokenize, sentence_features, char_text, best_match, strip_dose, NAME2CANON,
                      AlertEngine, IN_SCOPE, ROOT)

_M = pickle.load(open(ROOT / "models" / "sklearn_models.pkl", "rb"))
ENGINE = AlertEngine()

def ctx(tokens, i):  # must match compare_models.ctx
    p = tokens[i-1].lower() if i > 0 else "<s>"
    p2 = tokens[i-2].lower() if i > 1 else "<s>"
    n = tokens[i+1].lower() if i+1 < len(tokens) else "</s>"
    n = "<num>" if re.match(r"^\d", n) else n
    return {"prev=" + p: 1, "prev2=" + p2: 1, "next=" + n: 1, "prevnext=" + p + "_" + n: 1}

def scores_lrc(tokens):
    X = np.array(sentence_features(tokens))
    C = [char_text(tokens, i) for i in range(len(tokens))]
    D = _M["dv"].transform([ctx(tokens, i) for i in range(len(tokens))])
    return _M["lrc"].predict_proba(hstack([_M["tfidf"].transform(C), csr_matrix(X), D]).tocsr())[:, 1]

def scores_lr(tokens):
    X = np.array(sentence_features(tokens))
    C = [char_text(tokens, i) for i in range(len(tokens))]
    return _M["lr"].predict_proba(hstack([_M["tfidf"].transform(C), csr_matrix(X)]).tocsr())[:, 1]

# Selected model = lowest misclassification cost on VALIDATION (see results/thresholds.json)
METHODS = ["Logistic regression", "Fuzzy match (baseline)", "Exact match (baseline)"]

from wordfreq import zipf_frequency
COMMON_WORD_ZIPF = 3.5  # everyday English words (e.g., "diabetes", "medicine") are never mapped to a drug

def is_common_word(tok):
    t = strip_dose(tok).lower()
    return t not in NAME2CANON and t.isalpha() and zipf_frequency(t, "en") >= COMMON_WORD_ZIPF

def detect(text, method="Logistic regression", threshold=None):
    tokens = tokenize(text or "")
    if not tokens:
        return []
    if method == "Exact match (baseline)":
        flags = [(strip_dose(t) in NAME2CANON, 1.0) for t in tokens]
    elif method == "Fuzzy match (baseline)":
        thr = threshold if threshold is not None else _M["thr"]["fuzzy"][0]
        sims = [best_match(t)[0] / 100 if any(c.isalpha() for c in t) and len(t) >= 3 else 0.0 for t in tokens]
        flags = [(s >= thr, s) for s in sims]
    else:
        thr = threshold if threshold is not None else _M["thr"]["logreg"][0]
        p = scores_lr(tokens)
        flags = [(x >= thr, float(x)) for x in p]
    out = []
    for t, (f, score) in zip(tokens, flags):
        if f:
            sim, canon, matched = best_match(t)
            common = is_common_word(t)
            out.append({"token": t, "canonical": canon, "matched_name": matched,
                        "similarity": round(sim, 1), "model_score": round(score, 3),
                        "in_scope": canon in IN_SCOPE, "common_word": common,
                        # everyday words and weak matches are never auto-mapped: the user must confirm
                        "needs_review": common or sim < 80})
    return out

# ---------------- safety layer on top of the model (added Nov 22 after live testing) ----------------
# These steps do not change the model or its evaluation; they decide what the user and clinician SEE.
import csv as _csv
from rapidfuzz import process as _proc, fuzz as _fuzz
OTHER = {r["name"]: r["generic"] for r in _csv.DictReader(open(ROOT / "data" / "other_drug_names.csv"))}
COMBOS = [(r["phrase"], r["ingredients"].split(";"), r["source"]) for r in _csv.DictReader(open(ROOT / "data" / "combo_products.csv"))]
RARE_ZIPF = 2.5      # words this rare in English, not recognized as a medication, are shown as "unrecognized"

def _other_match(tok):
    t = strip_dose(tok).lower()
    if len(t) < 4 or not any(c.isalpha() for c in t):
        return 0, None, None
    hit = _proc.extractOne(t, list(OTHER), scorer=_fuzz.ratio)
    return (hit[1], OTHER[hit[0]], hit[0]) if hit else (0, None, None)

def safety_layer(text, dets):
    """1) Combination products (Tylenol PM) -> each ingredient.  2) Names of known medications outside our
    dictionary (Toradol = ketorolac) are named and marked Not assessed instead of being mapped to a look-alike
    (tramadol).  3) Returns rare words we could not identify, so nothing disappears silently."""
    tokens = tokenize(text or "")
    low = (text or "").lower()
    out, used = [], set()
    # 1. combination products
    for phrase, ingredients, source in COMBOS:
        for m in re.finditer(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", low):
            surface = text[m.start():m.end()]
            used |= set(phrase.split())
            for ing in ingredients:
                out.append({"token": surface, "canonical": ing, "matched_name": phrase, "similarity": 100.0, "model_score": 1.0,
                            "in_scope": ing in IN_SCOPE, "common_word": False, "needs_review": False,
                            "combo": f"{surface} contains {' + '.join(ingredients)} ({source})"})
    # generic "<brand> PM" that is not in our table: warn plainly
    pm_unknown = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)
                  if tokens[i + 1].lower() == "pm" and tokens[i].lower() not in used
                  and (strip_dose(tokens[i]).lower() in NAME2CANON or tokens[i].lower() in OTHER)]
    # 2. model detections, re-checked against known names outside our dictionary
    seen = set()
    for d in dets:
        if d["token"].lower() in used:
            continue
        osim, ogen, oname = _other_match(d["token"])
        exact_ours = strip_dose(d["token"]).lower() in NAME2CANON
        if not exact_ours and ogen and osim >= 85 and osim > d["similarity"]:
            d = dict(d, canonical=ogen, matched_name=oname, similarity=round(osim, 1), in_scope=False,
                     outside_list=True, needs_review=osim < 90,
                     lookalike=None if d["canonical"] == ogen else d["canonical"])
        out.append(d); seen.add(d["token"].lower())
    #    known outside names the model did not flag
    for t in tokens:
        tl = strip_dose(t).lower()
        if tl in OTHER and t.lower() not in seen and tl not in used and tl not in NAME2CANON:
            out.append({"token": t, "canonical": OTHER[tl], "matched_name": tl, "similarity": 100.0, "model_score": 0.0,
                        "in_scope": False, "common_word": False, "needs_review": False, "outside_list": True})
            seen.add(t.lower())
    # 3. rare words nobody recognized (could be a medication we have never seen)
    unrecognized = []
    for t in tokens:
        tl = t.lower().strip("-")
        if (len(tl) >= 5 and re.fullmatch(r"[a-z][a-z\-]*", tl) and tl not in seen and tl not in used
                and tl not in NAME2CANON and zipf_frequency(tl.replace("-", ""), "en") < RARE_ZIPF
                and t not in unrecognized):
            unrecognized.append(t)
    return out, unrecognized, pm_unknown

def check(canonicals):
    return ENGINE.check(canonicals)

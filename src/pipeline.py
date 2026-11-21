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

def check(canonicals):
    return ENGINE.check(canonicals)

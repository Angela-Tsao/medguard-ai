"""Compare medication-name detectors: exact match, fuzzy match (baselines), logistic regression,
random forest, and a trained spaCy NER. Thresholds are tuned on VALIDATION only; test sets are
scored once. Reports precision / recall / F1 by input type with bootstrap 95% CIs."""
import json, time, random, pickle, re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import precision_recall_curve
import spacy
from spacy.tokens import Doc
from spacy.training import Example
import sys
sys.path.insert(0, str(Path(__file__).parent))
from medguard import (best_match, normalize, sentence_features, char_text, FEATURE_NAMES, strip_dose,
                      NAME2CANON, ROOT, DATA)

RES = ROOT / "results"; RES.mkdir(exist_ok=True)
MODELS = ROOT / "models"; MODELS.mkdir(exist_ok=True)
rng = np.random.default_rng(42)
random.seed(42)

def load(name):
    return [json.loads(l) for l in open(DATA / f"sentences_{name}.jsonl")]
train, val, test_s, test_h = load("train"), load("val"), load("test_synthetic"), load("test_handwritten")

def ctx(tokens, i):
    p = tokens[i-1].lower() if i > 0 else "<s>"
    p2 = tokens[i-2].lower() if i > 1 else "<s>"
    n = tokens[i+1].lower() if i+1 < len(tokens) else "</s>"
    n = "<num>" if re.match(r"^\d", n) else n
    return {"prev=" + p: 1, "prev2=" + p2: 1, "next=" + n: 1, "prevnext=" + p + "_" + n: 1}

def flat(sents):
    X, Xc, Xd, y, idx = [], [], [], [], []
    for si, s in enumerate(sents):
        feats = sentence_features(s["tokens"])
        for ti, f in enumerate(feats):
            X.append(f); Xc.append(char_text(s["tokens"], ti)); Xd.append(ctx(s["tokens"], ti))
            y.append(s["labels"][ti]); idx.append((si, ti))
    return np.array(X), Xc, Xd, np.array(y), idx

print("featurizing ...")
Xtr, Ctr, Dtr, ytr, _ = flat(train)

# ---------------- detectors ------------------------------------------------------------
def det_exact(s):
    return [int(strip_dose(t) in NAME2CANON) for t in s["tokens"]]

def sim_scores(s):
    return [best_match(t)[0] / 100 if any(c.isalpha() for c in t) and len(t) >= 3 else 0.0
            for t in s["tokens"]]

tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2)
Ttr = tfidf.fit_transform(Ctr)
lr = LogisticRegression(max_iter=3000, C=2.0, class_weight="balanced")
lr.fit(hstack([Ttr, csr_matrix(Xtr)]).tocsr(), ytr)

rf = RandomForestClassifier(n_estimators=300, min_samples_leaf=2, class_weight="balanced",
                            n_jobs=-1, random_state=42)
rf.fit(Xtr, ytr)
rf.set_params(n_jobs=1)

dv = DictVectorizer(); Dtr_m = dv.fit_transform(Dtr)
lrc = LogisticRegression(max_iter=4000, C=1.0, class_weight="balanced")
lrc.fit(hstack([Ttr, csr_matrix(Xtr), Dtr_m]).tocsr(), ytr)

gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1, class_weight="balanced", random_state=42)
gb.fit(Xtr, ytr)

def prob_lr(s):
    X = np.array(sentence_features(s["tokens"]))
    C = [char_text(s["tokens"], i) for i in range(len(s["tokens"]))]
    return lr.predict_proba(hstack([tfidf.transform(C), csr_matrix(X)]).tocsr())[:, 1]

def prob_lrc(s):
    X = np.array(sentence_features(s["tokens"]))
    C = [char_text(s["tokens"], i) for i in range(len(s["tokens"]))]
    D = dv.transform([ctx(s["tokens"], i) for i in range(len(s["tokens"]))])
    return lrc.predict_proba(hstack([tfidf.transform(C), csr_matrix(X), D]).tocsr())[:, 1]

def prob_gb(s):
    return gb.predict_proba(np.array(sentence_features(s["tokens"])))[:, 1]

def prob_rf(s):
    return rf.predict_proba(np.array(sentence_features(s["tokens"])))[:, 1]

# spaCy NER (blank English pipeline, trained from scratch on the same training sentences)
print("training spaCy NER ...")
spacy.util.fix_random_seed(42)
nlp = spacy.blank("en")
ner = nlp.add_pipe("ner"); ner.add_label("DRUG")
def to_example(s):
    doc = Doc(nlp.vocab, words=s["tokens"])
    ents = [(i, i + 1, "DRUG") for i, l in enumerate(s["labels"]) if l]
    tags = ["U-DRUG" if l else "O" for l in s["labels"]]
    return Example.from_dict(doc, {"entities": tags})
train_ex = [to_example(s) for s in train]
optimizer = nlp.initialize(lambda: train_ex)
spacy_losses = []
for epoch in range(12):
    random.shuffle(train_ex)
    losses = {}
    for b in spacy.util.minibatch(train_ex, size=32):
        nlp.update(b, sgd=optimizer, drop=0.2, losses=losses)
    spacy_losses.append(losses["ner"])
print("spaCy losses:", [round(x) for x in spacy_losses])

def det_spacy(s):
    doc = nlp(Doc(nlp.vocab, words=s["tokens"]))
    out = [0] * len(s["tokens"])
    for e in doc.ents:
        for i in range(e.start, e.end):
            out[i] = 1
    return out

# ---------------- threshold tuning on validation ----------------------------------------
# Cost-based threshold (asymmetric costs): a missed medication can hide a dangerous interaction and
# the user never sees it; a false flag is visible in the confirmation step and costs one click.
# We set cost(miss) = 10 x cost(false flag) and pick the threshold that minimizes total cost on VALIDATION.
COST_MISS, COST_FALSE = 10.0, 1.0
def tune(score_fn, sents, name):
    ys, ps = [], []
    for s in sents:
        ys += s["labels"]; ps += list(score_fn(s))
    ys = np.array(ys); ps = np.array(ps)
    p, r, t = precision_recall_curve(ys, ps)
    npos = ys.sum()
    tp = r[:-1] * npos
    fp = np.where(p[:-1] > 0, tp / p[:-1] - tp, 0)
    fn = npos - tp
    cost = COST_MISS * fn + COST_FALSE * fp
    i = int(np.argmin(cost))
    curve = pd.DataFrame({"threshold": t, "precision": p[:-1], "recall": r[:-1], "cost": cost})
    curve.to_csv(RES / f"val_pr_curve_{name}.csv", index=False)
    return float(t[i]), float(r[i]), float(p[i])

thr = {}
for name, fn in [("fuzzy", sim_scores), ("logreg", prob_lr), ("logreg_ctx", prob_lrc), ("rforest", prob_rf), ("gboost", prob_gb)]:
    thr[name] = tune(fn, val, name)
    print(f"{name}: threshold={thr[name][0]:.3f} val_recall={thr[name][1]:.3f} val_precision={thr[name][2]:.3f}")

DETECTORS = {
    "Exact match (baseline)": det_exact,
    "Fuzzy match (baseline)": lambda s: [int(x >= thr["fuzzy"][0]) for x in sim_scores(s)],
    "Logistic regression": lambda s: [int(x >= thr["logreg"][0]) for x in prob_lr(s)],
    "Logistic regression + context": lambda s: [int(x >= thr["logreg_ctx"][0]) for x in prob_lrc(s)],
    "Random forest": lambda s: [int(x >= thr["rforest"][0]) for x in prob_rf(s)],
    "Gradient boosting": lambda s: [int(x >= thr["gboost"][0]) for x in prob_gb(s)],
    "spaCy NER": det_spacy,
}

# ---------------- evaluation -------------------------------------------------------------
def per_sentence(s, pred):
    gold = set(i for i, l in enumerate(s["labels"]) if l)
    predset = set(i for i, l in enumerate(pred) if l)
    tp = len(gold & predset)
    canon_ok = sum(1 for m in s["mentions"] if m["tok"] in predset and normalize(s["tokens"][m["tok"]]) == m["canonical"])
    return tp, len(predset), len(gold), canon_ok

def summarize(rows, B=1000):
    rows = np.array(rows, dtype=float)
    def m(r):
        tp, npred, ngold, cok = r.sum(0)
        P = tp / npred if npred else 1.0
        R = tp / ngold if ngold else np.nan
        F = 2 * P * R / (P + R) if (P + R) else 0.0
        return P, R, F, (cok / ngold if ngold else np.nan)
    point = m(rows)
    boots = np.array([m(rows[rng.integers(0, len(rows), len(rows))]) for _ in range(B)])
    lo, hi = np.nanpercentile(boots, 2.5, axis=0), np.nanpercentile(boots, 97.5, axis=0)
    return point, lo, hi

results, timings, errors = [], {}, []
for dname, fn in DETECTORS.items():
    for setname, sents in [("Synthetic test (unseen drugs + templates)", test_s), ("Hand-written holdout", test_h)]:
        t0 = time.perf_counter()
        preds = [fn(s) for s in sents]
        dt = (time.perf_counter() - t0) / len(sents) * 1000
        timings.setdefault(dname, []).append(dt)
        bytype = {}
        for s, p in zip(sents, preds):
            r = per_sentence(s, p)
            bytype.setdefault(s["input_type"], []).append(r)
            bytype.setdefault("ALL", []).append(r)
            if setname.startswith("Hand"):
                gold = {m["tok"] for m in s["mentions"]}
                pr = {i for i, l in enumerate(p) if l}
                for i in gold - pr:
                    errors.append({"model": dname, "type": "missed", "token": s["tokens"][i], "input_type": s["input_type"], "sentence": " ".join(s["tokens"])})
                for i in pr - gold:
                    errors.append({"model": dname, "type": "false_alarm", "token": s["tokens"][i], "input_type": s["input_type"], "sentence": " ".join(s["tokens"])})
        for it, rows in bytype.items():
            (P, R, F, NR), lo, hi = summarize(rows)
            results.append({"model": dname, "test_set": setname, "input_type": it, "n_sentences": len(rows),
                            "n_mentions": int(np.array(rows)[:, 2].sum()),
                            "precision": P, "precision_lo": lo[0], "precision_hi": hi[0], "recall": R, "recall_lo": lo[1], "recall_hi": hi[1],
                            "f1": F, "f1_lo": lo[2], "f1_hi": hi[2], "normalized_recall": NR, "norm_recall_lo": lo[3], "norm_recall_hi": hi[3]})

res = pd.DataFrame(results)
res.to_csv(RES / "model_comparison.csv", index=False)
pd.DataFrame(errors).to_csv(RES / "handwritten_errors.csv", index=False)
pd.DataFrame([{"model": k, "ms_per_sentence": float(np.mean(v))} for k, v in timings.items()]).to_csv(RES / "speed.csv", index=False)
json.dump({k: {"threshold": v[0], "val_recall": v[1], "val_precision": v[2]} for k, v in thr.items()},
          open(RES / "thresholds.json", "w"), indent=1)

# feature importance (random forest, permutation-free impurity importance) + LR numeric coefficients
fi = pd.DataFrame({"feature": FEATURE_NAMES, "rf_importance": rf.feature_importances_})
fi["lr_coef"] = lr.coef_[0][-len(FEATURE_NAMES):]
fi.sort_values("rf_importance", ascending=False).to_csv(RES / "feature_importance.csv", index=False)

# save models for the app
pickle.dump({"tfidf": tfidf, "lr": lr, "rf": rf, "lrc": lrc, "dv": dv, "gb": gb, "thr": thr}, open(MODELS / "sklearn_models.pkl", "wb"))
nlp.to_disk(MODELS / "spacy_ner")

pd.set_option("display.width", 200)
show = res[res.input_type.isin(["ALL", "clean", "brand", "misspelled", "ocr_noise", "dose_attached", "colloquial", "negatives"])]
print(show.pivot_table(index=["test_set", "input_type"], columns="model", values="recall").round(3))
print(show[show.input_type == "ALL"][["model", "test_set", "precision", "recall", "recall_lo", "recall_hi", "f1", "normalized_recall"]].round(3))
print(pd.read_csv(RES / "speed.csv"))

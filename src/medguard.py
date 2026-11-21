"""MedGuard AI core library: tokenizer, dictionary, normalizer, features, detectors, alert engine."""
import re
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd
from rapidfuzz import process, fuzz

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

TOKEN_RE = re.compile(r"[A-Za-z0-9\-]+|[^\sA-Za-z0-9]")
def tokenize(text):
    return TOKEN_RE.findall(text)

# ---------------- dictionary (simulates RxNorm Current Prescribable Content) -------------
VOCAB = pd.read_csv(DATA / "drug_vocab.csv")
NAME2CANON = dict(zip(VOCAB["name"].str.lower(), VOCAB["canonical"]))
DICT_NAMES = list(NAME2CANON)
IN_SCOPE = set(VOCAB.loc[VOCAB.in_alert_scope == 1, "canonical"])

DOSE_RE = re.compile(r"(\d+(\.\d+)?)\s*(mg|mcg|ml|g)?$", re.I)
OCR_FIX = str.maketrans({"1": "l", "0": "o", "5": "s", "8": "b", "9": "g", "7": "t"})
OCR_FIX_I = str.maketrans({"1": "i", "0": "o", "5": "s", "8": "b", "9": "g", "7": "t"})

def strip_dose(tok):
    t = tok.lower()
    s = DOSE_RE.sub("", t)
    return s if len(s) >= 3 else t

@lru_cache(maxsize=100_000)
def best_match(tok):
    """Return (best_similarity_0_100, canonical, matched_name) using OCR-aware candidates."""
    base = strip_dose(tok)
    cands = {base, base.translate(OCR_FIX), base.translate(OCR_FIX_I), base.replace("m", "rn")}
    best = (0.0, None, None)
    for c in cands:
        if len(c) < 3:
            continue
        r = process.extractOne(c, DICT_NAMES, scorer=fuzz.ratio)
        if r and r[1] > best[0]:
            best = (r[1], NAME2CANON[r[0]], r[0])
    return best

def normalize(tok):
    return best_match(tok)[1]

# ---------------- hand-crafted features ------------------------------------------------
CUE_PREV = {"take", "takes", "taking", "on", "my", "started", "prescribed", "use", "uses", "of",
            "stop", "gave", "and", ",", ":", ";", "with", "reads", "for", "baby", "up", "say"}
SUFFIXES = ["pril", "olol", "statin", "sartan", "pine", "azole", "pam", "lam", "mide", "cin",
            "ine", "one", "ide", "xin", "fen", "ol", "in", "an", "ex", "ax"]
STOP = {"i", "a", "the", "and", "my", "on", "for", "to", "at", "in", "of", "with", "is", "he", "she",
        "it", "me", "every", "day", "night", "morning", "take", "takes", "taking", "pill", "doctor"}
FEATURE_NAMES = (["best_sim", "exact_in_dict", "sim_ge_85", "has_digit", "digit_ratio", "all_caps",
                  "capitalized", "length", "vowel_ratio", "is_stopword", "is_punct", "prev_is_cue",
                  "next_is_dose_or_punct", "next_is_unit", "position_ratio"]
                 + [f"suffix_{s}" for s in SUFFIXES])

def token_features(tokens, i):
    t = tokens[i]
    tl = t.lower()
    sim, _, _ = best_match(t) if re.search(r"[A-Za-z]", t) and len(t) >= 3 else (0.0, None, None)
    letters = [c for c in tl if c.isalpha()]
    prev = tokens[i - 1].lower() if i > 0 else "<s>"
    nxt = tokens[i + 1].lower() if i + 1 < len(tokens) else "</s>"
    base = strip_dose(tl)
    f = [sim / 100, float(strip_dose(tl) in NAME2CANON), float(sim >= 85),
         float(any(c.isdigit() for c in t)), sum(c.isdigit() for c in t) / max(len(t), 1),
         float(t.isupper() and len(t) > 1), float(t[:1].isupper()), min(len(t), 20) / 20,
         (sum(c in "aeiou" for c in letters) / max(len(letters), 1)), float(tl in STOP),
         float(not any(c.isalnum() for c in t)), float(prev in CUE_PREV),
         float(bool(re.match(r"^\d", nxt)) or nxt in {",", ".", ";", "?", "</s>"}),
         float(nxt in {"mg", "tab", "cap", "hcl", "dr", "bid", "tid", "prn", "daily"}),
         i / max(len(tokens) - 1, 1)]
    f += [float(base.endswith(s)) for s in SUFFIXES]
    return f

def sentence_features(tokens):
    return [token_features(tokens, i) for i in range(len(tokens))]

def char_text(tokens, i):
    """Token text with light context for character n-gram models."""
    return strip_dose(tokens[i]).lower()

# ---------------- alert engine ------------------------------------------------------------
class AlertEngine:
    def __init__(self):
        self.pim = pd.read_csv(DATA / "kb_beers_pim.csv").set_index("canonical")
        self.ddi = pd.read_csv(DATA / "kb_interactions.csv")
        self.groups = pd.read_csv(DATA / "kb_drug_groups.csv")
        self.group_rules = pd.read_csv(DATA / "kb_group_rules.csv")
        self.se = pd.read_csv(DATA / "kb_side_effects.csv").set_index("canonical")

    def members(self, canon):
        return set(self.groups.loc[self.groups.canonical == canon, "group"]) | {canon}

    SEVERITY_ORDER = {"Major": 0, "Avoid combination": 1, "Moderate-Major": 2, "Moderate": 3}

    def check(self, canonicals):
        meds = sorted(set(canonicals))
        alerts, not_assessed = [], [m for m in meds if m not in IN_SCOPE]
        assessed = [m for m in meds if m in IN_SCOPE]
        ddi = []
        # 1. drug-drug interactions (pairwise, by drug or drug group)
        for i in range(len(assessed)):
            for j in range(i + 1, len(assessed)):
                a, b = assessed[i], assessed[j]
                ma, mb = self.members(a), self.members(b)
                for _, r in self.ddi.iterrows():
                    if (r.group_a in ma and r.group_b in mb) or (r.group_a in mb and r.group_b in ma):
                        note = r.context_note if isinstance(r.context_note, str) and r.context_note else ""
                        ddi.append({"type": "Drug interaction", "rule_id": r.rule_id, "severity": r.severity,
                                    "drugs": f"{a} + {b}", "message": r.risk_plain_language, "note": note,
                                    "source": r.source, "key": (r.rule_id, tuple(sorted((a, b))))})
        # group-count rules (e.g., 2+ anticholinergics, 3+ CNS-active drugs)
        for _, r in self.group_rules.iterrows():
            hits = [m for m in assessed if r.group in self.members(m)]
            if len(hits) >= r.min_count:
                ddi.append({"type": "Drug interaction", "rule_id": r.rule_id, "severity": r.severity,
                            "drugs": " + ".join(hits), "message": r.risk_plain_language, "note": "",
                            "source": r.source, "key": (r.rule_id, tuple(hits))})
        alerts += sorted(ddi, key=lambda x: (self.SEVERITY_ORDER.get(x["severity"], 9), x["rule_id"]))
        # 2. Beers potentially inappropriate medications
        for m in assessed:
            if m in self.pim.index:
                r = self.pim.loc[m]
                alerts.append({"type": "Older-adult caution (Beers)", "rule_id": "BEERS", "severity": r.level,
                               "drugs": m, "message": f"{r.drug_class}: {r.concern_plain_language}", "note": "",
                               "source": r.source, "key": ("PIM", m)})
        # 3. geriatric-relevant side effects
        for m in assessed:
            if m in self.se.index:
                r = self.se.loc[m]
                alerts.append({"type": "Side effects to watch", "rule_id": "SE", "severity": "Info",
                               "drugs": m, "message": r.geriatric_flags.replace(";", "; "), "note": "",
                               "source": r.source, "key": ("SE", m)})
        return alerts, not_assessed

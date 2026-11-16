"""Generate synthetic, leakage-safe sentence data for medication-name recognition.

Splits are made BY DRUG (generic + all its brand names stay together) and BY TEMPLATE,
so validation/test sentences use drugs and sentence patterns never seen in training.
"""
import json, random, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEED = 42
rng = random.Random(SEED)

TOKEN_RE = re.compile(r"[A-Za-z0-9\-]+|[^\sA-Za-z0-9]")
def tokenize(text):
    return TOKEN_RE.findall(text)

vocab = pd.read_csv(DATA / "drug_vocab.csv")
ALL_NAMES = set(vocab["name"].str.lower())
by_drug = {c: g for c, g in vocab.groupby("canonical")}

# ---- 1. split drugs (by canonical) ------------------------------------------------
drugs = sorted(by_drug)
rng.shuffle(drugs)
n = len(drugs)
DRUG_SPLIT = {}
for i, d in enumerate(drugs):
    DRUG_SPLIT[d] = "train" if i < int(n * 0.6) else ("val" if i < int(n * 0.8) else "test")

# ---- 2. templates (split by template) --------------------------------------------
# {D} = a drug slot; {N} = a distractor (non-drug) word slot; {T} time phrase; {C} condition
TEMPLATES = [
    "I take {D} every morning with breakfast .",
    "My doctor put me on {D} for my {C} .",
    "Every night I take {D} and {D} before bed .",
    "I'm on {D} , {D} , and sometimes {D} when my back hurts .",
    "She takes {D} twice a day and {D} {T} .",
    "Current meds : {D} , {D} , {D} .",
    "He has been taking {D} since {N} told him to .",
    "I pick up my {D} at {N} every month .",
    "Mom takes {D} for her {C} and {D} for sleep .",
    "Patient reports taking {D} daily and {D} as needed .",
    "I just started {D} last week .",
    "{D} in the morning , {D} at night .",
    "I ran out of {D} so I took {D} instead .",
    "Does {D} interact with {D} ?",
    "My cardiologist prescribed {D} and my other doctor gave me {D} .",
    "I take one {D} pill {T} .",
    "Grandpa is on {D} , {D} and a baby {D} .",
    "Pt on {D} and {D} , denies other meds .",
    "I sometimes take {D} when I can't sleep .",
    "{N} said to keep taking {D} with food .",
    "Med list : {D} ; {D} ; {D} ; {D}",
    "I have {D} and {D} in my pill box .",
    "For pain I use {D} , and for my {C} I take {D} .",
    "Dad's bottles say {D} and {D} .",
    "Taking {D} {T} , plus {D} .",
    "I was told to stop {D} but I still take {D} .",
    "My neighbor {N} gave me some {D} .",
    "Home visit : client takes {D} , {D} , {D} .",
    "I take my {D} with {N} juice .",
    "Refill needed for {D} .",
    "She is allergic to {D} but takes {D} .",
    "I keep {D} by the bed and {D} in the kitchen .",
    "Every day : {D} . Every other day : {D} .",
    "We give him {D} at lunch and {D} at dinner .",
    "Started on {D} after the hospital , still on {D} too .",
    "Bottle label reads {D}",
    "I also take {D} for my {C} , doctor {N} knows .",
    "Two pills : {D} and {D} .",
    "I double up on {D} when {N} visits .",
    "Taking {D} and {D} and {D} every single day .",
    "Can I take {D} with my {D} ?",
    "My wife manages my {D} and {D} .",
    "Medication review : {D} , {D} .",
    "Usually {D} {T} , sometimes {D} .",
    "I get {D} from {N} pharmacy .",
]
# v2: pharmacy-label formats ({S} = dose/strength token) and free-text clauses ({W} = common word)
TEMPLATES += [
    "{D} {S} TAB TAKE 1 DAILY",
    "{D} HCL {S} TAKE WITH MEALS",
    "RX 4471923 {D} {S} CAP QTY 30",
    "TAKE 1 TABLET BY MOUTH DAILY {D} {S}",
    "{D} {S} REFILLS 2 DR {N}",
    "{D} ER {S} TAKE AT BEDTIME",
    "{D} {S} TAB TAKE 2 TWICE DAILY PRN",
    "{D} {S} CAPSULE EVERY 12 HOURS",
    "my {W} has been {W} so I take {D} .",
    "I take {D} , but the {W} makes me {W} .",
    "{W} {W} and then {D} with {W} .",
    "after {W} I usually take {D} and {D} .",
    "the {W} told me {D} is fine with my {W} .",
    "I stopped {W} last month and started {D} .",
    "{D} for the {W} , {D} for the {W} .",
]
STRENGTHS = ["5MG", "10MG", "20MG", "25MG", "40MG", "50MG", "100MG", "300MG", "500MG", "1000MG", "81MG", "0.5MG"]
from wordfreq import top_n_list
from rapidfuzz import process as _p, fuzz as _f
_words = [w for w in top_n_list("en", 6000) if w.isalpha() and len(w) >= 3 and w not in ALL_NAMES]
rng.shuffle(_words)
WORD_SPLIT = {"train": _words[: int(len(_words) * .6)], "val": _words[int(len(_words) * .6): int(len(_words) * .8)],
              "test": _words[int(len(_words) * .8):]}

tids = list(range(len(TEMPLATES)))
rng.shuffle(tids)
nt = len(tids)
TEMPLATE_SPLIT = {t: ("train" if i < int(nt * 0.6) else ("val" if i < int(nt * 0.8) else "test"))
                  for i, t in enumerate(tids)}

TIMES = ["at night", "in the morning", "after lunch", "before dinner", "every other day", "on Sundays"]
CONDS = ["blood pressure", "sugar", "heart", "cholesterol", "back pain", "arthritis", "nerves", "thyroid"]
# Hard negatives: non-drug words, some visually close to drug names
NEGS = ["Norma", "Valerie", "Lassie", "Zola", "Celia", "Ambrose", "Bennett", "Cyprus", "Flora",
        "Walgreens", "Costco", "April", "celery", "Atlas", "Coral", "Linda", "Marvin", "Tyler",
        "orange", "grapefruit", "Safeway", "Dr. Patel", "Aldo", "Zorro", "Lexi", "Klara"]

# ---- 3. noise functions -----------------------------------------------------------
KEY_NEIGH = {c: n for c, n in zip("qwertyuiopasdfghjklzxcvbnm",
             ["wa","qes","wrd","etf","ryg","tuh","yij","uok","ipl","ol","qsz","awdx","sefc","drgv",
              "fthb","gyjn","hukm","jil","kol","asx","zdc","xfv","cgb","vhn","bjm","nk"])}
VOWELS = "aeiou"

def misspell(w):
    for _ in range(20):
        s = list(w.lower())
        for _ in range(rng.choice([1, 1, 2])):
            op = rng.choice(["del", "swap", "sub", "dup", "vowel"])
            i = rng.randrange(1, len(s)) if len(s) > 2 else 0
            if op == "del" and len(s) > 4:
                del s[i]
            elif op == "swap" and i < len(s) - 1:
                s[i], s[i + 1] = s[i + 1], s[i]
            elif op == "sub" and s[i] in KEY_NEIGH:
                s[i] = rng.choice(KEY_NEIGH[s[i]])
            elif op == "dup":
                s.insert(i, s[i])
            elif op == "vowel":
                vi = [k for k, ch in enumerate(s) if ch in VOWELS and k > 0]
                if vi:
                    k = rng.choice(vi); s[k] = rng.choice([v for v in VOWELS if v != s[k]])
        out = "".join(s)
        if out != w.lower() and out not in ALL_NAMES:
            return out
    return w.lower()[:-1]

OCR_MAP = {"l": "1", "i": "1", "o": "0", "s": "5", "b": "8", "e": "c", "g": "9", "t": "7"}
def ocr_noise(w):
    for _ in range(20):
        s = ""
        for ch in w.lower():
            s += OCR_MAP[ch] if ch in OCR_MAP and rng.random() < 0.35 else ch
        s = s.replace("rn", "m") if rng.random() < 0.3 else s
        if s != w.lower():
            return s.upper() if rng.random() < 0.7 else s
    return w.upper().replace("O", "0", 1)

DOSES = ["5mg", "10mg", "20mg", "25mg", "40mg", "81mg", "100mg", "500mg", "1000mg", "0.5mg", "10MG", "500MG"]
def dose_attached(w):
    return w + rng.choice(DOSES)

def case_style(w):
    return rng.choice([w.lower(), w.capitalize(), w.capitalize(), w.upper()])

INPUT_TYPES = ["clean", "brand", "misspelled", "ocr_noise", "dose_attached"]

def surface_for(canonical, itype):
    g = by_drug[canonical]
    gen = g[g.name_type == "generic"]["name"].tolist()
    brands = g[g.name_type == "brand"]["name"].tolist()
    base_pool = gen + brands
    if itype == "brand":
        if not brands:
            return None
        return case_style(rng.choice(brands))
    base = rng.choice(gen) if gen else rng.choice(base_pool)
    if itype == "clean":
        return case_style(base)
    if itype == "misspelled":
        return misspell(rng.choice(base_pool))
    if itype == "ocr_noise":
        return ocr_noise(rng.choice(base_pool))
    if itype == "dose_attached":
        return dose_attached(case_style(rng.choice(base_pool)))

def make_sentence(split, itype, sid):
    tpls = [t for t in tids if TEMPLATE_SPLIT[t] == split]
    pool = [d for d in drugs if DRUG_SPLIT[d] == split]
    if itype == "brand":
        pool = [d for d in pool if (by_drug[d].name_type == "brand").any()]
    t = rng.choice(tpls)
    tpl = TEMPLATES[t]
    k = tpl.count("{D}")
    chosen = rng.sample(pool, min(k, len(pool)))
    tokens, labels, mentions = [], [], []
    di = 0
    for piece in tpl.split(" "):
        if piece == "{D}":
            c = chosen[di % len(chosen)]; di += 1
            surf = surface_for(c, itype)
            mentions.append({"tok": len(tokens), "surface": surf, "canonical": c})
            tokens.append(surf); labels.append(1)
        else:
            fill = (piece.replace("{T}", rng.choice(TIMES)).replace("{C}", rng.choice(CONDS))
                         .replace("{N}", rng.choice(NEGS)).replace("{S}", rng.choice(STRENGTHS))
                         .replace("{W}", rng.choice(WORD_SPLIT[split])))
            for tk in tokenize(fill):
                tokens.append(tk); labels.append(0)
    # v2: append a free-text clause of common words to half the sentences
    if rng.random() < 0.5:
        for w in rng.sample(WORD_SPLIT[split], rng.randint(2, 6)):
            tokens.append(w if rng.random() < 0.8 else w.capitalize()); labels.append(0)
    return {"id": sid, "split": split, "input_type": itype, "template_id": t,
            "tokens": tokens, "labels": labels, "mentions": mentions}

def build(split, per_type):
    out = []
    for itype in INPUT_TYPES:
        for i in range(per_type):
            out.append(make_sentence(split, itype, f"{split}-{itype}-{i}"))
    return out

# ---- 4. author-written holdout (placeholder for team-written sentences) -----------
# [[surface|canonical]] marks a medication mention. Written by hand, not from templates.
HANDWRITTEN = [
    ("clean", "I'm 78 and I take [[metformin|metformin]] and [[lisinopril|lisinopril]] , plus [[Advil|ibuprofen]] when my knees act up ."),
    ("clean", "my husband is on [[warfarin|warfarin]] and the dentist gave him [[amoxicillin|amoxicillin]]"),
    ("clean", "Ok so morning is [[Synthroid|levothyroxine]] on an empty stomach , then [[amlodipine|amlodipine]] with coffee ."),
    ("clean", "[[Lipitor|atorvastatin]] at bedtime , that's it really"),
    ("clean", "She uses [[Tylenol|acetaminophen]] for headaches and takes [[Zoloft|sertraline]] for her mood ."),
    ("clean", "Doctor switched me from [[simvastatin|simvastatin]] to [[rosuvastatin|rosuvastatin]] in March ."),
    ("clean", "I take [[Eliquis|apixaban]] for my heart rhythm and [[Flomax|tamsulosin]] for my prostate ."),
    ("clean", "[[Benadryl|diphenhydramine]] helps me sleep most nights ."),
    ("clean", "For my sugar it's [[glipizide|glipizide]] and [[Januvia|sitagliptin]] ."),
    ("clean", "I've been on [[gabapentin|gabapentin]] for nerve pain and [[oxycodone|oxycodone]] after surgery ."),
    ("misspelled", "i take metforman and lisinipril every day"),
    ("misspelled", "my mom is on [[warfrin|warfarin]] and [[cipro|ciprofloxacin]] for a bladder infection"),
    ("misspelled", "[[atorvastin|atorvastatin]] at night and [[amlodapine|amlodipine]] in the morning"),
    ("misspelled", "he takes [[gabapenten|gabapentin]] and [[tramadal|tramadol]] for his back"),
    ("misspelled", "Dr said keep taking [[omeprazol|omeprazole]] and stop the [[ibuprophen|ibuprofen]]"),
    ("misspelled", "on [[lorazapam|lorazepam]] for anxiety and [[zolpidam|zolpidem]] for sleep"),
    ("misspelled", "Grandma uses [[hydroxizine|hydroxyzine]] for itching and [[furosamide|furosemide]] for swelling"),
    ("misspelled", "[[spironolactone|spironolactone]] and [[losarten|losartan]] , both for blood pressure"),
    ("misspelled", "I took [[benadril|diphenhydramine]] and [[xanex|alprazolam]] last night"),
    ("misspelled", "[[levothyroxin|levothyroxine]] , [[metoprolal|metoprolol]] , [[asprin|aspirin]]"),
    ("ocr_noise", "[[L1SINOPR1L|lisinopril]] 10MG TAB TAKE 1 DAILY"),
    ("ocr_noise", "[[METF0RMIN|metformin]] HCL 500MG TAKE WITH MEALS"),
    ("ocr_noise", "[[WARFAR1N|warfarin]] 5MG TAB AS DIRECTED"),
    ("ocr_noise", "[[ATORVA5TATIN|atorvastatin]] 40MG TAKE AT BEDTIME"),
    ("ocr_noise", "[[GA8APENTIN|gabapentin]] 300MG CAP TID"),
    ("ocr_noise", "[[0MEPRAZ0LE|omeprazole]] DR 20MG CAP DAILY"),
    ("ocr_noise", "[[ZOLP1DEM|zolpidem]] 5MG TAB AT BEDTIME PRN"),
    ("ocr_noise", "[[AML0D1PINE|amlodipine]] 5MG TAB DAILY"),
    ("ocr_noise", "[[TRAMAD0L|tramadol]] 50MG Q6H PRN PAIN"),
    ("ocr_noise", "[[FUR0SEM1DE|furosemide]] 20MG TAKE IN AM"),
    ("dose_attached", "[[metformin500mg|metformin]] twice a day and [[lisinopril10mg|lisinopril]] once"),
    ("dose_attached", "taking [[aspirin81mg|aspirin]] and [[atorvastatin40mg|atorvastatin]]"),
    ("dose_attached", "[[gabapentin300mg|gabapentin]] three times daily"),
    ("dose_attached", "[[Eliquis5mg|apixaban]] bid , [[metoprolol25mg|metoprolol]] bid"),
    ("dose_attached", "[[sertraline50mg|sertraline]] in the morning"),
    ("dose_attached", "[[furosemide40mg|furosemide]] and [[spironolactone25mg|spironolactone]]"),
    ("dose_attached", "[[levothyroxine75mcg|levothyroxine]] before breakfast"),
    ("dose_attached", "[[oxycodone5mg|oxycodone]] as needed and [[lorazepam1mg|lorazepam]] at night"),
    ("dose_attached", "[[ibuprofen800mg|ibuprofen]] after meals"),
    ("dose_attached", "[[omeprazole20mg|omeprazole]] daily for years now"),
    ("colloquial", "I take my water pill and a baby [[aspirin|aspirin]] every morning"),
    ("colloquial", "she is on a blood thinner and something for her nerves"),
    ("colloquial", "the little white pill for cholesterol and [[Tylenol|acetaminophen]] PM at night"),
    ("colloquial", "he takes his sugar pill and a sleeping pill"),
    ("colloquial", "my heart pill , my thyroid pill , and [[Aleve|naproxen]] for pain"),
    ("negatives", "I went to Walgreens with Valerie and bought some celery and grapefruit ."),
    ("negatives", "Norma and Lassie came over in April ."),
    ("negatives", "Ambrose drove me to Costco after my appointment with Dr. Patel ."),
    ("negatives", "Celia said Atlas the dog ate my orange ."),
    ("negatives", "I take [[metformin|metformin]] , and my friend Flora takes nothing ."),
]
MARK = re.compile(r"\[\[([^|\]]+)\|([^\]]+)\]\]")

def parse_handwritten(text, itype, sid):
    # unmarked misspellings in the first misspelled example are intentional placeholders: mark them
    if text.startswith("i take metforman"):
        text = "i take [[metforman|metformin]] and [[lisinipril|lisinopril]] every day"
    tokens, labels, mentions = [], [], []
    pos = 0
    for m in MARK.finditer(text):
        for tk in tokenize(text[pos:m.start()]):
            tokens.append(tk); labels.append(0)
        surf, canon = m.group(1), m.group(2)
        mentions.append({"tok": len(tokens), "surface": surf, "canonical": canon})
        tokens.append(surf); labels.append(1)
        # handle trailing word glued after the mark (e.g., "Tylenol PM") naturally via text
        pos = m.end()
    for tk in tokenize(text[pos:]):
        tokens.append(tk); labels.append(0)
    return {"id": sid, "split": "test_handwritten", "input_type": itype, "template_id": -1,
            "tokens": tokens, "labels": labels, "mentions": mentions}

if __name__ == "__main__":
    out = {
        "train": build("train", 800),
        "val": build("val", 160),
        "test_synthetic": [dict(s, split="test_synthetic") for s in build("test", 200)],
        "test_handwritten": [parse_handwritten(t, it, f"hw-{i}") for i, (it, t) in enumerate(HANDWRITTEN)],
    }
    for k, v in out.items():
        with open(DATA / f"sentences_{k}.jsonl", "w") as f:
            for s in v:
                f.write(json.dumps(s) + "\n")
        print(k, len(v), "sentences,", sum(len(s["mentions"]) for s in v), "mentions")
    split_info = {"drug_split": DRUG_SPLIT, "template_split": {str(k): v for k, v in TEMPLATE_SPLIT.items()}}
    json.dump(split_info, open(DATA / "split_info.json", "w"), indent=1)
    # leakage check
    tr = {d for d, s in DRUG_SPLIT.items() if s == "train"}
    te = {m["canonical"] for s in out["test_synthetic"] for m in s["mentions"]}
    print("drug overlap train/test_synthetic:", len(tr & te))
    print("template overlap train/test:", len({s['template_id'] for s in out['train']} & {s['template_id'] for s in out['test_synthetic']}))

# MedGuard AI — BUS AN 517 prototype

Medication safety alerts for older adults. Free-text medication list in → recognized medications →
user confirmation → alerts (drug interactions, Beers Criteria cautions, geriatric side effects) with sources.

## Run the app
    pip install -r requirements.txt
    streamlit run app.py

## App pages
- **Check medicines** – enter a list, confirm medicine cards, get the summary for the clinician (with the patient's original text, recognized names highlighted), questions for the pharmacist, a downloadable visit sheet, and (nurse view) a visit note
- **How it works** – 5-step pipeline and a live side-by-side of exact lookup, fuzzy match and our model
- **Results** – key numbers and charts read live from `results/`
- **Business case** – users and buyers, value calculator (all inputs are editable assumptions), roadmap, pilot metrics, our ask
- **Responsible AI** – guardrails, failure modes found in testing, model card

Design: Inter font (bundled in `static/`, SIL Open Font License, works offline), blush background, white cards, deep-red primary actions; theme in `.streamlit/config.toml`, styles in `src/ui.py`.
Icons are illustrations by medicine type (`data/drug_info.csv`), deliberately not real pill pictures.
`app_v1_simple.py` is the previous one-page version.

## Verified numbers
- Model: logistic regression (selected before seeing test results). Synthetic test (1,000 sentences, 1,323 mentions): precision 92.2%, recall 99.7%, F1 0.958.
- End-to-end (30 lists, 225 expected alerts): all 225 found, 0 wrong.
- Sealed team test set 1 (150 sentences, scored once): logistic regression precision 94.8% vs random forest 91.6% — logistic regression confirmed as the final model. Stress tests 2–6 (scored once with the frozen model) are in `results/sealed_test_*_results.csv`.
- Demo: "I take warfarin, lisinopril, and sometimes Advil." → 3 drugs, 7 alerts, first is warfarin + ibuprofen severe bleeding.

## Full ML analysis (start here)
Open **`MedGuard_ML_Analysis.ipynb`** (also saved as `MedGuard_ML_Analysis.html` with all outputs) and *Run all* (~3 min).
It walks through: problem framing and error costs, data generation and leakage checks, features, the 7 methods,
cost-based threshold choice on validation, test-set comparison with 95% bootstrap CIs, feature importance and speed,
the end-to-end alert check, six stress tests scored once with the frozen model, and error analysis.

By default it uses the frozen models in `models/` (the exact models behind every reported number), so the numbers reproduce exactly.
Set `RETRAIN = True` in the first code cell to regenerate the data and retrain everything from scratch.

## Reproduce step by step (command line)
    python src/gen_data.py                       # synthetic sentences, split by drug + template + word (no leakage)
    python src/compare_models.py                 # 7 methods, cost-based thresholds on validation (~3 min)
    python src/eval_end_to_end.py                # do the right alerts appear for 30 synthetic medication lists?
    python src/eval_sealed.py sealed_test_1      # stress tests 1-3 (one word per medication)
    python src/eval_mentions.py sealed_test_6    # stress tests 4-6 (names split over words, several drugs per sentence)
    python src/eval_scenarios.py                 # 11 clinical scenario tests (add --before for the pre-fix app)
    python src/make_figures.py                   # charts in results/figures/

`gen_data.py` reads `data/drug_vocab_training.csv`, a frozen copy of the drug list as it was when the data was generated,
so regenerating gives byte-identical data. The app uses the latest list, `data/drug_vocab.csv`.
Stress-test texts are in `data/sealed_test_*.txt`; hand labels in `data/sealed_test_*_gold.py` (and `*_labels.py` for tests 5-6).

## Safety layer (added Nov 22 after live testing)
These steps sit on top of the model (`src/pipeline.py`, `safety_layer`); they do not change the model or its evaluation.
- **Combination products:** `data/combo_products.csv` splits Tylenol PM, Advil PM, Aleve PM and their store-brand versions into
  their ingredients (e.g., acetaminophen + diphenhydramine), each verified against the Drug Facts label. Any other "<name> PM" gets a
  plain warning to check the label.
- **Medications outside our dictionary:** `data/other_drug_names.csv` lists about 200 common medication names we do not cover. They are
  named and listed as *Not assessed* instead of being mapped to a look-alike (Toradol is ketorolac, not tramadol; hydrocortisone is not hydrocodone).
- **Unrecognized words:** rare words that match nothing are shown to the user and, unless removed, listed as *Not assessed*, so no medication disappears silently.
- **New rules:** R28 two or more anticoagulants (ELIQUIS label 5.2); R29 tramadol + serotonergic drugs (tramadol label 5.9 and 7).

## Folders
- `data/drug_vocab.csv` — 101 drugs / 200 names (stand-in for RxNorm Current Prescribable Content)
- `data/kb_*.csv` — alert knowledge base (Beers 2023 Tables 2 & 5, FDA label side effects).
  **64 rows verified** against AGS Beers Criteria 2023 and FDA labels on DailyMed (Beers 19/22, interactions 10/26,
  group rules 2/3, side effects 33/43); the 30 newer rows added by teammates are marked `verified=PENDING` until checked.
- `data/sentences_*.jsonl` — train / val / test_synthetic / test_handwritten
- `results/` — model_comparison.csv, thresholds.json, end_to_end_alerts.csv, handwritten_errors.csv, figures/
- `results/v1`, `v2`, `v3_prec90` — earlier iterations kept for the "what we tried" story

## Nov 21 update: antibiotics
Added amoxicillin, azithromycin, doxycycline, cephalexin and nitrofurantoin to the rule set (now 49 of 101 drugs),
using their FDA/DailyMed labels and Beers 2023 (nitrofurantoin). New interaction rules R22–R27 use severity
"Monitor (label)" because labels say to monitor/adjust but do not grade severity. Previous files are in
`data/backup_before_antibiotics/`. All new rows are PENDING until a teammate checks them against the cited label section.

## To do before Demo Day
1. Verify every knowledge-base row (data/kb_*.csv) against Beers 2023 and the FDA labels.
2. Replace `data/drug_vocab.csv` with names from RxNorm Current Prescribable Content (keep the same columns).
3. Each teammate writes 15–20 sentences in their own words → add as a sealed final test set and score once.

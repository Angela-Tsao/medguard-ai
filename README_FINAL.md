# MedGuard AI — FINAL package (2026-11-15)

Run this first: `streamlit run app.py` (after `pip install -r requirements.txt`)
Colab check: open `MedGuard_run_all.ipynb` in Colab, Runtime → Run all.

## What changed vs the 2026-11-12 prototype
- Knowledge base is now 62/62 verified (was 62/62 PENDING):
  - Beers: 19/19 YES — checked against AGS Beers Criteria 2023, J Am Geriatr Soc 2023;71:2052-2081, Tables 2, 5, 7.
  - Interactions: 8/8 YES, group rules: 2/2 YES — checked against Beers Table 5 + FDA warfarin label.
  - Side effects: 33/33 YES — checked against FDA labels on DailyMed (§6/§5).
  - Original files are kept in `data/backup_original_kb/` (named *_ORIGINAL.csv).
- Conditions are now written into the plain-language messages, so no code change was needed.
  Examples: aspirin is "avoid starting for primary prevention — secondary prevention is generally indicated";
  warfarin is "avoid starting when a DOAC is possible — long-term well-controlled users may continue";
  oxybutynin citation changed from Table 2 to Table 7.
- Two spot-checks still open before the dry run: hydroxyzine (MedlinePlus summary only) and gabapentin
  (class literature only) had no direct DailyMed §6 quote retrieved.
- For lorazepam/alprazolam/diazepam, say "drowsiness and dizziness, which raise fall risk" — a fall
  is not itself a listed side effect.

## Verified numbers (unchanged by the KB swap — re-run 2026-11-15)
- Model: logistic regression (selected before seeing test results; random forest F1 0.997 was NOT selected).
- Synthetic test (1,000 sentences, 1,323 mentions): precision 92.2%, recall 99.7%, F1 0.958; 112 false flags, 4 missed.
- End-to-end (30 lists, 212 expected alerts): logistic regression found all 212, 0 wrong.
  Fuzzy baseline: 11 wrong. Exact match: found 61.3% (missed 82).
- Demo: "I take warfarin, lisinopril, and sometimes Advil." → 3 drugs, 6 alerts,
  first is warfarin + ibuprofen severe bleeding.

## 5 demo inputs re-run after the swap (all pass, same alert counts as before)
1. metformin/lisinopril/Advil → 4 alerts
2. warfarin/lisinopril/Advil → 6 alerts
3. warfrin + cipro → 3 alerts
4. "water pill" + baby aspirin → 2 alerts (aspirin only; "water pill" not mapped)
5. zolpidem/sertraline/gabapentin/tramadol/oxybutynin → 9 alerts

## Limits (do not claim otherwise on Demo Day)
- English only; single-word medication names only; no photo/OCR.
- Drug list is a stand-in, not yet replaced with an RxNorm Current Prescribable Content export.
- Hand-written test set is small (50 sentences, 69 mentions, one author) — the sealed team-written
  test set is still to be scored once.
- No MedGuard savings figure exists — do not invent one. Use only the cost figures in
  `docs/MedGuard_business_cost_figures.md`.
- See `docs/` for the full verification notes, cost figures, and demo script + deck outline.

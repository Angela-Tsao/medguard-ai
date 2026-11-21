# MedGuard AI — BUS AN 517

Medication safety alerts for older adults. Type or paste a medication list → the trained model recognises medication names → confirm the matches → curated rules check interactions, Beers Criteria cautions and side effects, and produce a plain-language report with sources.

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Push this folder to a public GitHub repo.
2. At share.streamlit.io, click **Create app**, pick the repo, branch `main`, main file `app.py`, then **Deploy**.
3. The app needs no secrets and no extra setup.

## Verified numbers
- Model: logistic regression (selected before seeing test results). Synthetic test (1,000 sentences, 1,323 mentions): precision 92.2%, recall 99.7%, F1 0.958.
- End-to-end (30 lists, 223 expected alerts): all 223 found, 0 wrong.
- Knowledge base: 64 rows verified against AGS Beers Criteria 2023 and FDA labels on DailyMed (Beers 19/22, interactions 10/25, group rules 2/2, side effects 33/43); the 28 newer rows added by teammates are marked PENDING until checked.
- Nov 21 update: antibiotics — amoxicillin, azithromycin, doxycycline, cephalexin and nitrofurantoin added to the rule set (now 49 of 101 drugs), using their FDA/DailyMed labels and Beers 2023 (nitrofurantoin). New interaction rules R22–R27 use severity "Monitor (label)" because labels say to monitor/adjust but do not grade severity. Previous files are in `data/backup_before_antibiotics/`. All new rows are PENDING until a teammate checks them against the cited label section.
- Sealed team test set (150 sentences, scored once on 2026-11-21): logistic regression precision 94.8% vs random forest 91.6% — logistic regression confirmed as the final model.
- Design: Inter font (bundled in `static/`, SIL Open Font License, works offline), blush background, white cards, deep-red primary actions; theme in `.streamlit/config.toml`, styles in `src/ui.py`.
- Demo: "I take warfarin, lisinopril, and sometimes Advil." → 3 drugs, 7 alerts, first is warfarin + ibuprofen severe bleeding.

## Limits
English only; single-word medication names only; no photo/OCR. Prototype for education only — not medical advice. Always talk to a pharmacist or doctor before changing any medicine.

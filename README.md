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
- End-to-end (30 lists, 212 expected alerts): all 212 found, 0 wrong.
- Knowledge base: 62/62 verified (Beers 19, interactions 8, group rules 2, side effects 33) against AGS Beers Criteria 2023 and FDA labels on DailyMed.
- Demo: "I take warfarin, lisinopril, and sometimes Advil." → 3 drugs, 6 alerts, first is warfarin + ibuprofen severe bleeding.

## Limits
English only; single-word medication names only; no photo/OCR. Prototype for education only — not medical advice. Always talk to a pharmacist or doctor before changing any medicine.

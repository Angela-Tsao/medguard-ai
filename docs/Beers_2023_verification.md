# MedGuard AI — Beers Criteria 2023 verification (19 rows)

Checked 2026-11-15 against the full text of the AGS Beers Criteria® 2023
(J Am Geriatr Soc. 2023;71:2052–2081, DOI 10.1111/jgs.18372),
PMC full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC12478568/
— Table 2 (potentially inappropriate medications), Table 5 (drug–drug
interactions) and Table 7 (drugs with strong anticholinergic properties).

Prototype file checked: `MedGuard_AI_prototype.zip` →
`data/kb_beers_pim.csv` (19 rows), `data/kb_interactions.csv` (8 rows),
`data/kb_group_rules.csv` (2 rows). All 62 KB rows were PENDING before this check.

## Verdict

- **18 of 19 Beers rows are correctly listed in Table 2.** No drug needs to be removed.
- **1 source citation is wrong: oxybutynin.** It is not in Table 2. It is in
  Table 7 (strong anticholinergic drugs), where the paper notes oxybutynin
  "has the best evidence for adverse cognitive effects" among bladder
  antimuscarinics. The flag itself is defensible; the citation must change.
- **The bigger issue is missing conditions.** The app (`src/medguard.py`,
  `AlertEngine.check`) fires a Beers alert for *any* occurrence of a listed
  drug — it does not check indication, duration or dose. Seven of the 19
  flags are conditional in Beers 2023, so the app will over-flag in the demo
  unless the wording carries the condition. The corrected CSV below fixes
  this by putting the condition in the message itself, with no code change.

## Corrected file

`kb_beers_pim_VERIFIED.csv` (in this same folder) — same columns as the
prototype file, `verified` set to YES on all 19 rows, with:
- oxybutynin source corrected to Table 7;
- condition added to the plain-language message for glipizide, ibuprofen,
  naproxen, aspirin, warfarin, rivaroxaban, omeprazole, digoxin and
  amiodarone (see per-drug notes);
- diphenhydramine noted as oral use only (Table 2 lists "Diphenhydramine (oral)").

To use it: back up the original, then replace
`data/kb_beers_pim.csv` in the prototype with this file and re-run the
5 demo inputs to confirm the alerts still fire.

## Per-drug notes (Beers 2023, Table 2 unless stated)

| Drug | Verdict | What Beers actually says |
|---|---|---|
| diphenhydramine | ✓ correct | First-generation antihistamines: Avoid. Highly anticholinergic; risk of confusion, dry mouth, constipation. Note: oral only; acute severe allergy may be appropriate. |
| hydroxyzine | ✓ correct | Same class: Avoid. |
| meclizine | ✓ correct | Same class: Avoid. |
| amitriptyline | ✓ correct | Antidepressants with strong anticholinergic activity: Avoid. Highly anticholinergic, sedating, orthostatic hypotension. |
| oxybutynin | ⚠ citation wrong | **Not in Table 2.** In Table 7 (strong anticholinergic drugs) as a bladder antimuscarinic; best evidence for adverse cognitive effects. Also relevant to Table 3 (dementia/delirium). Fix the source, keep the flag. |
| lorazepam | ✓ correct | Benzodiazepines: Avoid. Cognitive impairment, delirium, falls, fractures, motor-vehicle crashes. |
| alprazolam | ✓ correct | Same class: Avoid. |
| diazepam | ✓ correct | Same class: Avoid (long-acting). |
| zolpidem | ✓ correct | Z-drugs: Avoid. Adverse events similar to benzodiazepines. |
| cyclobenzaprine | ✓ correct | Skeletal muscle relaxants: Avoid. Poorly tolerated; anticholinergic effects, sedation, fracture risk. |
| glipizide | ✓ correct, wording needs the nuance | 2023 expanded this criterion from long-acting sulfonylureas to **all** sulfonylureas: avoid as first- or second-line monotherapy/add-on unless substantial barriers to safer agents. **If one must be used, choose short-acting (e.g. glipizide) over long-acting (glyburide, glimepiride).** The prototype's "higher risk of low blood sugar" is true but hides that glipizide is the *preferred* sulfonylurea. |
| ibuprofen | ✓ correct, conditional | Non-COX-2-selective NSAIDs: avoid **chronic** use unless alternatives are not effective and the patient can take a gastroprotective agent (PPI/misoprostol). Also avoid short-term scheduled use with steroids/anticoagulants/antiplatelets on the same terms. |
| naproxen | ✓ correct, conditional | Same as ibuprofen. |
| aspirin | ✓ correct, conditional | Avoid **initiating** aspirin for **primary** prevention; consider deprescribing in older adults already taking it for primary prevention. Aspirin for **secondary** prevention is generally indicated. The app cannot tell which applies — say so in the demo. |
| warfarin | ✓ correct, conditional | Avoid **starting** warfarin as initial therapy for nonvalvular AF or VTE unless DOACs are contraindicated or there are substantial barriers. Long-term users with well-controlled INR (>70% time in range) may reasonably continue. |
| rivaroxaban | ✓ correct, conditional | Avoid for **long-term** treatment of nonvalvular AF or VTE in favour of safer anticoagulants (higher major/GI bleeding vs other DOACs, esp. apixaban). May be reasonable when once-daily dosing is needed for adherence. |
| omeprazole | ✓ correct, conditional | PPIs: avoid scheduled use **>8 weeks** unless high-risk (oral steroids/chronic NSAID), erosive esophagitis, Barrett's, pathologic hypersecretory condition, or demonstrated maintenance need. Risks: C. difficile, pneumonia, GI malignancy, bone loss, fractures. |
| digoxin | ✓ correct, conditional | Avoid as **first-line** for AF or heart failure; if used, avoid dosages **>0.125 mg/day**. Caution about stopping in long-term HFrEF users. |
| amiodarone | ✓ correct, conditional | Avoid as **first-line** for AF unless heart failure or substantial left-ventricular hypertrophy. |

## Interactions + group rules — also checked (bonus, same source)

All 8 interaction rows and both group rules are supported by Beers Table 5,
with two wording gaps worth fixing before the dry run:

- **Opioid + benzodiazepine** ✓ Avoid (overdose risk). **Opioid + gabapentinoid** ✓ Avoid (severe sedation/respiratory depression).
- **RAS inhibitor + potassium-sparing diuretic** ✓, but Table 5 limits it to
  "avoid routinely using 2+ RAS inhibitors, or a RAS inhibitor and a
  potassium-sparing diuretic, concurrently **in those with CKD Stage 3a or
  higher**". The prototype drops the CKD condition — add it to the message.
- **Warfarin + ciprofloxacin** ✓ (named in Table 5), **+ amiodarone** ✓,
  **+ trimethoprim-sulfamethoxazole** ✓. **Warfarin + clarithromycin** ✓ via
  Table 5's "Macrolides (excluding azithromycin)" — clarithromycin is a
  macrolide, but it is not named individually; keep the row, cite the class.
- **Warfarin + NSAID** ✓ as a claim, but **not in Beers Table 5** — the
  prototype correctly cites the FDA warfarin label instead. Keep that
  citation; do not re-label it as Beers.
- **CNS_ACTIVE ≥3** ✓ Table 5: avoid concurrent use of ≥3 CNS-active drugs
  (antiepileptics incl. gabapentinoids, antidepressants, antipsychotics,
  benzodiazepines, Z-drugs, opioids, skeletal muscle relaxants).
  One judgement call: **trazodone** is in the prototype's CNS_ACTIVE group,
  but Table 5 lists antidepressant classes as TCAs/SSRIs/SNRIs — trazodone
  is none of those three. Team to decide whether to keep it or drop it.
- **ANTICHOLINERGIC ≥2** ✓ Table 5: "Anticholinergic + Anticholinergic —
  Avoid; minimize the number (Table 7)". "More than one" = ≥2, so the
  threshold is right.

## NOT verified in this run

- **Side effects (33 rows, `kb_side_effects.csv`)** — still PENDING. They
  cite "FDA label (openFDA adverse_reactions)" but were not checked against
  openFDA/DailyMed in this run. That is the next verification job.
- Drug list vs RxNorm, sealed test set, deck/model card — untouched here.
- Demo Day / dry-run dates (2026-11-21 dry run, 2026-12-05 Demo Day,
  2026-12-04 deck due) are still **unconfirmed** — the proposal itself says
  to confirm on Canvas.

## Suggested demo Q&A line

> "Beers flags are conditional, not bans. Our app flags the drug and states
> the condition — for example, aspirin is flagged only as 'avoid *starting*
> for primary prevention', and warfarin only as 'avoid *starting* when a
> DOAC is possible' — because the app does not know the patient's indication,
> dose or duration. Every alert tells the user to ask a pharmacist, and we
> never suggest stopping a drug."

## Sources

- AGS Beers Criteria® 2023 full text (PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC12478568/
- DOI: 10.1111/jgs.18372 — J Am Geriatr Soc. 2023;71:2052–2081.
- Prototype files: `~/workspace/user/files/MedGuard_AI_prototype.zip`
  (`data/kb_beers_pim.csv`, `data/kb_interactions.csv`,
  `data/kb_group_rules.csv`, `src/medguard.py`).

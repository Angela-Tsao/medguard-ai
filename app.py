"""MedGuard AI - Streamlit app.   Run:  streamlit run app.py
Design: Inter font (bundled in ./static), blush background, white cards, deep-red primary actions.
Analysis logic, thresholds, rules and guardrails live in src/ and are unchanged by the UI."""
import sys, re, html, datetime
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))
from pipeline import detect, check, METHODS
from medguard import NAME2CANON, IN_SCOPE
import ui

st.set_page_config(page_title="MedGuard AI", page_icon=":material/medication:", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
RES = ROOT / "results"

EXAMPLES = {
    "Typed list": "I take metformin and lisinopril every morning, plus Advil when my knees hurt.",
    "Misspelled": "my mom is on warfrin and the doctor gave her cipro for a bladder infection",
    "Pill bottle text": "OXYC0D0NE 5MG TAB Q6H PRN and L0RAZEPAM 1MG AT BEDTIME",
    "Home visit": "Home visit: client takes Zolpidem10mg, sertraline, gabapentin 300mg, tramadol and oxybutynin.",
    "Limitation demo": "I take my water pill, a baby aspirin and some vitamin D.",
}
SUPPLEMENT_RE = re.compile(r"\b(vitamin\s*[a-z0-9]?\b|fish oil|omega-?3|supplements?|herbal\s*\w*|probiotics?|melatonin|"
                           r"turmeric|ginkgo|st\.? john'?s wort|multivitamins?)", re.I)
DISCLAIMER = ("Prototype for education only. MedGuard AI does not give medical advice, and its safety rules are a small sample "
              "that must be checked against their sources. Always talk to a pharmacist or doctor before changing any medication.")

@st.cache_data
def load_results():
    def rd(n):
        p = RES / n
        return pd.read_csv(p) if p.exists() else None
    return {"cmp": rd("model_comparison.csv"), "e2e": rd("end_to_end_alerts.csv"),
            "sealed": rd("sealed_test_1_results.csv"), "speed": rd("speed.csv")}
R = load_results()
SYN = "Synthetic test (unseen drugs + templates)"

def cmp_row(model, test=SYN, itype="ALL"):
    c = R["cmp"]
    return c[(c.model == model) & (c.test_set == test) & (c.input_type == itype)].iloc[0]

def false_flags(row):
    tp = row.recall * row.n_mentions
    return tp / row.precision - tp if row.precision > 0 else 0

def md(s):
    st.markdown(s, unsafe_allow_html=True)

# ------------------------------------------------------------------ header
icons = "".join(ui.icon_svg(c, 44) for c in ["warfarin", "metformin", "gabapentin", "lisinopril", "albuterol"])
md(f"""<div class="mg-hero"><div style="flex:1">
<div class="mg-brand" role="heading" aria-level="1">MedGuard <span>AI</span></div>
<div class="mg-tagline">Safer medications. Smarter decisions.</div>
<p class="mg-sub">Enter a medication list the way people really write it. MedGuard AI finds each medication, checks it against
older-adult safety rules, and turns the results into questions to bring to a pharmacist.</p></div>
<div class="mg-hero-icons" aria-hidden="true">{icons}</div></div>""")

tab_check, tab_how, tab_res, tab_biz, tab_rai = st.tabs([
    ":material/medication: Check Medications", ":material/account_tree: How it works", ":material/monitoring: Results",
    ":material/business_center: Business case", ":material/verified_user: Responsible AI"])

# ================================================================== TAB 1: CHECK MEDICATIONS
with tab_check:
    md(ui.disclaimer(DISCLAIMER))

    with st.container(key="mgbox_input"):
        c1, c2 = st.columns([3, 2])
        with c1:
            view = st.radio("Who is using MedGuard?", ["Older adult / family", "Home health nurse"], horizontal=True)
        with c2:
            with st.expander("Demo settings", icon=":material/tune:"):
                method = st.selectbox("Recognition method", METHODS, index=0, help="Switch to a baseline to compare live.")
        nurse = view == "Home health nurse"

        st.subheader("1. Enter medications")
        st.caption("Try an example, or type your own list.")
        cols = st.columns(len(EXAMPLES))
        for c, (label, txt) in zip(cols, EXAMPLES.items()):
            if c.button(label, width="stretch"):
                st.session_state["text_box"] = txt
        text = st.text_area("Medication list", height=110, key="text_box",
                            placeholder="e.g. I take metformin 500mg twice a day, lisinopril, and Advil when my back hurts")
        st.caption("Misspellings, brand names and text copied from a pill bottle are all fine.")
        if st.button("Check Medications", type="primary", icon=":material/search:"):
            if not text.strip():
                st.session_state.pop("detections", None)
                st.session_state["empty_warning"] = True
            else:
                st.session_state.pop("empty_warning", None)
                with st.spinner("Analyzing medications…", show_time=False):
                    st.session_state["detections"] = detect(text, method)
                st.session_state["supplements"] = sorted({m.group(0).strip().lower() for m in SUPPLEMENT_RE.finditer(text)})
                st.session_state["source_text"] = text
            st.session_state.pop("report", None)
        if st.session_state.get("empty_warning"):
            md(ui.notice("Please enter at least one medication name.", "alert", "#B45309", "#FFFBEB"))

    dets = st.session_state.get("detections")
    if dets is not None:
        with st.container(key="mgbox_confirm"):
            st.subheader("2. Confirm what we found")
            st.caption("Icons show the type of medication, not what your pills look like. Never identify a pill by its appearance.")
            src_text = st.session_state.get("source_text", "")
            found = {d["token"].lower() for d in dets}
            vague = [m.group(0) for m in re.finditer(r"\b(\w+)\s+(pill|pills|medicine|tablet)\b", src_text, re.I)
                     if m.group(1).lower() not in found and m.group(1).lower() not in {"one", "a", "the", "my", "two", "baby"}]
            if vague:
                md(ui.notice("We noticed " + ", ".join(f"“{html.escape(v)}”" for v in vague) + ". We can't tell which medication "
                             "that is from a description, so please add the name printed on the bottle below.", "search"))
            if not dets:
                md(ui.notice("No medication names found. Check the spelling or add one below."))
            confirmed = []
            grid = st.columns(3)
            for i, d in enumerate(dets):
                with grid[i % 3]:
                    if not d.get("needs_review", d["similarity"] < 80):
                        status = "checked" if d["canonical"] in IN_SCOPE else "not_assessed"
                        extra = (f'<div class="mg-src" style="margin-top:8px">Match {d["similarity"]:.0f}% · model score {d["model_score"]:.2f}</div>'
                                 if nurse else "")
                        md(ui.med_card(d["token"], d["canonical"], status, extra))
                        if st.checkbox("Include in safety check", value=True, key=f"det{i}"):
                            confirmed.append(d["canonical"])
                    else:
                        why = "looks like an everyday word" if d.get("common_word") else f"is only a {d['similarity']:.0f}% match"
                        md(ui.med_card(d["token"], None, "review",
                                       f'<div class="mg-src" style="margin-top:8px">“{html.escape(d["token"])}” {why}. '
                                       f'Closest name: {html.escape(d["canonical"])}.</div>'))
                        fix = st.text_input("Type the correct name, or leave blank to skip", key=f"fix{i}")
                        if fix.strip():
                            confirmed.append(NAME2CANON.get(fix.strip().lower(), fix.strip().lower()))
            extra = st.multiselect("Add a medication we missed", sorted(NAME2CANON), placeholder="Search medication names")
            confirmed += [NAME2CANON[x] for x in extra]
            sups = st.session_state.get("supplements", [])
            if sups:
                md(ui.notice("Supplements noticed: " + html.escape(", ".join(sups)) +
                             ". They are not in our rule set and will be listed as Not assessed.", "circle-dash", "#4B5563", "#F9FAFB"))
            if not confirmed:
                st.caption("Confirm or add at least one medication to see a safety report.")
            elif st.button("Generate safety report", type="primary", icon=":material/shield:"):
                with st.spinner("Checking interactions and older-adult safety rules…"):
                    alerts, na = check(confirmed)
                st.session_state["report"] = (alerts, na + sups)
                st.session_state["confirmed"] = sorted(set(confirmed))

    rep = st.session_state.get("report")
    if rep is not None:
        alerts, not_assessed = rep
        meds = st.session_state["confirmed"]
        groups = {t: [a for a in alerts if a["type"] == t] for t in ui.ALERT_STYLE}
        with st.container(key="mgbox_report"):
            st.subheader("3. Safety report")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Medications checked", len([m for m in meds if m in IN_SCOPE]))
            m2.metric("Interactions", len(groups["Drug interaction"]))
            m3.metric("Older-adult cautions", len(groups["Older-adult caution (Beers)"]))
            m4.metric("Not assessed", len(not_assessed))
            if not alerts:
                md(ui.notice("No alerts in our limited rule set. <b>This does not mean the combination is safe.</b>",
                             "info", "#047857", "#ECFDF5"))
            left, right = st.columns([3, 2], gap="large")
            with left:
                for t, items in groups.items():
                    if items:
                        md(ui.section_title(t, len(items)))
                        for a in items:
                            md(ui.alert_card(a))
                if not_assessed:
                    md(f'<div class="mg-sec">{ui.line_icon("circle-dash", 22, "#4B5563")}<span>Not assessed</span>'
                       f'<span class="mg-count">{len(not_assessed)}</span></div>')
                    md(f'<div class="mg-alert" style="border-left-color:#9CA3AF"><div class="mg-alert-msg">These are outside our '
                       f'current rule set, so we cannot say anything about them: <b>{html.escape(", ".join(not_assessed))}</b>.</div></div>')
            qs = []
            for a in groups["Drug interaction"]:
                qs.append(f"Is it OK for me to take {a['drugs'].replace(' + ', ' and ')} together?")
            for a in groups["Older-adult caution (Beers)"]:
                qs.append(f"Is {a['drugs']} still the best choice for me, or is there a safer option at my age?")
            for a in groups["Side effects to watch"][:3]:
                qs.append(f"Which side effects of {a['drugs']} should I call you about?")
            if not_assessed:
                qs.append("Can you check " + ", ".join(not_assessed) + " against my other medications?")
            with right:
                body = "".join(f'<div class="mg-q"><b>{n}.</b><span>{html.escape(q)}</span></div>' for n, q in enumerate(qs, 1)) \
                       or '<div class="mg-q">No questions generated.</div>'
                md(ui.panel("Questions to bring to your pharmacist", body, "message", ui.ACCENT))
                today = datetime.date.today().strftime("%b %d, %Y")
                sheet = f"""<!doctype html><html><head><meta charset="utf-8"><title>MedGuard AI - pharmacist visit sheet</title>
<style>body{{font-family:Inter,Arial,sans-serif;max-width:760px;margin:30px auto;color:#1F2937}}td,th{{border:1px solid #E5E7EB;padding:8px;text-align:left}}
table{{border-collapse:collapse;width:100%}}h1{{color:#B91C1C}}.s{{color:#6B7280;font-size:12px}}</style></head><body>
<h1>Medication list for my pharmacist</h1><p class="s">Prepared with MedGuard AI (student prototype) on {today}. Not medical advice.</p>
<h2>My medications</h2><table><tr><th>Medication</th><th>Used for</th></tr>{''.join(f'<tr><td>{html.escape(m)}</td><td>{html.escape(ui.info(m)["used_for"])}</td></tr>' for m in meds)}</table>
<h2>Questions</h2><ol>{''.join(f'<li>{html.escape(q)}</li>' for q in qs)}</ol>
<h2>Flags found</h2><ul>{''.join(f'<li><b>{html.escape(a["drugs"])}</b>: {html.escape(a["message"])} <span class="s">({html.escape(a["source"])})</span></li>' for a in alerts if a["type"] != "Side effects to watch")}</ul>
<p class="s">Please do not stop or change any medication without talking to your doctor or pharmacist.</p></body></html>"""
                st.download_button("Download pharmacist visit sheet", sheet, file_name="medguard_pharmacist_sheet.html",
                                   mime="text/html", width="stretch", icon=":material/download:")
                if nurse:
                    note = (f"Medication review ({today}). Meds reported: {', '.join(meds)}. "
                            f"Flags: {len(groups['Drug interaction'])} interaction(s) "
                            f"[{'; '.join(a['drugs'] for a in groups['Drug interaction']) or 'none'}], "
                            f"{len(groups['Older-adult caution (Beers)'])} Beers caution(s) "
                            f"[{', '.join(a['drugs'] for a in groups['Older-adult caution (Beers)']) or 'none'}]. "
                            f"Not assessed: {', '.join(not_assessed) or 'none'}. Plan: send list to prescriber/pharmacist for review.")
                    st.text_area("Visit note (copy into your charting system)", note, height=170)
            md(ui.notice("Bring this list to your pharmacist or doctor. Do not stop or change any medication on your own.",
                         "shield", ui.ACCENT, "#FEF2F2"))

    with st.expander("Medication type colors", icon=":material/palette:"):
        md('<div class="mg-legend">' + "".join(
            f'<span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="6" fill="{c}"/></svg>{html.escape(k)}</span>'
            for k, c in ui.CATEGORY_COLOR.items() if k != "Unknown") + "</div>")

# ================================================================== TAB 2: HOW IT WORKS
with tab_how:
    with st.container(key="mgbox_how"):
        st.header("How MedGuard AI works")
        md('<div class="mg-steps">' + "".join([
            ui.step_box(1, "Enter anything", "A list in everyday words, with typos, brand names or pill-bottle text."),
            ui.step_box(2, "Find medication names", "A trained model decides which words are medication names.", ml=True),
            ui.step_box(3, "Standardize", "Brand and misspelled names are matched to one generic name (Advil → ibuprofen)."),
            ui.step_box(4, "Person confirms", "The user ticks each medication. Unsure matches must be retyped."),
            ui.step_box(5, "Check & explain", "Cited rules: interactions, Beers Criteria, side effects. Plain-language report."),
        ]) + "</div>")
        md(ui.notice("<b>The model only finds names. Every alert comes from a cited rule</b>, so the AI never invents medical advice.",
                     "shield-check", "#047857", "#ECFDF5"))

    with st.container(key="mgbox_compare"):
        st.subheader("Try it: the same text, three methods")
        st.caption("This is why we needed machine learning. Edit the text and compare.")
        demo = st.text_input("Messy input", "Mom takes metforman 500mg, L1SINOPR1L 10MG TAB, a baby aspirin every morning and Benadryl at night.")
        cols = st.columns(3)
        labels = {"Exact match (baseline)": "Exact dictionary lookup", "Fuzzy match (baseline)": "Fuzzy spelling match",
                  "Logistic regression": "Our model (logistic regression)"}
        with st.spinner("Comparing methods…"):
            results = {m: detect(demo, m) for m in labels}
        for col, (m, lab) in zip(cols, labels.items()):
            with col:
                rows = "".join(
                    f'<div class="mg-found">{ui.line_icon("check" if not d.get("needs_review") else "help", 18, "#047857" if not d.get("needs_review") else "#B45309")}'
                    f'<code>{html.escape(d["token"])}</code><span>→ {html.escape(d["canonical"]) if not d.get("needs_review") else "ask the user"}</span></div>'
                    for d in results[m]) or '<div class="mg-found" style="color:#6B7280">Found nothing</div>'
                md(ui.panel(lab, rows))
        st.caption("Exact lookup misses typos and bottle text. Fuzzy matching finds them but also flags ordinary words such as "
                   "“morning”. The model learned which words really are medication names.")

    with st.container(key="mgbox_why"):
        st.subheader("Why this model")
        st.markdown("""
- We compared **7 methods** on the same data: 2 rule baselines and 5 ML models.
- Thresholds were set by **cost**: missing a medication costs 10× more than one extra item to untick, because a missed medication can hide a dangerous interaction.
- **Logistic regression** had the lowest cost on validation data, runs in under a millisecond, and is easy to explain.
""")

# ================================================================== TAB 3: RESULTS
with tab_res:
    if R["cmp"] is not None:
        with st.container(key="mgbox_res1"):
            st.header("Does it work?")
            ex, fz, lr = cmp_row("Exact match (baseline)"), cmp_row("Fuzzy match (baseline)"), cmp_row("Logistic regression")
            e2e = R["e2e"]; lr_e = e2e[(e2e.method == "Logistic regression") & (e2e.setting == "auto-confirm")].iloc[0]
            fz_e = e2e[(e2e.method == "Fuzzy match (baseline)") & (e2e.setting == "auto-confirm")].iloc[0]
            reduction = 1 - false_flags(lr) / false_flags(fz)
            md('<div class="mg-tiles">' + "".join([
                ui.stat_tile(f"{lr.recall:.1%}", "medication names found", f"in messy text (exact lookup: {ex.recall:.0%})"),
                ui.stat_tile(f"−{reduction:.0%}", "false flags", f"vs fuzzy matching ({false_flags(lr):.0f} vs {false_flags(fz):.0f})"),
                ui.stat_tile(f"{int(lr_e.gold_alerts * lr_e.alert_recall)}/{int(lr_e.gold_alerts)}", "safety alerts found",
                             f"30 test lists · {int(lr_e.false_alerts)} wrong alerts (fuzzy: {int(fz_e.false_alerts)})"),
                ui.stat_tile("<1 ms", "per sentence", "fast enough for a live demo"),
            ]) + "</div>")
            st.caption("Synthetic test set: 1,000 sentences with medications the model never saw in training.")
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("**Where exact lookup fails**")
                st.image(str(RES / "figures" / "fig1_recall_by_input_type.png"))
            with c2:
                st.markdown("**All 7 methods, with 95% confidence intervals**")
                st.image(str(RES / "figures" / "fig2_precision_recall_ci.png"))
    if R["sealed"] is not None:
        with st.container(key="mgbox_res2"):
            st.subheader("Team-written test (150 sentences, scored once)")
            s = R["sealed"][["method", "found_and_mapped_correctly", "precision", "ordinary_word_to_review", "oov_mentions", "oov_missed", "wrong_alerts"]].copy()
            s.columns = ["Method", "Known medications found", "Precision", "Everyday words flagged", "Unknown medications", "Unknown not shown", "Wrong alerts"]
            s["Known medications found"] = s["Known medications found"].map("{:.1%}".format); s["Precision"] = s["Precision"].map("{:.1%}".format)
            st.dataframe(s, hide_index=True, width="stretch")
            st.markdown("""**What we learned:**
- On correctly typed text, simple lookup is already enough; the model's value shows up with typos and bottle text.
- The biggest real gap is **coverage**: 41% of medications people wrote are not in our 101-medication list yet. Loading the full RxNorm list is the next step.
- Look-alike names (Toradol vs tramadol) can be matched to the wrong drug. We plan a stricter match cutoff, tuned on validation data.""")

# ================================================================== TAB 4: BUSINESS
with tab_biz:
    with st.container(key="mgbox_biz1"):
        st.header("Business case")
        c1, c2, c3 = st.columns(3)
        for col, t, ic, b in [
            (c1, "The problem", "alert", "Older adults often take many medications from several prescribers. Each prescriber may see only part of the list, so risky combinations can slip through."),
            (c2, "Why now", "info", "Safety rules exist (AGS Beers Criteria, FDA labels) but are written for clinicians. People write their lists in messy, everyday language."),
            (c3, "Our answer", "shield-check", "Accept the list as people actually write it, find every medication, and turn cited rules into plain-language questions for the pharmacist."),
        ]:
            col.markdown(ui.panel(t, html.escape(b), ic, ui.ACCENT), unsafe_allow_html=True)
        st.subheader("Who uses it, who pays")
        st.dataframe(pd.DataFrame([
            ["Older adult / family caregiver", "Prepares for a pharmacy or doctor visit", "Free consumer app", "A clear list of what to ask"],
            ["Home health nurse", "Reviews bottles during a home visit", "Home health agency (per-nurse subscription)", "Faster review, flags to send to the prescriber"],
            ["Pharmacist", "Receives the visit sheet", "Partner channel", "Better-prepared patients, fewer missed medications"],
        ], columns=["User", "When they use it", "Who pays (hypothesis)", "What they get"]), hide_index=True, width="stretch")

    with st.container(key="mgbox_biz2"):
        st.subheader("Value calculator for a home health agency")
        md(f'<div class="mg-assume">{ui.line_icon("alert", 18, "#B45309")}<span>Every input below is an <b>example assumption you can change</b>, '
           'not data we measured. Replace each one with a cited figure or a number from a pilot agency before presenting it as fact.</span></div>')
        a1, a2, a3 = st.columns(3)
        nurses = a1.number_input("Nurses at the agency", 1, 5000, 20)
        visits = a2.number_input("Home visits per nurse per week", 1, 80, 25)
        weeks = a3.number_input("Working weeks per year", 1, 52, 48)
        b1, b2, b3 = st.columns(3)
        minutes = b1.number_input("Minutes on medication review per visit (today)", 1, 120, 15)
        saved = b2.slider("Share of that time MedGuard saves", 0, 100, 30, format="%d%%")
        rate = b3.number_input("Nurse cost per hour (USD, with benefits)", 10, 300, 55)
        price = st.slider("Price per nurse per month (USD) — pricing hypothesis", 0, 200, 30)
        hours = nurses * visits * weeks * minutes * saved / 100 / 60
        value = hours * rate; cost = nurses * price * 12
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Nurse hours freed per year", f"{hours:,.0f}")
        k2.metric("Value of that time", f"${value:,.0f}")
        k3.metric("Agency cost per year", f"${cost:,.0f}")
        k4.metric("Value ÷ cost", f"{value / cost:.1f}×" if cost else "—")
        st.caption(f"Formula: {nurses} nurses × {visits} visits × {weeks} weeks × {minutes} min × {saved}% ÷ 60 = hours freed; × ${rate}/h = value.")

    with st.container(key="mgbox_biz3"):
        st.subheader("Path to a real product")
        st.dataframe(pd.DataFrame([
            ["Now (class prototype)", "101 medications, 44 with rules; synthetic + team test data", "Student time"],
            ["Pilot (3 months)", "Full RxNorm name list, every rule verified by a pharmacist, 1 home health agency", "Pharmacist review hours, hosting"],
            ["Version 1", "Licensed interaction database, bottle-photo input, HIPAA-ready hosting", "Data license, compliance, security review"],
            ["Version 2", "Connect to agency records (FHIR) so lists are pre-filled", "Integration work per customer"],
        ], columns=["Stage", "What is added", "Main cost driver"]), hide_index=True, width="stretch")
        c1, c2 = st.columns(2)
        with c1:
            md(ui.panel("How we would measure a pilot",
                        "• Minutes per medication review, before vs after<br>• Share of lists needing manual correction<br>"
                        "• Share of flags the pharmacist agreed were worth raising<br>• Share of patients who asked their pharmacist a question",
                        "check", ui.ACCENT))
        with c2:
            md(ui.panel("What makes us different",
                        "Existing interaction checkers expect clean drug names typed one at a time and are written for clinicians. "
                        "MedGuard AI accepts messy, whole-list input, focuses on older adults, and ends with questions for a pharmacist "
                        "instead of advice.", "info", ui.ACCENT))
        st.subheader("Our ask")
        st.markdown("One home health agency for a 3-month pilot, and one pharmacist to review every safety rule.")

# ================================================================== TAB 5: RESPONSIBLE AI
with tab_rai:
    with st.container(key="mgbox_rai1"):
        st.header("Responsible AI")
        c1, c2 = st.columns(2)
        with c1:
            md(ui.panel("What MedGuard AI does", "Finds medication names, matches them to one standard name, and shows cited "
                        "safety information in plain language.", "check", "#047857"))
        with c2:
            md(ui.panel("What it never does", "Recommend starting, stopping or changing a medication or dose; diagnose; or say "
                        "a combination is safe because no alert appeared.", "x", ui.ACCENT))
    with st.container(key="mgbox_rai2"):
        st.subheader("Guardrails built into the app")
        st.dataframe(pd.DataFrame([
            ["Person confirms every medication", "Nothing is checked until the user ticks it"],
            ["Unsure matches are never guessed", "Matches below 80% and everyday words (e.g., “diabetes”) must be confirmed or retyped"],
            ["“Not assessed” instead of silence", "Medications and supplements outside the rule set are listed, never shown as safe"],
            ["Descriptions are caught", "“my water pill” prompts the user to add the name on the bottle"],
            ["Every alert has a source", "Beers Criteria 2023 or the FDA label section it came from"],
            ["Severity is labeled, not just colored", "Each alert shows a text label and icon shape, so it is readable without color"],
            ["Icons are illustrations", "They show the medication type, not the pill's real look, so no one identifies a pill by sight"],
        ], columns=["Guardrail", "How it works"]), hide_index=True, width="stretch")
        st.subheader("Failure modes we found in testing")
        st.dataframe(pd.DataFrame([
            ["Look-alike names", "Toradol → tramadol, Lovastatin → atorvastatin (team test)", "Full RxNorm list; stricter cutoff"],
            ["Medication not in our list", "41% of names in the team test (e.g., Paxlovid, Sudafed)", "Full RxNorm list; show as Not assessed"],
            ["Description instead of name", "“my water pill”", "Prompt for the bottle name"],
            ["Heavily garbled bottle text", "“bcrtim” (Bactrim)", "Sent to user review"],
        ], columns=["Failure", "Example", "Mitigation"]), hide_index=True, width="stretch")
    with st.container(key="mgbox_rai3"):
        st.subheader("Model card (summary)")
        st.dataframe(pd.DataFrame([
            ["Intended use", "Support medication reviews by older adults, caregivers and home health nurses"],
            ["Not intended for", "Diagnosis, dosing, or replacing a pharmacist or doctor"],
            ["Model", "Logistic regression on character patterns + dictionary similarity; threshold set by cost (miss = 10× false flag)"],
            ["Training data", "Synthetic sentences; split by drug, template and word to prevent leakage"],
            ["Evaluation", "Synthetic test, hand-written set, 150-sentence team test scored once, 30-list end-to-end alert test"],
            ["Known limits", "English only; 101-medication list; rules pending pharmacist verification; single-word names"],
            ["Privacy", "No real patient data; nothing is stored after the session"],
        ], columns=["Item", "Details"]), hide_index=True, width="stretch")

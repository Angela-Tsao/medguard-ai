"""MedGuard AI - Streamlit app.   Run:  streamlit run app.py
Design: Inter font (bundled in ./static), blush background, white cards, deep-red primary actions.
Analysis logic, thresholds, rules and guardrails live in src/ and are unchanged by the UI."""
import sys, re, html, datetime
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))
from pipeline import detect, check, METHODS, safety_layer
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
DISCLAIMER = ("MedGuard AI helps you share an accurate medication list with your doctor or pharmacist. It is not a tool for "
              "making medication decisions: it does not tell you whether a medication is safe for you, and every flag must be reviewed "
              "by a doctor or pharmacist. Do not start, stop or change any medication based on this app. "
              "Student prototype; safety rules are a sample pending verification.")
POSITIONING = ("A communication bridge between patients and clinicians: it turns the list a patient writes into a clear, "
               "standardized list so the doctor or pharmacist knows what the patient is actually taking, and flags items "
               "for the clinician to review.")

@st.cache_data
def load_results():
    def rd(n):
        p = RES / n
        return pd.read_csv(p) if p.exists() else None
    return {"cmp": rd("model_comparison.csv"), "e2e": rd("end_to_end_alerts.csv"),
            "sealed": rd("sealed_test_1_results.csv"), "sealed2": rd("sealed_test_2_results.csv"), "speed": rd("speed.csv")}
R = load_results()
SYN = "Synthetic test (unseen drugs + templates)"

def cmp_row(model, test=SYN, itype="ALL"):
    c = R["cmp"]
    return c[(c.model == model) & (c.test_set == test) & (c.input_type == itype)].iloc[0]

def false_flags(row):
    tp = row.recall * row.n_mentions
    return tp / row.precision - tp if row.precision > 0 else 0

def highlight_original(text, dets):
    """Patient's own words with recognized names marked: green = recognized, amber = needs confirmation."""
    marks = {}
    for d in dets or []:
        marks[d["token"]] = "rev" if d.get("needs_review", d["similarity"] < 80) else "ok"
    if not marks:
        return html.escape(text)
    pat = re.compile(r"(?<![A-Za-z0-9-])(" + "|".join(re.escape(t) for t in sorted(marks, key=len, reverse=True)) + r")(?![A-Za-z0-9-])")
    out, last = [], 0
    for m in pat.finditer(text):
        out.append(html.escape(text[last:m.start()]))
        cls = "mg-hl-ok" if marks[m.group(1)] == "ok" else "mg-hl-rev"
        out.append(f'<mark class="{cls}">{html.escape(m.group(1))}</mark>')
        last = m.end()
    out.append(html.escape(text[last:]))
    return "".join(out).replace("\n", "<br>")

def md(s):
    st.markdown(s, unsafe_allow_html=True)

# ------------------------------------------------------------------ header
icons = "".join(ui.icon_svg(c, 44) for c in ["warfarin", "metformin", "gabapentin", "lisinopril", "albuterol"])
md(f"""<div class="mg-hero"><div style="flex:1">
<div class="mg-brand" role="heading" aria-level="1">MedGuard <span>AI</span></div>
<div class="mg-tagline">Safer medications. Smarter decisions.</div>
<p class="mg-sub">A bridge between patients and their doctors. Patients write down what they take, in their own words; MedGuard AI
turns it into a clear medication list for the doctor or pharmacist, with items flagged for <b>clinician review</b>.
It does not make medication decisions for patients.</p></div>
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
            view = st.radio("Who is using MedGuard?", ["Patient / family (preparing for a visit)", "Clinician (doctor, pharmacist, nurse)"], horizontal=True)
        with c2:
            with st.expander("Demo settings", icon=":material/tune:"):
                method = st.selectbox("Recognition method", METHODS, index=0, help="Switch to a baseline to compare live.")
        nurse = view.startswith("Clinician")

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
                    dets0, unrec, pm_unknown = safety_layer(text, detect(text, method))
                    st.session_state["detections"] = dets0
                    st.session_state["unrecognized"] = unrec
                    st.session_state["pm_unknown"] = pm_unknown
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
                        if d.get("combo"):
                            extra += f'<div class="mg-src" style="margin-top:8px">Combination product: {html.escape(d["combo"])}</div>'
                        if d.get("outside_list"):
                            extra += ('<div class="mg-src" style="margin-top:8px">Known medication, but not in our rule set: it will be listed '
                                      'as <b>Not assessed</b> for your clinician.'
                                      + (f' (Not the same as {html.escape(d["lookalike"])}.)' if d.get("lookalike") else "") + '</div>')
                        md(ui.med_card(d["token"], d["canonical"], status, extra))
                        if st.checkbox("Include in safety check", value=True, key=f"det{i}"):
                            confirmed.append(d["canonical"])
                    else:
                        why = "looks like an everyday word" if d.get("common_word") else f"is only a {d['similarity']:.0f}% match"
                        if d.get("outside_list"):
                            why += " to a medication outside our rule set"
                        md(ui.med_card(d["token"], None, "review",
                                       f'<div class="mg-src" style="margin-top:8px">“{html.escape(d["token"])}” {why}. '
                                       f'Closest name: {html.escape(d["canonical"])}.</div>'))
                        fix = st.text_input("Type the correct name, or leave blank to skip", key=f"fix{i}")
                        if fix.strip():
                            confirmed.append(NAME2CANON.get(fix.strip().lower(), fix.strip().lower()))
            extra = st.multiselect("Add a medication we missed", sorted(NAME2CANON), placeholder="Search medication names")
            confirmed += [NAME2CANON[x] for x in extra]
            pm_unknown = st.session_state.get("pm_unknown", [])
            if pm_unknown:
                md(ui.notice("<b>" + html.escape(", ".join(pm_unknown)) + "</b> may be a combination product. “PM” products usually also "
                             "contain a sleep aid such as diphenhydramine, which the Beers Criteria advise older adults to avoid. We only "
                             "recognized part of it: please check the label and add every ingredient below.", "alert", "#B45309", "#FFFBEB"))
            unrec = st.session_state.get("unrecognized", [])
            kept_unrec = []
            if unrec:
                md(ui.notice("We could not identify: <b>" + html.escape(", ".join(unrec)) + "</b>. If any of these is a medication, "
                             "it has <b>not</b> been checked. Kept words are listed as <b>Not assessed</b> so your clinician sees them.",
                             "search", "#B45309", "#FFFBEB"))
                kept_unrec = st.multiselect("Unrecognized words to list as Not assessed (remove any that are not medications)",
                                            unrec, default=unrec)
            sups = st.session_state.get("supplements", [])
            if sups:
                md(ui.notice("Supplements noticed: " + html.escape(", ".join(sups)) +
                             ". They are not in our rule set and will be listed as Not assessed.", "circle-dash", "#4B5563", "#F9FAFB"))
            if not confirmed and not kept_unrec:
                st.caption("Confirm or add at least one medication to see a safety report.")
            elif st.button("Generate safety report", type="primary", icon=":material/shield:"):
                with st.spinner("Checking interactions and older-adult safety rules…"):
                    alerts, na = check(confirmed)
                st.session_state["report"] = (alerts, na + sups + [f"{w} (unrecognized)" for w in kept_unrec])
                st.session_state["confirmed"] = sorted(set(confirmed))

    rep = st.session_state.get("report")
    if rep is not None:
        alerts, not_assessed = rep
        meds = st.session_state["confirmed"]
        groups = {t: [a for a in alerts if a["type"] == t] for t in ui.ALERT_STYLE}
        with st.container(key="mgbox_report"):
            st.subheader("3. Medication summary for your clinician" if not nurse else "3. Medication summary and flags for review")
            md(ui.notice("<b>For your doctor or pharmacist to review.</b> These flags come from published rules and are "
                         "<b>not a judgment about your treatment</b>. Your doctor may have good reasons for your current medications. "
                         "Do not start, stop or change anything on your own.", "shield", ui.ACCENT, "#FEF2F2"))
            src_text = st.session_state.get("source_text", "")
            if src_text:
                md(ui.panel("What the patient wrote, in their own words",
                            f'<div class="mg-orig">{highlight_original(src_text, st.session_state.get("detections"))}</div>'
                            '<div class="mg-src" style="margin-top:10px"><mark class="mg-hl-ok">green</mark> = recognized · '
                            '<mark class="mg-hl-rev">amber</mark> = needed confirmation · <b>anything not highlighted was not recognized.</b> '
                            'MedGuard AI only knows 101 medications and can miss names it has never seen, abbreviations, or names split by a space. '
                            'Please read the original text so that no medication is overlooked.</div>',
                            "file-text", "#4B5563"))
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
                md(ui.panel("Questions to ask your doctor or pharmacist", body, "message", ui.ACCENT))
                today = datetime.date.today().strftime("%b %d, %Y")
                sheet = f"""<!doctype html><html><head><meta charset="utf-8"><title>MedGuard AI - pharmacist visit sheet</title>
<style>body{{font-family:Inter,Arial,sans-serif;max-width:760px;margin:30px auto;color:#1F2937}}td,th{{border:1px solid #E5E7EB;padding:8px;text-align:left}}
table{{border-collapse:collapse;width:100%}}h1{{color:#B91C1C}}.s{{color:#6B7280;font-size:12px}}</style></head><body>
<h1>My current medications</h1><p class="s">Prepared by the patient with MedGuard AI (student prototype) on {today}, to share with my doctor or pharmacist.
This is not medical advice. Flags below are for clinician review only.</p>
<h2>In my own words</h2><p style="background:#F9FAFB;border:1px solid #E5E7EB;padding:10px;border-radius:8px">{html.escape(st.session_state.get("source_text", "")).replace(chr(10), "<br>")}</p>
<p class="s">This is exactly what I typed. The list below was generated from it by a computer program and may be missing medications.</p>
<h2>My medications (as recognized)</h2><table><tr><th>Medication</th><th>Used for</th></tr>{''.join(f'<tr><td>{html.escape(m)}</td><td>{html.escape(ui.info(m)["used_for"])}</td></tr>' for m in meds)}</table>
<h2>Questions</h2><ol>{''.join(f'<li>{html.escape(q)}</li>' for q in qs)}</ol>
<h2>Flags for clinician review</h2><ul>{''.join(f'<li><b>{html.escape(a["drugs"])}</b>: {html.escape(a["message"])} <span class="s">({html.escape(a["source"])})</span></li>' for a in alerts if a["type"] != "Side effects to watch")}</ul>
<p class="s">Please do not stop or change any medication without talking to your doctor or pharmacist.</p></body></html>"""
                st.download_button("Download list to share with my doctor", sheet, file_name="medguard_medication_list.html",
                                   mime="text/html", width="stretch", icon=":material/download:")
                if nurse:
                    note = (f"Medication review ({today}). Meds reported: {', '.join(meds)}. "
                            f"Flags: {len(groups['Drug interaction'])} interaction(s) "
                            f"[{'; '.join(a['drugs'] for a in groups['Drug interaction']) or 'none'}], "
                            f"{len(groups['Older-adult caution (Beers)'])} Beers caution(s) "
                            f"[{', '.join(a['drugs'] for a in groups['Older-adult caution (Beers)']) or 'none'}]. "
                            f"Not assessed: {', '.join(not_assessed) or 'none'}. "
                            f"Patient's original text: \"{st.session_state.get('source_text', '').strip()}\". Flags generated by MedGuard AI (decision support) for clinician review; no changes made by patient.")
                    st.text_area("Visit note (copy into your charting system)", note, height=170)
            md(ui.notice("Share this list with your doctor or pharmacist at your next visit. Do not start, stop or change any medication on your own.",
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
            ui.step_box(5, "Flag for the clinician", "Cited rules flag interactions, Beers cautions and side effects for a doctor or pharmacist to review."),
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
    if R.get("sealed2") is not None:
        with st.container(key="mgbox_res3"):
            st.subheader("Team test 2: same sentences rewritten with typos and doses (scored once)")
            s2 = R["sealed2"][["method", "found_and_mapped_correctly", "misspelled_found_correctly", "precision", "ordinary_word_to_review", "alerts_found", "alerts_expected", "wrong_alerts"]].copy()
            s2["Alerts found"] = s2.alerts_found.astype(int).astype(str) + " / " + s2.alerts_expected.astype(int).astype(str)
            s2 = s2.drop(columns=["alerts_found", "alerts_expected"])
            s2.columns = ["Method", "Known medications found", "Misspelled found (12)", "Precision", "Everyday words flagged", "Wrong alerts", "Alerts found"]
            for c in ["Known medications found", "Misspelled found (12)", "Precision"]:
                s2[c] = s2[c].map("{:.1%}".format)
            st.dataframe(s2, hide_index=True, width="stretch")
            st.markdown("""**Why the scores are still high:** every misspelling in this set is a single-letter slip (similarity 89% or more),
which dictionary similarity solves easily, and all 150 sentences follow the same \"I take …\" pattern written inside the team.
Counting medications outside our list, overall recall is only about 70%. The next test uses 10–20 lists written by people outside the team.""")

# ================================================================== TAB 4: BUSINESS
with tab_biz:
    with st.container(key="mgbox_biz1"):
        st.header("Business case")
        c1, c2, c3 = st.columns(3)
        for col, t, ic, b in [
            (c1, "The problem", "alert", "Older adults often take many medications from several prescribers. Doctors often do not know everything a patient is actually taking, so risky combinations can slip through."),
            (c2, "Why now", "info", "Safety rules exist (AGS Beers Criteria, FDA labels) but are written for clinicians. People write their lists in messy, everyday language."),
            (c3, "Our answer", "shield-check", "A bridge between patient and clinician: the patient writes the list in their own words; the clinician receives a clear, standardized list with flags to review. Decisions stay with the clinician."),
        ]:
            col.markdown(ui.panel(t, html.escape(b), ic, ui.ACCENT), unsafe_allow_html=True)
        st.subheader("Who uses it, who pays")
        st.dataframe(pd.DataFrame([
            ["Patient / family caregiver", "Writes down what they take before a visit", "Free", "An easy way to tell the doctor everything they take"],
            ["Doctor or pharmacist", "Reviews the list and the flags at the visit", "Clinic or pharmacy (hypothesis)", "A complete, standardized list; flags to review; less time reconciling medications"],
            ["Home health nurse", "Collects the list during a home visit and sends it to the prescriber", "Home health agency (hypothesis)", "Faster medication review; a ready visit note"],
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
            ["Now (class prototype)", "101 medications, 49 with rules; synthetic + team test data", "Student time"],
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
        st.subheader("Positioning")
        md(ui.notice("<b>MedGuard AI is decision support for clinicians, not a decision tool for patients.</b> " + html.escape(POSITIONING), "shield-check", "#047857", "#ECFDF5"))
        st.subheader("Our ask")
        st.markdown("One home health agency for a 3-month pilot, and one pharmacist to review every safety rule.")

# ================================================================== TAB 5: RESPONSIBLE AI
with tab_rai:
    with st.container(key="mgbox_rai1"):
        st.header("Responsible AI")
        c1, c2 = st.columns(2)
        with c1:
            md(ui.panel("What MedGuard AI does", "Acts as a bridge between patient and clinician: finds medication names in what the patient "
                        "wrote, standardizes them, and flags cited safety items <b>for a doctor or pharmacist to review</b>.", "check", "#047857"))
        with c2:
            md(ui.panel("What it never does", "Let a patient make medication decisions on their own; recommend starting, stopping or changing "
                        "a medication or dose; diagnose; or say a combination is safe because no alert appeared.", "x", ui.ACCENT))
    with st.container(key="mgbox_rai2"):
        st.subheader("Guardrails built into the app")
        st.table(pd.DataFrame([
            ["Person confirms every medication", "Nothing is checked until the user ticks it (human-in-the-loop, Week 5)"],
            ["Clinician makes every decision", "Flags are labeled for doctor or pharmacist review; the app never tells a patient what to do"],
            ["Unsure matches are never guessed", "Matches below 80% and everyday words (e.g., “diabetes”) must be confirmed or retyped"],
            ["“Not assessed” instead of silence", "Medications and supplements outside the rule set are listed, never shown as safe"],
            ["Descriptions are caught", "“my water pill” prompts the user to add the name on the bottle"],
            ["Every alert has a source", "Beers Criteria 2023 or the FDA label section it came from"],
            ["Severity is labeled, not just colored", "Each alert shows a text label and icon shape, so it is readable without color"],
            ["Icons are illustrations", "They show the medication type, not the pill's real look, so no one identifies a pill by sight"],
        ], columns=["Guardrail", "How it works"]).set_index("Guardrail"))
        st.subheader("Failure modes we found in testing")
        st.table(pd.DataFrame([
            ["Look-alike names", "Toradol → tramadol, Lovastatin → atorvastatin (team test)", "Full RxNorm list; stricter cutoff"],
            ["Medication not in our list", "41% of names in the team test (e.g., Paxlovid, Sudafed)", "Full RxNorm list; show as Not assessed"],
            ["Description instead of name", "“my water pill”", "Prompt for the bottle name"],
            ["Heavily garbled bottle text", "“bcrtim” (Bactrim)", "Sent to user review"],
        ], columns=["Failure", "Example", "Mitigation"]).set_index("Failure"))
    with st.container(key="mgbox_rai3"):
        st.subheader("Model card (summary)")
        st.table(pd.DataFrame([
            ["Intended use", "Decision support for clinicians. Helps patients and caregivers share an accurate medication list with their doctor or pharmacist, and flags items for clinician review."],
            ["Required human check", "Every flag must be reviewed by a pharmacist or clinician before any action. The patient confirms the list; the clinician makes all decisions."],
            ["Not intended for", "Patients making medication decisions on their own; diagnosis; dosing; replacing a pharmacist or doctor"],
            ["Model", "Logistic regression on character patterns + dictionary similarity; threshold set by cost (miss = 10× false flag)"],
            ["Training data", "Synthetic sentences; split by drug, template and word to prevent leakage"],
            ["Evaluation", "Synthetic test, hand-written set, two 150-sentence team tests (each scored once), 30-list end-to-end alert test. Next: 10–20 lists written by people outside the team"],
            ["Known limits", "English only; 101-medication list; rules pending pharmacist verification; single-word names"],
            ["Privacy", "No real patient data; nothing is stored after the session"],
        ], columns=["Item", "Details"]).set_index("Item"))

"""MedGuard AI - Streamlit prototype.  Run:  streamlit run app.py"""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
from pipeline import detect, check, METHODS
from medguard import NAME2CANON, IN_SCOPE

st.set_page_config(page_title="MedGuard AI", page_icon="💊", layout="centered")

EXAMPLES = {
    "Typed list": "I take metformin and lisinopril every morning, plus Advil when my knees hurt.",
    "Misspelled": "my mom is on warfrin and the doctor gave her cipro for a bladder infection",
    "Pill bottle text": "OXYC0D0NE 5MG TAB Q6H PRN and L0RAZEPAM 1MG AT BEDTIME",
    "Home visit (nurse)": "Home visit: client takes Zolpidem10mg, sertraline, gabapentin 300mg, tramadol and oxybutynin.",
    "Limitation demo": "I take my water pill, a baby aspirin and some vitamins.",
}
REVIEW_SIM = 80  # matches below this similarity are never auto-mapped to a drug

st.title("💊 MedGuard AI")
st.caption("Medication safety alerts for older adults · BUS AN 517 prototype")
st.warning("Prototype for education only. It does not give medical advice. The safety rules are a small sample "
           "and must be checked against their sources before use. Always talk to a pharmacist or doctor "
           "before changing any medicine.", icon="⚠️")

view = st.radio("Who is using this?", ["Older adult / family", "Home health nurse"], horizontal=True)
nurse = view == "Home health nurse"

with st.expander("Settings (for the demo)"):
    method = st.selectbox("Recognition method", METHODS, index=0,
                          help="Compare the trained model with the two baselines live.")

st.subheader("1. Enter medications")
cols = st.columns(len(EXAMPLES))
for c, (label, txt) in zip(cols, EXAMPLES.items()):
    if c.button(label, use_container_width=True):
        st.session_state["text_box"] = txt
text = st.text_area("Type or paste the medication list in any form", height=110, key="text_box")

if st.button("Find medicines", type="primary"):
    st.session_state["detections"] = detect(text, method)
    st.session_state.pop("report", None)

dets = st.session_state.get("detections")
if dets is not None:
    st.subheader("2. Confirm what we found")
    if not dets:
        st.info("No medication names found. Check the spelling or add one below.")
    # Guardrail: descriptions like "water pill" cannot be mapped to a specific drug
    import re as _re
    found = {d["token"].lower() for d in dets}
    vague = [m.group(0) for m in _re.finditer(r"\b(\w+)\s+(pill|pills|medicine|tablet)\b", text, _re.I)
             if m.group(1).lower() not in found and m.group(1).lower() not in {"one", "a", "the", "my", "two"}]
    if vague:
        st.warning("We noticed " + ", ".join(f"'{v}'" for v in vague) + ". We can't tell which medicine that is "
                   "from a description. Please add the name printed on the bottle below.", icon="🔎")
    confirmed = []
    for i, d in enumerate(dets):
        if d["similarity"] >= REVIEW_SIM:
            label = f"**{d['token']}** → {d['canonical']}"
            if nurse:
                label += f"  ·  match {d['similarity']:.0f}% · model score {d['model_score']:.2f}"
            if st.checkbox(label, value=True, key=f"det{i}"):
                confirmed.append(d["canonical"])
        else:
            st.markdown(f"❓ We are not sure what **{d['token']}** is (closest: {d['canonical']}, "
                        f"{d['similarity']:.0f}% match).")
            fix = st.text_input(f"Type the correct name for '{d['token']}' or leave blank to skip", key=f"fix{i}")
            if fix.strip():
                canon = NAME2CANON.get(fix.strip().lower())
                if canon:
                    confirmed.append(canon)
                else:
                    st.caption(f"'{fix}' is not in our medication list, so it will be marked Not assessed.")
                    confirmed.append(fix.strip().lower())
    extra = st.multiselect("Add a medicine we missed", sorted(NAME2CANON))
    confirmed += [NAME2CANON[x] for x in extra]

    if st.button("Check safety", type="primary"):
        st.session_state["report"] = check(confirmed)
        st.session_state["confirmed"] = sorted(set(confirmed))

rep = st.session_state.get("report")
if rep is not None:
    alerts, not_assessed = rep
    st.subheader("3. Safety report")
    st.write("Medicines checked: " + ", ".join(st.session_state["confirmed"]))
    order = ["Drug interaction", "Older-adult caution (Beers)", "Side effects to watch"]
    icons = {"Drug interaction": "🔴", "Older-adult caution (Beers)": "🟠", "Side effects to watch": "🟡"}
    if not alerts:
        st.success("No alerts found in our limited rule set. This does NOT mean the combination is safe.")
    for t in order:
        group = [a for a in alerts if a["type"] == t]
        if not group:
            continue
        st.markdown(f"### {icons[t]} {t} ({len(group)})")
        for a in group:
            with st.container(border=True):
                st.markdown(f"**{a['drugs']}** — {a['message']}")
                st.caption(f"Source: {a['source']}")
    if not_assessed:
        st.markdown("### ⚪ Not assessed")
        st.write("These are outside our current rule set, so we cannot say anything about them: "
                 + ", ".join(not_assessed))
    st.info("💬 Bring this list to your pharmacist or doctor. Do not stop or change any medicine on your own.")

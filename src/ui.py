"""Visual helpers for MedGuard AI: medicine-type icons (illustrations, never real pill appearance),
minimal line icons, accessible severity badges, cards and the app stylesheet."""
import html
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INFO = pd.read_csv(ROOT / "data" / "drug_info.csv").set_index("canonical")

INK, INK2, LINE, ACCENT = "#1F2937", "#6B7280", "#E5E7EB", "#B91C1C"

CATEGORY_COLOR = {
    "Heart & blood pressure": "#d64545", "Blood thinners": "#b83280", "Diabetes": "#2a78d6",
    "Cholesterol": "#b7860b", "Pain & muscle": "#d9622b", "Brain, mood & sleep": "#7c5cd6",
    "Stomach": "#1a9e6e", "Infections": "#0b8fa6", "Allergy & breathing": "#3d8fd0",
    "Bladder & prostate": "#8c6d3f", "Hormones, bones & other": "#6B7280", "Unknown": "#9CA3AF",
}

def info(canon):
    if canon in INFO.index:
        r = INFO.loc[canon]
        return {"used_for": r.used_for, "category": r.category, "form": r.form}
    return {"used_for": "Not in our medication list yet", "category": "Unknown", "form": "unknown"}

def icon_svg(canon, size=52):
    """Stylized icon by category and form. Deliberately NOT the real pill's look (avoids pill-matching by eye)."""
    i = info(canon); c = CATEGORY_COLOR.get(i["category"], "#9CA3AF"); form = i["form"]
    bg = f'<circle cx="26" cy="26" r="25" fill="{c}" fill-opacity="0.10"/>'
    if form == "capsule":
        body = (f'<g transform="rotate(-35 26 26)"><rect x="10" y="19" width="32" height="14" rx="7" fill="#ffffff" stroke="{c}" stroke-width="2"/>'
                f'<path d="M17 19 h9 v14 h-9 a7 7 0 0 1 0 -14z" fill="{c}"/></g>')
    elif form == "inhaler":
        body = (f'<rect x="17" y="12" width="13" height="22" rx="3" fill="{c}"/>'
                f'<rect x="20" y="30" width="18" height="9" rx="3" fill="#ffffff" stroke="{c}" stroke-width="2"/>')
    elif form == "tablet":
        body = (f'<ellipse cx="26" cy="27" rx="15" ry="10" fill="{c}" fill-opacity="0.35"/>'
                f'<ellipse cx="26" cy="25" rx="15" ry="10" fill="{c}"/>'
                f'<ellipse cx="21" cy="22" rx="5" ry="2.2" fill="#ffffff" fill-opacity="0.45"/>'
                f'<line x1="26" y1="17" x2="26" y2="33" stroke="#ffffff" stroke-opacity="0.8" stroke-width="1.6"/>')
    else:
        body = (f'<circle cx="26" cy="26" r="13" fill="#ffffff" stroke="{c}" stroke-width="2" stroke-dasharray="3 3"/>'
                f'<text x="26" y="31" text-anchor="middle" font-size="14" font-family="Inter, sans-serif" fill="{c}">?</text>')
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 52 52" role="img" '
            f'aria-label="{html.escape(i["category"])} medication icon">{bg}{body}</svg>')

# ---------------------------------------------------------------- minimal line icons (24x24, stroke)
_PATHS = {
    "alert": '<path d="M12 3 L22 20 H2 Z"/><line x1="12" y1="9" x2="12" y2="14"/><circle cx="12" cy="17" r="0.6" fill="currentColor"/>',
    "shield": '<path d="M12 3 L20 6 V12 C20 16.5 16.5 19.5 12 21 C7.5 19.5 4 16.5 4 12 V6 Z"/>',
    "shield-check": '<path d="M12 3 L20 6 V12 C20 16.5 16.5 19.5 12 21 C7.5 19.5 4 16.5 4 12 V6 Z"/><path d="M8.5 12 L11 14.5 L15.5 10"/>',
    "info": '<circle cx="12" cy="12" r="9"/><line x1="12" y1="11" x2="12" y2="16.5"/><circle cx="12" cy="7.8" r="0.6" fill="currentColor"/>',
    "octagon": '<path d="M8 3 H16 L21 8 V16 L16 21 H8 L3 16 V8 Z"/><line x1="12" y1="8" x2="12" y2="13"/><circle cx="12" cy="16.2" r="0.6" fill="currentColor"/>',
    "circle-dash": '<circle cx="12" cy="12" r="9" stroke-dasharray="3 3"/>',
    "message": '<path d="M4 5 H20 V16 H10 L5 20 V16 H4 Z"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12 L11 15 L16 9.5"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5 C9.5 7.5 14.5 7.5 14.5 10 C14.5 11.5 12 12 12 13.5"/><circle cx="12" cy="16.6" r="0.6" fill="currentColor"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><line x1="16" y1="16" x2="20.5" y2="20.5"/>',
    "x": '<circle cx="12" cy="12" r="9"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/>',
    "file-text": '<path d="M6 3 H14 L19 8 V21 H6 Z"/><path d="M14 3 V8 H19"/><line x1="9" y1="12" x2="16" y2="12"/><line x1="9" y1="15.5" x2="16" y2="15.5"/>',
}

def line_icon(name, size=20, color=INK2):
    return (f'<svg class="mg-li" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:{color}" aria-hidden="true">'
            f'{_PATHS[name]}</svg>')

def chip(text, color):
    return (f'<span class="mg-chip" style="color:{color};border-color:{color}40;background:{color}12">'
            f'{html.escape(text)}</span>')

STATUS = {"checked": ("Has safety rules", "#047857", "check"), "not_assessed": ("Not assessed", "#4B5563", "circle-dash"),
          "review": ("Please confirm", "#B45309", "help")}

def status_chip(status):
    label, col, ic = STATUS[status]
    return f'<span class="mg-chip mg-chip-ic" style="color:{col};border-color:{col}40;background:{col}10">{line_icon(ic, 14, col)}{label}</span>'

def med_card(token, canon, status, extra=""):
    i = info(canon)
    color = CATEGORY_COLOR.get(i["category"], "#9CA3AF")
    name = html.escape(canon or token)
    seen = "" if (canon and token.lower() == canon.lower()) else f'<div class="mg-seen">You wrote “{html.escape(token)}”</div>'
    return f"""<div class="mg-card {'mg-review' if status=='review' else ''}">
  <div class="mg-card-top">{icon_svg(canon, 48)}<div><div class="mg-name">{name}</div>{seen}</div></div>
  <div class="mg-use">{html.escape(i['used_for'])}</div>
  <div class="mg-chips">{chip(i['category'], color)}{status_chip(status)}</div>{extra}
</div>"""

# ---------------------------------------------------------------- severity (labels only; classification unchanged)
# Each alert type keeps its own label, colour AND shape so meaning never relies on colour alone.
ALERT_STYLE = {
    "Drug interaction": {"label": "Interaction", "color": "#B91C1C", "bg": "#FEF2F2", "icon": "alert",
                         "title": "Possible interactions for your clinician to review"},
    "Older-adult caution (Beers)": {"label": "Older-adult caution", "color": "#B45309", "bg": "#FFFBEB", "icon": "octagon",
                                    "title": "Older-adult cautions for your clinician to review"},
    "Side effects to watch": {"label": "Side effects", "color": "#1D4ED8", "bg": "#EFF6FF", "icon": "info",
                              "title": "Side effects to mention to your clinician"},
}
SEVERITY = ALERT_STYLE  # backwards-compatible name

def severity_badge(a):
    s = ALERT_STYLE.get(a["type"], {"label": a["type"], "color": INK2, "bg": "#F3F4F6", "icon": "info"})
    level = a.get("severity")
    txt = s["label"] + (f" · {level}" if level and level != "Info" else "")
    return (f'<span class="mg-sev" style="color:{s["color"]};background:{s["bg"]};border-color:{s["color"]}55" '
            f'role="note" aria-label="{html.escape(txt)}">{line_icon(s["icon"], 15, s["color"])}{html.escape(txt)}</span>')

def section_title(alert_type, count):
    s = ALERT_STYLE[alert_type]
    return (f'<div class="mg-sec">{line_icon(s["icon"], 22, s["color"])}<span>{s["title"]}</span>'
            f'<span class="mg-count">{count}</span></div>')

def alert_card(a):
    s = ALERT_STYLE.get(a["type"], {"color": INK2})
    drugs = [d.strip() for d in a["drugs"].split("+")]
    icons = "".join(icon_svg(d, 36) for d in drugs[:4])
    note = f'<div class="mg-src"><i>{html.escape(a["note"])}</i></div>' if a.get("note") else ""
    return f"""<div class="mg-alert" style="border-left-color:{s['color']}">
  <div class="mg-alert-top">{severity_badge(a)}</div>
  <div class="mg-alert-head"><span class="mg-icons">{icons}</span><span class="mg-alert-drugs">{html.escape(a['drugs'])}</span></div>
  <div class="mg-alert-msg">{html.escape(a['message'])}</div>
  {note}<div class="mg-src">Source: {html.escape(a['source'])}</div>
</div>"""

def step_box(n, title, body, ml=False):
    tag = '<span class="mg-ml">ML model</span>' if ml else '<span class="mg-rule">Rules</span>'
    return f"""<div class="mg-step"><div class="mg-step-n">{n}</div><div class="mg-step-t">{html.escape(title)}</div>
<div class="mg-step-b">{html.escape(body)}</div>{tag}</div>"""

def stat_tile(value, label, note=""):
    return f"""<div class="mg-tile"><div class="mg-tile-v">{html.escape(value)}</div><div class="mg-tile-l">{html.escape(label)}</div>
<div class="mg-tile-n">{html.escape(note)}</div></div>"""

def panel(title, body_html, icon=None, color=INK2):
    ic = line_icon(icon, 20, color) if icon else ""
    return f'<div class="mg-panel"><div class="mg-panel-h">{ic}<span>{html.escape(title)}</span></div>{body_html}</div>'

def disclaimer(text):
    return f'<div class="mg-disclaimer">{line_icon("shield", 18, "#6B7280")}<span>{html.escape(text)}</span></div>'

def notice(text_html, icon="info", color="#1D4ED8", bg="#EFF6FF"):
    return f'<div class="mg-notice" style="background:{bg};border-color:{color}33">{line_icon(icon, 18, color)}<span>{text_html}</span></div>'

CSS = """
<style>
:root { --ink:#1F2937; --ink2:#6B7280; --line:#E5E7EB; --accent:#B91C1C; --accent-dark:#991B1B; --blush:#FFF1F2;
        --shadow: 0 1px 2px rgba(17,24,39,.04), 0 4px 14px rgba(17,24,39,.06); }
.mg-hero, .mg-card, .mg-alert, .mg-panel, .mg-step, .mg-tile, .mg-disclaimer, .mg-notice { font-family: 'Inter', sans-serif; }
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }
.stApp { background: var(--blush); }
.block-container { padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1180px; }
h1, h2, h3, h4 { color: var(--ink) !important; font-weight: 700 !important; letter-spacing: -0.015em; }
h2 { font-size: 1.55rem !important; margin-top: .4rem !important; }
h3 { font-size: 1.2rem !important; }
p, li { color: var(--ink); }
[data-testid="stCaptionContainer"], .stCaption { color: var(--ink2) !important; }

/* header */
.mg-hero { background:#fff; border:1px solid var(--line); border-radius:20px; box-shadow:var(--shadow);
  padding: 26px 30px; margin-bottom: 18px; display:flex; gap:24px; align-items:center; }
.mg-brand { font-size: 2.35rem; font-weight: 800; color: var(--ink); letter-spacing: -0.03em; line-height:1.1; margin:0; }
.mg-brand span { color: var(--accent); }
.mg-tagline { font-size: 1.08rem; font-weight: 600; color: var(--accent); margin: 6px 0 8px; }
.mg-sub { color: var(--ink2); font-size: 0.98rem; margin:0; max-width: 640px; }
.mg-hero-icons { display:flex; gap:4px; flex-wrap:wrap; }

/* white containers */
[class*="st-key-mgbox"] { background:#fff; border:1px solid var(--line); border-radius:18px; box-shadow:var(--shadow);
  padding: 22px 24px 18px; margin-bottom: 16px; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #fff; border:1px solid var(--line); border-radius: 14px; padding: 6px; box-shadow: var(--shadow); }
.stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 8px 14px; font-weight: 600; color: var(--ink2); }
.stTabs [aria-selected="true"] { background: var(--blush); color: var(--accent) !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }

/* buttons */
.stButton > button, .stDownloadButton > button { border-radius: 10px; font-weight: 600; min-height: 42px;
  transition: background .15s ease, box-shadow .15s ease, transform .05s ease, border-color .15s ease; }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] { background: var(--accent) !important; border: 1px solid var(--accent) !important; color:#fff !important; }
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover { background: var(--accent-dark) !important; border-color: var(--accent-dark) !important;
  box-shadow: 0 6px 16px rgba(185,28,28,.25); }
.stButton > button[kind="primary"]:active { transform: translateY(1px); }
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primary"] span, [data-testid="stBaseButton-primary"] div { color:#fff !important; }
.stButton > button[kind="secondary"], .stDownloadButton > button { background:#fff; border:1px solid var(--line); color: var(--ink); }
.stButton > button[kind="secondary"]:hover, .stDownloadButton > button:hover { border-color: var(--accent); color: var(--accent); background:#fff; }

/* inputs */
.stTextArea textarea, .stTextInput input, .stNumberInput input { border-radius: 10px !important; font-size: 0.98rem; }
[data-baseweb="textarea"], [data-baseweb="input"], [data-baseweb="select"] > div { border-radius: 10px !important; border-color: var(--line) !important; }
[data-baseweb="textarea"]:focus-within, [data-baseweb="input"]:focus-within { border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(185,28,28,.12); }
.stTextArea, .stTextInput, .stMultiSelect, .stNumberInput { margin-bottom: 4px; }
label, [data-testid="stWidgetLabel"] p { color: var(--ink) !important; font-weight: 500; }

/* disclaimer & notices */
.mg-disclaimer { display:flex; gap:10px; align-items:flex-start; background:#fff; border:1px solid var(--line); border-radius:12px;
  padding: 10px 14px; color: var(--ink2); font-size: 0.86rem; line-height:1.45; margin: 4px 0 16px; }
.mg-notice { display:flex; gap:10px; align-items:flex-start; border:1px solid; border-radius:12px; padding:10px 14px; font-size:0.92rem; color:var(--ink); margin:8px 0; }
.mg-li { flex: 0 0 auto; margin-top: 1px; }

/* medication cards */
.mg-card { border:1px solid var(--line); border-radius:16px; padding:16px 18px; background:#fff; min-height:158px; margin-bottom:6px; box-shadow: var(--shadow); }
.mg-review { border-color:#FCD34D; background:#FFFBEB; }
.mg-card-top { display:flex; gap:12px; align-items:center; }
.mg-name { font-weight:700; font-size:1.1rem; color:var(--ink); text-transform: capitalize; }
.mg-seen { font-size:0.8rem; color:var(--ink2); }
.mg-use { color:var(--ink2); font-size:0.92rem; margin:10px 0 8px; }
.mg-chips { display:flex; flex-wrap:wrap; gap:6px; }
.mg-chip { display:inline-flex; align-items:center; gap:4px; font-size:0.76rem; font-weight:600; border:1px solid; border-radius:999px; padding:3px 10px; }

/* alerts */
.mg-sec { display:flex; align-items:center; gap:10px; font-size:1.12rem; font-weight:700; color:var(--ink); margin: 18px 0 6px; }
.mg-count { font-size:0.8rem; font-weight:700; color:var(--ink2); background:#F3F4F6; border-radius:999px; padding:2px 9px; }
.mg-alert { border:1px solid var(--line); border-left:5px solid; border-radius:14px; padding:14px 18px; margin:10px 0; background:#fff; box-shadow: var(--shadow); }
.mg-alert-top { margin-bottom: 8px; }
.mg-sev { display:inline-flex; align-items:center; gap:6px; font-size:0.78rem; font-weight:700; letter-spacing:.01em; border:1px solid; border-radius:8px; padding:3px 9px; }
.mg-alert-head { display:flex; align-items:center; gap:10px; }
.mg-icons { display:flex; }
.mg-alert-drugs { font-weight:700; text-transform: capitalize; color:var(--ink); font-size:1.02rem; }
.mg-alert-msg { margin:8px 0 6px; color:var(--ink); line-height:1.5; }
.mg-src { font-size:0.8rem; color:var(--ink2); }

/* panels, tiles, steps */
.mg-panel { border:1px solid var(--line); border-radius:16px; padding:16px 18px; background:#fff; box-shadow: var(--shadow); margin-bottom:12px; color: var(--ink); line-height:1.55; }
.mg-panel-h { display:flex; align-items:center; gap:8px; font-weight:700; font-size:1.02rem; color:var(--ink); margin-bottom:8px; }
.mg-orig { font-size:1rem; line-height:1.7; background:#F9FAFB; border:1px solid #E5E7EB; border-radius:10px; padding:12px 14px; white-space:pre-wrap; }
mark.mg-hl-ok { background:#D1FAE5; color:#065F46; border-radius:4px; padding:0 3px; }
mark.mg-hl-rev { background:#FEF3C7; color:#92400E; border-radius:4px; padding:0 3px; }
.mg-q { display:flex; gap:10px; padding:8px 0; border-top:1px solid #F3F4F6; font-size:0.94rem; }
.mg-q:first-of-type { border-top:none; }
.mg-q b { color: var(--accent); min-width: 18px; }
.mg-steps { display:flex; gap:12px; align-items:stretch; flex-wrap:wrap; margin: 8px 0 18px; }
.mg-step { flex:1 1 170px; border:1px solid var(--line); border-radius:16px; padding:16px; background:#fff; box-shadow: var(--shadow); }
.mg-step-n { width:28px; height:28px; border-radius:50%; background:var(--accent); color:#fff; font-weight:700; display:flex; align-items:center; justify-content:center; font-size:.9rem; }
.mg-step-t { font-weight:700; margin:10px 0 4px; color:var(--ink); }
.mg-step-b { font-size:0.88rem; color:var(--ink2); margin-bottom:10px; line-height:1.45; }
.mg-ml { background:#FEE2E2; color:#991B1B; font-size:0.72rem; font-weight:700; padding:3px 9px; border-radius:999px; }
.mg-rule { background:#F3F4F6; color:#4B5563; font-size:0.72rem; font-weight:700; padding:3px 9px; border-radius:999px; }
.mg-tiles { display:flex; gap:12px; flex-wrap:wrap; margin: 6px 0 14px; }
.mg-tile { flex:1 1 190px; border:1px solid var(--line); border-radius:16px; padding:16px 18px; background:#fff; box-shadow: var(--shadow); }
.mg-tile-v { font-size:1.9rem; font-weight:800; color:var(--accent); line-height:1.1; letter-spacing:-0.02em; }
.mg-tile-l { font-weight:600; color:var(--ink); margin-top:4px; }
.mg-tile-n { font-size:0.8rem; color:var(--ink2); margin-top:2px; }
.mg-assume { display:flex; gap:10px; font-size:0.86rem; color:#92400E; background:#FFFBEB; border:1px solid #FDE68A; border-radius:12px; padding:10px 14px; margin-bottom:10px; }
.mg-legend { display:flex; flex-wrap:wrap; gap:6px 14px; align-items:center; }
.mg-legend span { display:flex; align-items:center; gap:5px; font-size:0.85rem; color:var(--ink2); }
.mg-found { display:flex; align-items:center; gap:8px; padding:6px 0; border-top:1px solid #F3F4F6; font-size:.93rem; }
.mg-found code { background:#F9FAFB; border:1px solid var(--line); border-radius:6px; padding:1px 6px; color: var(--ink); }
[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:14px; padding:12px 16px; box-shadow: var(--shadow); }
[data-testid="stMetricValue"] { color: var(--ink); font-weight:800; }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
[data-testid="stExpander"] details { background:#fff; border-radius:12px; }
[data-testid="stImage"] img { border-radius: 12px; }

/* mobile */
@media (max-width: 768px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 3.5rem; }
  .mg-hero { flex-direction:column; align-items:flex-start; padding:18px; gap:12px; }
  .mg-brand { font-size: 1.8rem; }
  [class*="st-key-mgbox"] { padding: 16px 14px 12px; border-radius:14px; }
  .stTabs [data-baseweb="tab"] { padding: 6px 10px; font-size: .85rem; }
  .mg-tile-v { font-size: 1.5rem; }
  .mg-alert { padding: 12px 14px; }
}
</style>
"""

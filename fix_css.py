"""Replaces the CSS block in main.py with the new light purple/white theme."""

NEW_CSS = r'''CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ════ BASE ════════════════════════════════════════════════════════════ */
html, body, .gradio-container {
    background: linear-gradient(145deg, #f8f4ff 0%, #f0e8ff 45%, #eaf0ff 100%) !important;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    color: #2d1a54 !important;
    min-height: 100vh;
}
/* ════ HERO ════════════════════════════════════════════════════════════ */
.hero {
    background: linear-gradient(120deg, #6d28d9 0%, #8b5cf6 55%, #a78bfa 100%);
    border-radius: 18px; padding: 24px 18px 22px;
    text-align: center; margin-bottom: 14px;
    box-shadow: 0 8px 32px rgba(109,40,217,0.28);
}
.hero h1 { font-size:clamp(1.1rem,5vw,1.8rem); font-weight:800; color:#fff !important; margin:0 0 6px; }
.hero p  { color:rgba(255,255,255,0.9) !important; font-size:clamp(0.75rem,2.5vw,0.9rem); margin:0; }
/* ════ CARDS ════════════════════════════════════════════════════════════ */
.card {
    background: rgba(255,255,255,0.82);
    border: 1.5px solid rgba(139,92,246,0.2);
    border-radius: 14px; padding: 14px 14px 10px; margin-bottom: 10px;
    box-shadow: 0 2px 12px rgba(109,40,217,0.07);
}
.card-title {
    font-size:0.93rem; font-weight:700; color:#6d28d9;
    margin:0 0 10px; border-left:3px solid #8b5cf6;
    padding-left:8px; display:block;
}
/* ════ TABS ════════════════════════════════════════════════════════════ */
.tab-nav { gap:6px !important; flex-wrap:wrap !important; }
.tab-nav button {
    background:rgba(255,255,255,0.8) !important;
    border:1.5px solid rgba(139,92,246,0.3) !important;
    color:#5b21b6 !important; border-radius:10px !important;
    padding:10px 14px !important; font-weight:600 !important;
    font-size:clamp(0.75rem,2vw,0.88rem) !important;
    transition:all 0.18s !important; min-height:44px !important;
}
.tab-nav button.selected, .tab-nav button:hover {
    background:linear-gradient(120deg,#6d28d9,#8b5cf6) !important;
    color:white !important; border-color:#7c3aed !important;
    box-shadow:0 4px 16px rgba(109,40,217,0.3) !important;
}
/* ════ GROUPS ═══════════════════════════════════════════════════════════ */
.gr-group, .gr-box {
    background:rgba(255,255,255,0.75) !important;
    border:1.5px solid rgba(139,92,246,0.18) !important;
    border-radius:14px !important;
    box-shadow:0 1px 8px rgba(109,40,217,0.06) !important;
}
/* ════ LABELS ═══════════════════════════════════════════════════════════ */
.gradio-dropdown label, .gradio-checkbox label, .gradio-radio label,
label > span:first-child, .label-wrap > span {
    color:#4c1d95 !important; font-weight:600 !important; font-size:0.86rem !important;
}
/* ════ DROPDOWNS ════════════════════════════════════════════════════════ */
.gradio-dropdown select, select {
    width:100% !important; min-height:48px !important;
    background:#ffffff !important;
    border:1.5px solid rgba(139,92,246,0.45) !important;
    border-radius:10px !important; color:#2d1a54 !important;
    font-size:0.9rem !important; font-family:inherit !important;
    padding:10px 14px !important; cursor:pointer;
    -webkit-appearance:none; appearance:none;
    box-shadow:0 1px 4px rgba(109,40,217,0.08);
}
.gradio-dropdown select:focus {
    border-color:#7c3aed !important; outline:none !important;
    box-shadow:0 0 0 3px rgba(139,92,246,0.18) !important;
}
option { background:#fff !important; color:#2d1a54 !important; }
/* ════ CHECKBOX ════════════════════════════════════════════════════════ */
input[type=checkbox] { accent-color:#7c3aed !important; width:20px !important; height:20px !important; }
.gradio-checkbox label {
    display:flex !important; align-items:center !important; gap:8px !important;
    cursor:pointer; min-height:44px !important; color:#4c1d95 !important;
}
/* ════ RADIO ════════════════════════════════════════════════════════════ */
.gradio-radio .wrap { background:transparent !important; gap:6px !important; }
.gradio-radio .wrap label {
    background:rgba(139,92,246,0.07) !important;
    border:1.5px solid rgba(139,92,246,0.3) !important;
    border-radius:8px !important; padding:9px 14px !important;
    color:#4c1d95 !important; font-size:0.85rem !important;
    cursor:pointer; transition:all 0.18s !important;
}
.gradio-radio .wrap label:has(input:checked) {
    background:linear-gradient(120deg,#6d28d9,#8b5cf6) !important;
    border-color:#7c3aed !important; color:white !important;
    box-shadow:0 2px 10px rgba(109,40,217,0.22) !important;
}
/* ════ SPECIAL BOXES ═════════════════════════════════════════════════ */
.session-box {
    background:rgba(139,92,246,0.06) !important;
    border:1.5px dashed rgba(139,92,246,0.4) !important;
    border-radius:12px !important; padding:14px !important; margin-top:8px !important;
}
.shift-box {
    background:rgba(245,158,11,0.06) !important;
    border:1.5px dashed rgba(245,158,11,0.45) !important;
    border-radius:12px !important; padding:14px !important; margin-top:8px !important;
}
.deadline-box {
    background:rgba(239,68,68,0.04) !important;
    border:1.5px solid rgba(239,68,68,0.25) !important;
    border-radius:12px !important; padding:12px 14px !important; margin-top:4px !important;
}
/* ════ BUTTON ════════════════════════════════════════════════════════ */
#predict-btn {
    background:linear-gradient(120deg,#6d28d9 0%,#8b5cf6 60%,#a78bfa 100%) !important;
    border:none !important; border-radius:12px !important;
    font-size:clamp(0.9rem,3vw,1.05rem) !important; font-weight:800 !important;
    color:white !important; padding:16px !important; width:100% !important;
    min-height:54px !important; box-shadow:0 6px 24px rgba(109,40,217,0.4) !important;
    transition:all 0.22s !important; letter-spacing:0.3px !important;
}
#predict-btn:hover { transform:translateY(-2px) !important;
    box-shadow:0 10px 32px rgba(109,40,217,0.5) !important; }
#predict-btn span { color:white !important; }
/* ════ FOCUS RESULT ════════════════════════════════════════════════════ */
#focus-result .prose h3 { color:#4c1d95 !important; font-size:clamp(1.1rem,4vw,1.3rem) !important; }
#focus-result .prose p  { color:#3b1878 !important; }
#focus-result .prose blockquote {
    border-left:3px solid #8b5cf6; background:rgba(139,92,246,0.08);
    border-radius:8px; padding:10px 14px; margin:8px 0; color:#3b1878 !important;
}
/* ════ SCHEDULE OUTPUT ══════════════════════════════════════════════════ */
#schedule-out .prose, #schedule-out .prose p { color:#2d1a54 !important; }
#schedule-out .prose h2 { color:#4c1d95 !important; font-size:1.05rem !important; }
#schedule-out .prose table { width:100%; border-collapse:collapse; font-size:clamp(0.78rem,2vw,0.9rem); }
#schedule-out .prose th {
    color:#5b21b6 !important; font-weight:700;
    border-bottom:2px solid rgba(139,92,246,0.3);
    padding:8px 6px; background:rgba(139,92,246,0.08);
}
#schedule-out .prose td {
    padding:8px 6px; border-bottom:1px solid rgba(139,92,246,0.1);
    color:#2d1a54 !important; vertical-align:top;
}
#schedule-out .prose strong { color:#6d28d9 !important; }
#schedule-out .prose blockquote {
    border-left:3px solid #8b5cf6; background:rgba(139,92,246,0.08);
    border-radius:8px; padding:10px 14px; margin:8px 0; color:#2d1a54 !important;
}
/* ════ PROGRESS ═════════════════════════════════════════════════════════ */
.streak-badge { font-size:1.2rem !important; font-weight:700 !important; color:#5b21b6 !important; }
.gradio-dataframe table td, .gradio-dataframe table th,
.gradio-dataframe tbody td, .gradio-dataframe thead th,
[class*="svelte"] td, [class*="svelte"] th {
    color:#2d1a54 !important; background:transparent !important;
}
.gradio-dataframe table { border-color:rgba(139,92,246,0.2) !important; }
.gradio-dataframe thead th {
    background:rgba(139,92,246,0.1) !important;
    border-bottom:1px solid rgba(139,92,246,0.3) !important;
}
/* ════ TEXTBOXES ════════════════════════════════════════════════════════ */
textarea, input[type=text] {
    color:#2d1a54 !important; background:#ffffff !important;
    border:1.5px solid rgba(139,92,246,0.3) !important;
    border-radius:8px !important;
}
/* ════ GENERAL PROSE ═════════════════════════════════════════════════════ */
.prose, .prose * { color:#2d1a54 !important; }
.prose strong, .prose b { color:#6d28d9 !important; }
.prose h1, .prose h2, .prose h3, .prose h4 { color:#4c1d95 !important; }
.prose a { color:#7c3aed !important; }
.prose p, .prose li { color:#2d1a54 !important; }
.markdown-body, .markdown-body * { color:#2d1a54 !important; }
/* ════ MISC ══════════════════════════════════════════════════════════════ */
.gradio-plot label > span { color:#5b21b6 !important; }
button.reset, .reset-button, [aria-label="Reset"],
[title="Reset"], .gradio-slider button { display:none !important; }
.my-hr { border:none; border-top:1px solid rgba(139,92,246,0.2); margin:14px 0; }
footer { display:none !important; }
/* ════ MOBILE ════════════════════════════════════════════════════════════ */
@media (max-width:768px) {
    .gr-row, .row { flex-direction:column !important; }
    .gr-column, [class*="col-"] { width:100% !important; max-width:100% !important;
        flex:1 1 100% !important; }
    select, .gradio-dropdown select { min-height:52px !important; font-size:1rem !important; }
    .card { padding:12px !important; }
    .tab-nav button { padding:9px 10px !important; font-size:0.76rem !important; }
}
"""
'''

with open("app/main.py", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")

# Find CSS block: line starting with 'CSS = """' and ending with '"""'
start_idx = end_idx = None
for i, line in enumerate(lines):
    if start_idx is None and line.strip().startswith('CSS = """'):
        start_idx = i
    elif start_idx is not None and i > start_idx and line.strip() == '"""':
        end_idx = i
        break

if start_idx is None or end_idx is None:
    print(f"ERROR: could not find CSS block (start={start_idx}, end={end_idx})")
    exit(1)

print(f"Replacing lines {start_idx+1}–{end_idx+1}")
new_lines = lines[:start_idx] + NEW_CSS.split("\n") + lines[end_idx+1:]
with open("app/main.py", "w", encoding="utf-8") as f:
    f.write("\n".join(new_lines))
print("Done! CSS replaced successfully.")

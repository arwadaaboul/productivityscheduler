"""
main.py — Student Intelligent Productivity Scheduler
=====================================================
Features:
  - ML focus prediction (Random Forest)
  - AI session time recommendation
  - Rescue Mode for Low focus days
  - Time-aware schedule (anchored to real NOW)
  - Deadline input
  - Daily log, streak tracker, focus trend chart
  - Export schedule as .txt

Run:    py app/main.py
Local:  http://127.0.0.1:7860
"""

import os, sys, tempfile
from datetime import datetime
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date as dt_date
import gradio as gr

# ── Config ────────────────────────────────────────────────────────────────────
SHARE = True

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_DIR)
from app.model.scheduler    import get_schedule
from app.utils.log_manager  import (
    save_entry, load_log, get_streak, get_trend_data, build_history_table
)

MODELS_DIR  = os.path.join(PROJECT_DIR, "models")
EXPORTS_DIR = os.path.join(PROJECT_DIR, "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)

# ── Load models ───────────────────────────────────────────────────────────────

def _load(fname):
    p = os.path.join(MODELS_DIR, fname)
    return joblib.load(p) if os.path.exists(p) else None

model_real      = _load("model_real.pkl")
model_synthetic = _load("model_synthetic.pkl")
model_combined  = _load("model_combined.pkl")
PREDICT_MODEL   = model_combined or model_synthetic or model_real

MODEL_MAP = {
    "Model A – Real Survey Only":            model_real,
    "Model B – Synthetic Dataset Only":      model_synthetic,
    "Model C – Combined (Real + Synthetic)": model_combined,
}

# ── Options ───────────────────────────────────────────────────────────────────

SLEEP_H_OPTS = (
    ["1 hr", "1.5 hrs", "2 hrs", "2.5 hrs", "3 hrs"] +
    ["3.5 hrs", "4 hrs", "4.5 hrs", "5 hrs", "5.5 hrs",
     "6 hrs", "6.5 hrs", "7 hrs", "7.5 hrs",
     "8 hrs", "8.5 hrs", "9 hrs", "9.5 hrs", "10 hrs"]
)

QUALITY_OPTS = [
    "1 — Very poor (restless, barely slept)",
    "2 — Poor (woke up often)",
    "3 — Okay (decent enough)",
    "4 — Good (woke up refreshed)",
    "5 — Excellent (best sleep)",
]

STRESS_OPTS = [
    "1-2 — Very calm, no worries",
    "3-4 — Mild stress, manageable",
    "5-6 — Moderate stress",
    "7-8 — Quite stressed",
    "9-10 — Extremely stressed",
]

WELLBEING_OPTS = [
    "1-2 — Very low, struggling today",
    "3-4 — Low, not feeling great",
    "5-6 — Average, okay",
    "7-8 — Good, feeling well",
    "9-10 — Excellent, thriving",
]

SCREEN_OPTS = ["0 hrs", "0.5 hrs", "1 hr", "1.5 hrs", "2 hrs",
               "2.5 hrs", "3 hrs", "3.5 hrs", "4 hrs", "5 hrs",
               "6 hrs", "7 hrs", "8 hrs"]

EXERCISE_OPTS = [
    "Rarely or never",
    "1–2 days per week",
    "3–4 days per week",
    "5+ days per week (very active)",
]

DISTRACTION_OPTS = [
    "Never — I stay fully focused",
    "Rarely — occasionally distracted",
    "Sometimes — moderate distraction",
    "Often — hard to resist",
    "Constantly — always on my phone",
]

PEAK_OPTS = [
    "Morning (6am – 12pm)",
    "Afternoon (12pm – 5pm)",
    "Evening (5pm – 10pm)",
    "Late Night (10pm – 6am)",
]

SESSION_H_OPTS = ["0.5 hrs", "1 hr", "1.5 hrs", "2 hrs", "2.5 hrs",
                  "3 hrs", "3.5 hrs", "4 hrs", "4.5 hrs", "5 hrs",
                  "5.5 hrs", "6 hrs", "6.5 hrs", "7 hrs", "7.5 hrs", "8 hrs"]

SHIFT_OPTS = [f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)]

DEADLINE_OPTS = [
    "No deadline soon",
    "1 day (tomorrow!)",
    "2 days",
    "3 days",
    "5 days",
    "7 days (1 week)",
    "10 days",
    "14 days (2 weeks)",
]

# ── Lookup tables ─────────────────────────────────────────────────────────────

EXERCISE_ENC = {
    "Rarely or never":                0,
    "1–2 days per week":              1,
    "3–4 days per week":              3,
    "5+ days per week (very active)": 5,
}
DISTRACTION_ENC   = {o: i for i, o in enumerate(DISTRACTION_OPTS)}
DISTRACTION_SHORT = {
    "Never — I stay fully focused":    "Never",
    "Rarely — occasionally distracted":"Rarely",
    "Sometimes — moderate distraction":"Sometimes",
    "Often — hard to resist":          "Often",
    "Constantly — always on my phone": "Constantly",
}
FOCUS_COLORS    = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}
FOCUS_MSGS      = {
    "High":   "Your brain is ready for deep, demanding work today.",
    "Medium": "Solid focus — structured sessions will keep you on track.",
    "Low":    "Recovery day — short sprints serve you better than pushing through.",
}
FOCUS_RECOMMEND = {"High": (4, 6), "Medium": (2, 4), "Low": (1, 2)}
DEADLINE_DAYS_MAP = {
    "No deadline soon":     None,
    "1 day (tomorrow!)":    1,
    "2 days":               2,
    "3 days":               3,
    "5 days":               5,
    "7 days (1 week)":      7,
    "10 days":              10,
    "14 days (2 weeks)":    14,
}

# ── Parse helpers ─────────────────────────────────────────────────────────────

def _hrs(s):
    try:    return float(str(s).split()[0])
    except: return 1.0

def _range_first(s):
    try:    return int(str(s).split("-")[0].strip())
    except: return 5

def _first_num(s):
    try:    return int(str(s).split()[0])
    except: return 3

def _parse_time(t_str):
    try:
        h, m = str(t_str).split(":")
        return int(h), int(m)
    except:
        return 17, 0


# ── AI session recommender ────────────────────────────────────────────────────

def recommend_session_time(sleep_quality, stress, wellbeing,
                           sleep_hours, exercise_freq):
    scores = {
        "Morning (6am – 12pm)":     0,
        "Afternoon (12pm – 5pm)":   0,
        "Evening (5pm – 10pm)":     0,
        "Late Night (10pm – 6am)": -5,
    }
    if sleep_quality >= 4:
        scores["Morning (6am – 12pm)"]   += 4
        scores["Afternoon (12pm – 5pm)"] += 2
    elif sleep_quality == 3:
        scores["Afternoon (12pm – 5pm)"] += 3
        scores["Morning (6am – 12pm)"]   += 1
    else:
        scores["Afternoon (12pm – 5pm)"] += 4
        scores["Evening (5pm – 10pm)"]   += 3

    if sleep_hours >= 7:
        scores["Morning (6am – 12pm)"] += 2
    elif sleep_hours < 5:
        scores["Morning (6am – 12pm)"] -= 3
        scores["Evening (5pm – 10pm)"]  += 2

    if stress >= 7:
        scores["Late Night (10pm – 6am)"] -= 3
        scores["Afternoon (12pm – 5pm)"]  += 2
    elif stress <= 3:
        scores["Morning (6am – 12pm)"]    += 2
        scores["Late Night (10pm – 6am)"] += 2

    if wellbeing >= 7:
        scores["Morning (6am – 12pm)"]    += 1
        scores["Late Night (10pm – 6am)"] += 2
    elif wellbeing <= 3:
        scores["Late Night (10pm – 6am)"] -= 4
        scores["Evening (5pm – 10pm)"]    -= 1

    if "5+" in exercise_freq or "3–4" in exercise_freq:
        scores["Morning (6am – 12pm)"] += 1

    best = max(scores, key=scores.get)
    reasons = []
    if sleep_quality >= 4:
        reasons.append(f"great sleep quality ({sleep_quality}/5)")
    elif sleep_quality <= 2:
        reasons.append(f"poor sleep ({sleep_quality}/5) — brain needs time to wake up")
    if stress >= 7:
        reasons.append("high stress is better managed with structured daytime work")
    elif stress <= 3:
        reasons.append("low stress gives you scheduling flexibility")
    if sleep_hours >= 7.5:
        reasons.append(f"{sleep_hours}h sleep primes morning focus")
    elif sleep_hours < 5:
        reasons.append(f"only {sleep_hours}h sleep — morning alertness may be delayed")
    reason = " and ".join(reasons) if reasons else "based on your habits today"
    return best, reason


# ── Main prediction + schedule ────────────────────────────────────────────────

def predict_and_schedule(
    sleep_hours, sleep_quality, stress_level, wellbeing,
    screen_time, exercise_freq, distraction,
    has_job, shift_start, shift_end,
    deadline,
    schedule_for,
    s1_time, s1_hours,
    use_s2, s2_time, s2_hours,
    use_s3, s3_time, s3_hours,
):
    if PREDICT_MODEL is None:
        err = "⚠️ Models not found — run `py app/model/train_model.py` first."
        return err, err, None

    model = PREDICT_MODEL["model"]
    feats = PREDICT_MODEL["feature_names"]

    sl_h  = _hrs(sleep_hours)
    sl_q  = _first_num(sleep_quality)
    st_l  = _range_first(stress_level)
    wb    = _range_first(wellbeing)
    sc_t  = _hrs(screen_time)
    ex    = EXERCISE_ENC.get(exercise_freq, 1)
    dt    = DISTRACTION_ENC.get(distraction, 2)
    sh_d  = DISTRACTION_SHORT.get(distraction, "Sometimes")
    s1h   = _hrs(s1_hours)
    dl_days = DEADLINE_DAYS_MAP.get(deadline, None)

    encode_map = {
        "sleep_hours":           sl_h,
        "sleep_quality":         sl_q,
        "stress_level":          st_l,
        "screen_time":           sc_t,
        "study_hours":           s1h,
        "exercise_freq":         ex,
        "mental_wellbeing":      wb,
        "distraction":           dt,
        "study_hours_per_day":   s1h,
        "social_media_hours":    sc_t,
        "exercise_frequency":    ex,
        "mental_health_rating":  wb,
        "attendance_percentage": 80,
        "netflix_hours":         sc_t * 0.5,
        "part_time_job_enc":     1 if has_job == "Yes" else 0,
    }
    row_df = pd.DataFrame([[encode_map.get(f, 0) for f in feats]], columns=feats)
    probs  = model.predict_proba(row_df)[0]
    labels = model.classes_
    focus  = labels[np.argmax(probs)]
    conf   = probs[np.argmax(probs)]

    emoji  = FOCUS_COLORS.get(focus, "❓")
    lo, hi = FOCUS_RECOMMEND.get(focus, (2, 4))
    msg    = FOCUS_MSGS.get(focus, "")

    rec_slot, rec_reason = recommend_session_time(
        sleep_quality=sl_q, stress=st_l, wellbeing=wb,
        sleep_hours=sl_h, exercise_freq=exercise_freq
    )

    deadline_badge = ""
    if dl_days == 1:
        deadline_badge = "\n\n> 🚨 **Deadline tomorrow** — every hour counts today!"
    elif dl_days and dl_days <= 3:
        deadline_badge = f"\n\n> ⚡ **{dl_days} days to deadline** — push for longer sessions today."
    elif dl_days:
        deadline_badge = f"\n\n> 📅 **{dl_days} days to deadline** — steady progress wins."

    focus_md = (
        f"### {emoji}  {focus} Focus &nbsp;·&nbsp; {conf:.0%} confidence\n\n"
        f"{msg}\n\n"
        f"> 📌 **Recommended study time today: {lo}–{hi} hours**  \n"
        f"> *(Adjust your session hours and regenerate anytime)*\n\n"
        f"> 🤖 **AI recommends: {rec_slot.split('(')[0].strip()}** — {rec_reason}."
        f"{deadline_badge}"
    )

    sessions = [{"time": s1_time, "hours": s1h}]
    if use_s2 and s2_time:
        sessions.append({"time": s2_time, "hours": _hrs(s2_hours)})
    if use_s3 and s3_time:
        sessions.append({"time": s3_time, "hours": _hrs(s3_hours)})

    sh, sm = _parse_time(shift_start)
    eh, em = _parse_time(shift_end)

    now_dt   = datetime.now()
    tomorrow = (schedule_for == "Tomorrow — plan my full day ahead")

    if tomorrow:
        sched_h, sched_m = 7, 0   # Tomorrow starts fresh at 7am
    else:
        sched_h, sched_m = now_dt.hour, now_dt.minute

    day_label = "tomorrow" if tomorrow else "today"
    schedule_md = get_schedule(
        focus_level      = focus,
        sessions         = sessions,
        exercise_freq    = exercise_freq,
        part_time_job    = (has_job == "Yes"),
        shift_start_h    = sh, shift_start_m = sm,
        shift_end_h      = eh, shift_end_m   = em,
        distraction      = sh_d,
        recommended_time = rec_slot,
        current_h        = sched_h,
        current_m        = sched_m,
        deadline_days    = dl_days,
        for_tomorrow     = tomorrow,
    )

    # ── Log this entry ─────────────────────────────────────────────────────
    total_hours = sum(
        [s1h] +
        ([_hrs(s2_hours)] if use_s2 else []) +
        ([_hrs(s3_hours)] if use_s3 else [])
    )
    save_entry(focus=focus, study_hours=total_hours, sleep_hours=sl_h,
               stress=st_l, wellbeing=wb, deadline_days=dl_days)

    # ── Export to .txt file ────────────────────────────────────────────────
    export_text = (
        f"STUDENT INTELLIGENT PRODUCTIVITY SCHEDULER\n"
        f"Generated: {now_dt.strftime('%Y-%m-%d %H:%M')}\n"
        f"{'='*50}\n\n"
        f"FOCUS PREDICTION\n{'-'*30}\n"
        f"{focus} Focus — {conf:.0%} confidence\n"
        f"Recommended study: {lo}–{hi} hrs\n"
        f"AI best window: {rec_slot}\n\n"
        f"SCHEDULE\n{'-'*30}\n"
        + schedule_md.replace("**", "").replace("*", "").replace("> ", "")
          .replace("🟢","").replace("🟡","").replace("🔴","")
          .replace("#", "").strip()
    )
    export_path = os.path.join(
        EXPORTS_DIR,
        f"schedule_{now_dt.strftime('%Y%m%d_%H%M%S')}.txt"
    )
    with open(export_path, "w", encoding="utf-8") as f:
        f.write(export_text)

    return focus_md, schedule_md, export_path


# ── Visibility toggles ────────────────────────────────────────────────────────

def toggle_s2(v):    return gr.update(visible=v)
def toggle_s3(v):    return gr.update(visible=v)
def toggle_shift(v): return gr.update(visible=(v == "Yes"))


# ── Progress tab charts ───────────────────────────────────────────────────────

def make_trend_chart(entries):
    BG = "#f3eeff"
    dates, scores, hours = get_trend_data(entries, n=14)
    if not dates:
        fig, ax = plt.subplots(figsize=(9, 3.5), facecolor=BG)
        ax.set_facecolor(BG)
        ax.text(0.5, 0.5,
                "No entries yet\nGenerate your first schedule to start tracking!",
                ha="center", va="center", transform=ax.transAxes,
                color="#a855f7", fontsize=14, fontweight="bold", linespacing=1.9)
        ax.axis("off")
        return fig

    from datetime import datetime as _dt
    date_objs = [_dt.strptime(d, "%Y-%m-%d") for d in dates]
    xs = np.arange(len(date_objs))

    COLOR_MAP  = {1: "#FF6B6B", 2: "#FFD93D", 3: "#6BCB77"}
    FOCUS_LABEL = {1: "Low", 2: "Medium", 3: "High"}
    pt_colors  = [COLOR_MAP.get(s, "#a855f7") for s in scores]

    fig, ax1 = plt.subplots(figsize=(10, 4), facecolor=BG)
    ax1.set_facecolor(BG)

    # Subtle grid
    ax1.yaxis.grid(True, color="#ddd6fe", linewidth=0.8, linestyle="--", zorder=0)
    ax1.set_axisbelow(True)

    # Study hours — ghost bars in background
    if any(h > 0 for h in hours):
        ax2 = ax1.twinx()
        ax2.set_facecolor(BG)
        bar_positions = xs
        ax2.bar(bar_positions, hours, width=0.55, color="#5b00e0",
                alpha=0.25, zorder=1, linewidth=0)
        ax2.set_ylim(0, max(hours) * 3.5)
        ax2.set_ylabel("Study Hours", color="#7c3aed", fontsize=9, labelpad=6)
        ax2.tick_params(axis="y", colors="#7c3aed", labelsize=8)
        for s in ax2.spines.values(): s.set_visible(False)

    # Glow line — draw multiple times with decreasing alpha
    for lw, alpha in [(10, 0.05), (6, 0.1), (4, 0.15), (2.5, 0.9)]:
        ax1.plot(xs, scores, color="#c084fc", linewidth=lw, alpha=alpha,
                 solid_capstyle="round", solid_joinstyle="round", zorder=3)

    # Gradient fill under line (simulate with stacked fills)
    for lvl, color, label in [(3, "#6BCB77", "High"), (2, "#FFD93D", "Medium"), (1, "#FF6B6B", "Low")]:
        mask = [s >= lvl for s in scores]
        if any(mask):
            ax1.fill_between(xs, [s if m else np.nan for s, m in zip(scores, mask)],
                             0.5, alpha=0.06, color=color, zorder=2)
    ax1.fill_between(xs, scores, 0.5, alpha=0.12, color="#a855f7", zorder=2)

    # Points with glow
    for glow_s, glow_a in [(300, 0.08), (150, 0.15), (80, 1.0)]:
        ax1.scatter(xs, scores, c=pt_colors, s=glow_s, zorder=4+glow_s//100,
                    alpha=glow_a, linewidths=0)
    ax1.scatter(xs, scores, c="white", s=20, zorder=10, linewidths=0)

    # Annotate each point
    for x, s, col in zip(xs, scores, pt_colors):
        ax1.annotate(FOCUS_LABEL[s], (x, s),
                     textcoords="offset points", xytext=(0, 12),
                     ha="center", fontsize=7.5, fontweight="bold",
                     color=col, zorder=11)

    # x-axis: date labels
    ax1.set_xticks(xs)
    ax1.set_xticklabels(
        [_dt.strptime(d, "%Y-%m-%d").strftime("%b %d") for d in dates],
        color="#c4b5fd", fontsize=8, rotation=30, ha="right")
    ax1.set_yticks([1, 2, 3])
    ax1.set_yticklabels(["Low", "Med", "High"], color="white", fontsize=9, fontweight="600")
    ax1.set_ylim(0.3, 3.9)
    ax1.set_xlim(-0.5, len(xs) - 0.5)
    ax1.tick_params(axis="x", which="both", length=0)
    ax1.tick_params(axis="y", which="both", length=0)
    for s in ax1.spines.values(): s.set_visible(False)

    ax1.set_title("Focus Trend  —  Last 14 Days",
                  color="white", fontsize=14, fontweight="bold", pad=14)

    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_els = [
        Line2D([0],[0], color="#6BCB77", lw=2.5, label="High"),
        Line2D([0],[0], color="#FFD93D", lw=2.5, label="Medium"),
        Line2D([0],[0], color="#FF6B6B", lw=2.5, label="Low"),
        Patch(facecolor="#5b00e0", alpha=0.4, label="Study hrs"),
    ]
    ax1.legend(handles=legend_els, facecolor="#e9d5ff", edgecolor="#5b00e0",
               labelcolor="white", fontsize=8, loc="upper left",
               framealpha=0.8, borderpad=0.7)

    plt.tight_layout(pad=1.4)
    return fig


def load_progress():
    entries = load_log()
    streak  = get_streak(entries)
    chart   = make_trend_chart(entries)
    table   = build_history_table(entries)

    if streak == 0:
        streak_md = "🔥 No streak yet — generate your first schedule to start!"
    elif streak == 1:
        streak_md = "🔥 **1-day streak** — great start! Come back tomorrow to keep it going."
    else:
        streak_md = f"🔥 **{streak}-day streak!** You're on a roll — keep going! 💜"

    if not table:
        df = pd.DataFrame(columns=["Date","Time","Focus","Study Hrs","Sleep Hrs","Stress","Wellbeing"])
    else:
        df = pd.DataFrame(table, columns=["Date","Time","Focus","Study Hrs","Sleep Hrs","Stress","Wellbeing"])

    return streak_md, chart, df


# ── Model charts ─────────────────────────────────────────────────────────────

def make_accuracy_chart():
    BG = "#f3eeff"
    model_entries = [(lbl, p) for lbl, p in MODEL_MAP.items() if p is not None]
    if not model_entries:
        fig, ax = plt.subplots(figsize=(6, 3), facecolor=BG)
        ax.text(0.5, 0.5, "No models found.\nRun train_model.py first.",
                ha="center", va="center", transform=ax.transAxes,
                color="#a855f7", fontsize=13, fontweight="bold")
        ax.set_facecolor(BG); ax.axis("off"); return fig

    n = len(model_entries)
    fig, axes = plt.subplots(1, n, figsize=(4.5 * n, 4.5), facecolor=BG)
    if n == 1: axes = [axes]

    DONUT_COLORS = ["#7c3aed", "#2563eb", "#059669"]  # purple, blue, green per model
    RING_BG      = "#e9d5ff"
    SHORT_NAMES  = ["Model A\nReal Survey", "Model B\nSynthetic", "Model C\nCombined ✅"]

    for idx, (ax, (lbl, p)) in enumerate(zip(axes, model_entries)):
        acc  = p["accuracy"]
        pct  = acc * 100
        col  = DONUT_COLORS[idx % len(DONUT_COLORS)]
        rest = 100 - pct

        ax.set_facecolor(BG)
        ax.axis("equal")

        # Outer glow ring (very faint)
        glow = plt.matplotlib.patches.Wedge(
            (0.5, 0.5), 0.47, 0, 360, width=0.13,
            transform=ax.transAxes, color=col, alpha=0.08, zorder=1)
        ax.add_patch(glow)

        # Background ring
        bg_ring = plt.matplotlib.patches.Wedge(
            (0.5, 0.5), 0.44, 0, 360, width=0.10,
            transform=ax.transAxes, color=RING_BG, zorder=2)
        ax.add_patch(bg_ring)

        # Progress arc
        arc = plt.matplotlib.patches.Wedge(
            (0.5, 0.5), 0.44, 90, 90 - 3.6 * pct, width=0.10,
            transform=ax.transAxes, color=col, zorder=3,
            capstyle="round")
        ax.add_patch(arc)

        # Central text
        ax.text(0.5, 0.56, f"{pct:.1f}%",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=22, fontweight="800", color="white", zorder=5)
        ax.text(0.5, 0.44, "accuracy",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=9, color="#c4b5fd", zorder=5)

        # Model name below
        short = SHORT_NAMES[idx] if idx < len(SHORT_NAMES) else lbl
        ax.text(0.5, -0.04, short,
                ha="center", va="top", transform=ax.transAxes,
                fontsize=10, fontweight="700", color="white",
                linespacing=1.5)

        # Small badge if best model
        if idx == len(model_entries) - 1 or pct == max(p2["accuracy"] * 100 for _, p2 in model_entries):
            ax.text(0.5, 0.96, "★ In Use",
                    ha="center", va="top", transform=ax.transAxes,
                    fontsize=8, fontweight="700", color=col)

        for spine in ax.spines.values(): spine.set_visible(False)
        ax.set_xticks([]); ax.set_yticks([])

    fig.suptitle("Model Accuracy — Random Forest Classifiers",
                 color="white", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout(pad=2.0)
    return fig


def make_feat_chart():
    BG = "#f3eeff"
    p = PREDICT_MODEL
    if p is None:
        fig, ax = plt.subplots(figsize=(6, 3), facecolor=BG)
        ax.set_facecolor(BG)
        ax.text(0.5, 0.5, "No models found.",
                ha="center", va="center", transform=ax.transAxes,
                color="#a855f7", fontsize=13)
        ax.axis("off"); return fig

    model = p["model"]; feats = p["feature_names"]
    imps  = model.feature_importances_
    idx   = np.argsort(imps)   # ascending — smallest at top when plotted horizontally
    labels = [feats[i].replace("_", " ").title() for i in idx]
    values = imps[idx]
    n = len(labels)

    fig, ax = plt.subplots(figsize=(10, max(5, n * 0.55)), facecolor=BG)
    ax.set_facecolor(BG)

    # Subtle grid
    ax.xaxis.grid(True, color="#ddd6fe", linewidth=0.7, linestyle="--", zorder=0)
    ax.set_axisbelow(True)

    # Gradient-style bars: interpolate purple → pink based on value
    LOW_COL  = np.array([0.49, 0.13, 0.93])  # #7c3aed
    HIGH_COL = np.array([0.94, 0.33, 0.72])  # #ef54b8
    norm_vals = (values - values.min()) / max(values.max() - values.min(), 1e-9)
    bar_colors = [LOW_COL + (HIGH_COL - LOW_COL) * v for v in norm_vals]

    bars = ax.barh(labels, values, color=bar_colors, height=0.62,
                   zorder=3, linewidth=0)

    # Rounded-end caps (draw a dot at the end of each bar)
    for bv, bc, bar in zip(values, bar_colors, bars.patches):
        y = bar.get_y() + bar.get_height() / 2
        ax.plot(bv, y, "o", ms=7.5, color=bc, zorder=5)

    # Value labels
    for bar, val in zip(bars.patches, values):
        ax.text(val + values.max() * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=8.5,
                fontweight="600", color="#e0cffc", zorder=6)

    # Highlight top 3 with a star
    top3_idx = np.argsort(values)[-3:]  # after argsort ascending, top3 are last 3
    for ti in top3_idx:
        bar = bars.patches[ti]
        ax.text(-values.max() * 0.01,
                bar.get_y() + bar.get_height() / 2,
                "★", ha="right", va="center", fontsize=10,
                color="#FFD700", zorder=6)

    ax.set_xlim(0, values.max() * 1.22)
    ax.tick_params(axis="y", colors="white", labelsize=9, length=0)
    ax.tick_params(axis="x", colors="#9d7fd8", labelsize=8, length=0)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.set_xlabel("Importance Score", fontsize=10, color="#c4b5fd", labelpad=8)
    ax.set_title(
        f"Feature Importances  ·  {p['name']}",
        color="white", fontsize=14, fontweight="bold", pad=14)

    from matplotlib.patches import Patch
    ax.legend(
        handles=[
            Patch(color="#7c3aed", label="Lower importance"),
            Patch(color="#ef54b8", label="Higher importance"),
            Patch(color="#FFD700", label="★ Top 3 features"),
        ],
        facecolor="#e9d5ff", edgecolor="#5b00e0",
        labelcolor="white", fontsize=8, loc="lower right",
        framealpha=0.8)

    plt.tight_layout(pad=1.4)
    return fig


def load_charts():
    lines=[
        f"{lbl:<45} {p['accuracy']:.2%}" if p else f"{lbl:<45} Not trained"
        for lbl,p in MODEL_MAP.items()
    ]
    return make_accuracy_chart(), make_feat_chart(), "\n".join(lines)


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
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


# ── Gradio UI ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="Student Intelligent Productivity Scheduler") as demo:

    gr.HTML("""
    <div class="hero">
      <h1>🎓 Student Intelligent Productivity Scheduler</h1>
      <p>Answer a few questions → AI predicts your focus → get a personalised day plan, starting from right now</p>
    </div>
    """)

    # ══ Tab 1: My Schedule ════════════════════════════════════════════════════
    with gr.Tab("📅 My Schedule"):

        # ── Sleep & Wellbeing ──────────────────────────────────────────────
        gr.HTML('<span class="card-title">🌙 Sleep & Wellbeing</span>')
        with gr.Group(elem_classes="card"):
            with gr.Row():
                sleep_hours   = gr.Dropdown(SLEEP_H_OPTS, value="7 hrs",
                    label="🛌 Hours of sleep last night")
                sleep_quality = gr.Dropdown(QUALITY_OPTS, value="3 — Okay (decent enough)",
                    label="😴 Sleep quality")
            with gr.Row():
                stress_level  = gr.Dropdown(STRESS_OPTS, value="5-6 — Moderate stress",
                    label="😰 Stress level right now")
                wellbeing     = gr.Dropdown(WELLBEING_OPTS, value="5-6 — Average, okay",
                    label="🌱 Overall wellbeing today")

        # ── Daily Habits ───────────────────────────────────────────────────
        gr.HTML('<span class="card-title">📱 Daily Habits</span>')
        with gr.Group(elem_classes="card"):
            with gr.Row():
                screen_time   = gr.Dropdown(SCREEN_OPTS, value="2 hrs",
                    label="📱 Social media & streaming today")
                exercise_freq = gr.Dropdown(EXERCISE_OPTS, value="1–2 days per week",
                    label="🏃 Exercise frequency")
            with gr.Row():
                distraction = gr.Dropdown(DISTRACTION_OPTS,
                    value="Sometimes — moderate distraction",
                    label="📵 Phone distraction while studying?")
                has_job = gr.Radio(["No", "Yes"], value="No",
                    label="💼 Do you have a part-time job?")

        with gr.Group(visible=False, elem_classes="shift-box") as shift_box:
            gr.HTML('<p style="color:#fbbf24;font-size:0.86rem;font-weight:700;margin:0 0 10px;">⏱️ Your work shift — blocked in your schedule</p>')
            with gr.Row():
                shift_start = gr.Dropdown(SHIFT_OPTS, value="17:00", label="Shift starts at")
                shift_end   = gr.Dropdown(SHIFT_OPTS, value="21:00", label="Shift ends at")

        has_job.change(fn=toggle_shift, inputs=has_job, outputs=shift_box)

        # ── Deadline ───────────────────────────────────────────────────────
        gr.HTML('<span class="card-title">⏰ Upcoming Deadline</span>')
        with gr.Group(elem_classes="deadline-box"):
            deadline = gr.Dropdown(DEADLINE_OPTS, value="No deadline soon",
                label="📅 Do you have an exam or assignment due soon?")

        # ── Study Plan ─────────────────────────────────────────────────────
        gr.HTML('<span class="card-title">📚 Today\'s Study Plan</span>')
        gr.HTML('<p style="color:rgba(220,190,255,0.6);font-size:0.82rem;margin:-6px 0 8px;">Session 1 required. Add more for split study days.</p>')

        with gr.Group(elem_classes="card"):
            gr.HTML('<p style="color:#d8aaff;font-size:0.88rem;font-weight:700;margin:0 0 8px;">📖 Session 1 — main study block</p>')
            with gr.Row():
                s1_time  = gr.Dropdown(PEAK_OPTS, value="Morning (6am – 12pm)",
                    label="⏰ Time of day")
                s1_hours = gr.Dropdown(SESSION_H_OPTS, value="2 hrs",
                    label="🕐 How many hours?")

        use_s2 = gr.Checkbox(label="➕  Add a second study session today", value=False)
        with gr.Group(visible=False, elem_classes="session-box") as s2_box:
            gr.HTML('<p style="color:#d8aaff;font-size:0.88rem;font-weight:700;margin:0 0 8px;">📖 Session 2</p>')
            with gr.Row():
                s2_time  = gr.Dropdown(PEAK_OPTS, value="Afternoon (12pm – 5pm)",
                    label="⏰ Time of day")
                s2_hours = gr.Dropdown(SESSION_H_OPTS, value="1.5 hrs",
                    label="🕐 How many hours?")

        use_s3 = gr.Checkbox(label="➕  Add a third study session today", value=False)
        with gr.Group(visible=False, elem_classes="session-box") as s3_box:
            gr.HTML('<p style="color:#d8aaff;font-size:0.88rem;font-weight:700;margin:0 0 8px;">📖 Session 3</p>')
            with gr.Row():
                s3_time  = gr.Dropdown(PEAK_OPTS, value="Evening (5pm – 10pm)",
                    label="⏰ Time of day")
                s3_hours = gr.Dropdown(SESSION_H_OPTS, value="1 hr",
                    label="🕐 How many hours?")

        use_s2.change(fn=toggle_s2, inputs=use_s2, outputs=s2_box)
        use_s3.change(fn=toggle_s3, inputs=use_s3, outputs=s3_box)

        # ── Generate ───────────────────────────────────────────────────────
        gr.HTML('<hr class="my-hr">')
        schedule_for = gr.Radio(
            ["Today (starting from now)", "Tomorrow — plan my full day ahead"],
            value="Today (starting from now)",
            label="🗓️  Generate schedule for"
        )
        predict_btn = gr.Button("✨  Predict My Focus & Generate My Schedule",
                                elem_id="predict-btn")
        gr.HTML('<hr class="my-hr">')

        # ── Results ────────────────────────────────────────────────────────
        gr.HTML('<span class="card-title">🔮 Your Results</span>')
        focus_out    = gr.Markdown(
            value="*Press the button above — your focus prediction will appear here.*",
            elem_id="focus-result")
        schedule_out = gr.Markdown(
            value="*Your personalised schedule will appear here...*",
            elem_id="schedule-out")

        gr.HTML('<hr class="my-hr">')
        gr.HTML('<span class="card-title">💾 Export Your Schedule</span>')
        export_file = gr.File(label="📄 Download as .txt", visible=True,
                              interactive=False)

        predict_btn.click(
            fn=predict_and_schedule,
            inputs=[
                sleep_hours, sleep_quality, stress_level, wellbeing,
                screen_time, exercise_freq, distraction,
                has_job, shift_start, shift_end,
                deadline,
                schedule_for,
                s1_time, s1_hours,
                use_s2, s2_time, s2_hours,
                use_s3, s3_time, s3_hours,
            ],
            outputs=[focus_out, schedule_out, export_file],
        )

    # ══ Tab 2: Progress ═══════════════════════════════════════════════════════
    with gr.Tab("📈 My Progress"):
        refresh_btn = gr.Button("🔄 Refresh Progress", variant="secondary")

        streak_out  = gr.Markdown(elem_classes="streak-badge")
        trend_chart = gr.Plot(label="Focus Trend")
        history_df  = gr.DataFrame(
            label="Session History (last 30 days)",
            headers=["Date","Time","Focus","Study Hrs","Sleep Hrs","Stress","Wellbeing"],
            interactive=False,
        )

        def _refresh_progress():
            return load_progress()

        refresh_btn.click(fn=_refresh_progress,
                          outputs=[streak_out, trend_chart, history_df])
        demo.load(fn=_refresh_progress,
                  outputs=[streak_out, trend_chart, history_df])

    # ══ Tab 3: Research Insights ══════════════════════════════════════════════
    with gr.Tab("📊 Research Insights"):
        gr.Markdown("""
        ### Model Accuracy Comparison
        Three Random Forest models trained for this dissertation.
        The app uses **Model C (Combined)** automatically.

        > **Model A** — 1,500+ real LJMU student survey responses  
        > **Model B** — synthetic student habits dataset (1,001 rows)  
        > **Model C** — both combined ✅ (used for predictions)
        """)
        with gr.Row():
            acc_plot  = gr.Plot(label="Accuracy Comparison")
            feat_plot = gr.Plot(label="Feature Importances")
        acc_table = gr.Textbox(label="Accuracy Summary", lines=5, interactive=False)
        gr.Button("🔄 Refresh Charts", variant="secondary").click(
            fn=load_charts, outputs=[acc_plot, feat_plot, acc_table])
        demo.load(fn=load_charts, outputs=[acc_plot, feat_plot, acc_table])

    # ══ Tab 4: About ══════════════════════════════════════════════════════════
    with gr.Tab("ℹ️ About"):
        gr.Markdown("""
        ## About This App
        Final-year BSc Computer Science dissertation — **Liverpool John Moores University, 2026**.

        ### What it does
        1. You answer questions about today's habits
        2. ML model predicts **High / Medium / Low focus**
        3. AI recommends the **optimal study window** for your habits
        4. Dynamic scheduler builds your day from **right now**, not 6am
        5. **Rescue Mode** activates on Low focus days
        6. Your daily progress is **logged automatically** — view it in 📈 My Progress

        ### Schedule intelligence
        | Focus | Work Block | Break | Long Break |
        |-------|-----------|-------|------------|
        | 🟢 High   | 90 min deep work | 15 min | 30 min |
        | 🟡 Medium | 50 min focused   | 10 min | 20 min |
        | 🔴 Low 🆘 | 25 min sprint + reset | 5 min | 15 min |

        ### How to run
        ```
        py app/main.py
        ```
        Open **http://127.0.0.1:7860** · check terminal for public share link.

        ---
        *Developed by Arwa Daaboul LJMU Computer Science · 2026*
        """)

# ── Launch ───────────────────────────────────────────────
if __name__ == "__main__":
    demo.launch(inbrowser=True, share=SHARE, css=CSS)

"""
scheduler.py — Student Intelligent Productivity Scheduler
==========================================================
Generates a genuinely personalised daily schedule by dynamically
building time blocks based on:

  - Predicted focus level  (High / Medium / Low)
  - Up to 3 independent study sessions, each with own time slot + duration
  - Part-time job: shift start & end are BLOCKED in the schedule
  - Exercise frequency
  - Phone distraction level

Block sizes adapt to focus:
  High   → 90 min deep work · 15 min short break · 30 min long break
  Medium → 50 min focus     · 10 min short break · 20 min long break
  Low    → 25 min sprint    ·  5 min short break · 15 min long break
"""

from datetime import datetime, timedelta

# ── Focus config ──────────────────────────────────────────────────────────────

FOCUS_CONFIG = {
    "High": {
        "emoji":      "🟢",
        "label":      "High Focus Day",
        "work_min":   90,
        "break_min":  15,
        "long_break": 30,
        "tip": (
            "Your brain is firing on all cylinders. Protect your peak hours for the "
            "hardest tasks — phone off, single-task only, no notifications."
        ),
    },
    "Medium": {
        "emoji":      "🟡",
        "label":      "Moderate Focus Day",
        "work_min":   50,
        "break_min":  10,
        "long_break": 20,
        "tip": (
            "Solid focus today — use Pomodoro-style blocks. Write one clear goal "
            "before each session and minimise tab-switching."
        ),
    },
    "Low": {
        "emoji":      "🔴",
        "label":      "Low Focus Day — Rescue Mode Active 🆘",
        "work_min":   25,
        "break_min":   5,
        "long_break": 15,
        "tip": (
            "Rescue mode is active. Short 25-min sprints on the simplest tasks only — "
            "reviewing notes, flashcards, or planning. Avoid reading new material or writing "
            "from scratch. A 20-min reset before each session will help your brain shift gears."
        ),
        "rescue_tip": (
            "Take this reset seriously — studies show even a 10–20 min rest before studying "
            "can double retention on a low-energy day."
        ),
    },
}

SESSION_START = {
    "Morning (6am – 12pm)":     8,
    "Afternoon (12pm – 5pm)":  13,
    "Evening (5pm – 10pm)":    18,
    "Late Night (10pm – 6am)": 22,
}

SESSION_LABEL = {
    "Morning (6am – 12pm)":     "Morning session",
    "Afternoon (12pm – 5pm)":   "Afternoon session",
    "Evening (5pm – 10pm)":     "Evening session",
    "Late Night (10pm – 6am)":  "Late-night session",
}

EXERCISE_REGULAR = {"3-4 days per week", "5+ days per week"}

DISTRACTION_TIPS = {
    "Never":      "🏆 Phone-free studying mastered — leading by example!",
    "Rarely":     "✅ Great phone discipline — keep it up.",
    "Sometimes":  "📱 Phone tip: silence it and check only during breaks.",
    "Often":      "📵 Phone tip: use an app blocker (Forest, Cold Turkey) during work blocks.",
    "Constantly": "🚨 Phone tip: move your phone to another room during every study block.",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0") or "12:00 AM"

def _adv(dt: datetime, mins: int) -> datetime:
    return dt + timedelta(minutes=int(mins))

def _hhmm(hour: int, minute: int = 0) -> datetime:
    """Create a datetime on our dummy date."""
    return datetime(2000, 1, 1, hour % 24, minute % 60)

def _total_mins(dt: datetime) -> int:
    """Minutes since midnight — safe even past midnight (next day)."""
    return dt.hour * 60 + dt.minute


def _build_study_blocks(start_dt, study_mins, cfg, session_label="", block_num_start=1):
    """
    Dynamically fill `study_mins` minutes of study blocks.
    Returns (list_of_rows, end_dt, next_block_num).
    """
    rows = []
    now = start_dt
    work_min   = cfg["work_min"]
    break_min  = cfg["break_min"]
    long_break = cfg["long_break"]
    focus      = cfg.get("_focus", "Medium")

    suffix = f" ({session_label})" if session_label else ""
    rows.append((now, "⏰", f"**Study session begins{suffix}**"))

    mins_done   = 0
    block_count = 0
    block_num   = block_num_start

    while mins_done < study_mins:
        remaining  = study_mins - mins_done
        this_block = min(work_min, remaining)

        if focus == "High":
            lbl = f"Deep Work Block {block_num} — {this_block} min · single task, phone away"
        elif focus == "Medium":
            lbl = f"Focused Study Block {block_num} — {this_block} min · clear goal set"
        else:
            lbl = f"Focus Sprint {block_num} — {this_block} min · one small task only"

        rows.append((now, "▶", lbl))
        now         = _adv(now, this_block)
        mins_done  += this_block
        block_count += 1
        block_num   += 1

        if mins_done >= study_mins:
            break

        if block_count % 2 == 0:
            rows.append((now, "☕", f"Long break — {long_break} min · away from desk, no screens"))
            now = _adv(now, long_break)
        else:
            rows.append((now, "🔄", f"Short break — {break_min} min · stand up, drink water"))
            now = _adv(now, break_min)

    total_h = study_mins / 60
    rows.append((now, "✅", f"Session complete — {total_h:.1f} h done 🎉"))
    return rows, now, block_num


# ── Main entry point ──────────────────────────────────────────────────────────

def get_schedule(
    focus_level:      str,
    sessions:         list,
    exercise_freq:    str  = "1–2 days per week",
    part_time_job:    bool = False,
    shift_start_h:    int  = 17,
    shift_start_m:    int  = 0,
    shift_end_h:      int  = 21,
    shift_end_m:      int  = 0,
    distraction:      str  = "Sometimes",
    recommended_time: str  = "",
    current_h:        int  = 8,
    current_m:        int  = 0,
    deadline_days:    int | None = None,
    for_tomorrow:     bool = False,
) -> str:
    """
    Build and return a Markdown schedule string.

    Parameters
    ----------
    focus_level   : 'High', 'Medium', or 'Low'
    sessions      : list of dicts with 'time' (PEAK_OPTS key) and 'hours' (float)
    exercise_freq : exercise frequency string
    part_time_job : bool — if True, shift_start/end are blocked off
    shift_start_h/m : shift start in 24h time
    shift_end_h/m   : shift end in 24h time
    distraction   : short string key for tip lookup
    """
    cfg = dict(FOCUS_CONFIG.get(focus_level, FOCUS_CONFIG["Medium"]))
    cfg["_focus"] = focus_level

    # Filter out empty / skipped sessions
    valid = [s for s in sessions if s.get("hours", 0) > 0 and s.get("time", "None") != "None"]
    if not valid:
        return "⚠️ Please add at least one study session above."

    # Sort sessions by their start hour
    valid.sort(key=lambda s: SESSION_START.get(
        str(s["time"]).split(";")[0].strip(), 99))

    total_h = sum(s["hours"] for s in valid)

    # Shift as datetime range
    shift_start_dt = _hhmm(shift_start_h, shift_start_m) if part_time_job else None
    shift_end_dt   = _hhmm(shift_end_h,   shift_end_m)   if part_time_job else None

    # ── Current real time as anchor ────────────────────────────────────
    real_now = _hhmm(current_h, current_m)
    # Schedule starts 5 min from now at minimum
    now = _adv(real_now, 5)

    # Opening line
    rows = []
    if for_tomorrow:
        rows.append((now, "🗓️", f"**Tomorrow's plan — starting at {_fmt(now)}**"))
    else:
        rows.append((now, "🕐", f"**Schedule starts from now — {_fmt(now)}**"))
    now = _adv(now, 2)

    # Morning context lines (only if generating early)
    if current_h < 8:
        rows.append((now, "🌅", "Wake up — stretch, hydrate, morning routine"))
        now = _adv(now, 20)
        rows.append((now, "🍳", "Breakfast — eat away from your desk"))
        now = _adv(now, 30)
    elif current_h < 11:
        rows.append((now, "☕", "Morning coffee / tea & today’s plan — 5 min"))
        now = _adv(now, 10)
    elif current_h < 14:
        rows.append((now, "🍽️", "Grab lunch if you haven’t yet — eat away from desk"))
        now = _adv(now, 30)
    elif current_h < 18:
        rows.append((now, "💪", "Afternoon energy — stretch, water, then let’s go"))
        now = _adv(now, 10)
    else:
        rows.append((now, "🌙", "Evening mode — tidy your space & silence notifications"))
        now = _adv(now, 10)

    exercise_added = False
    block_num      = 1

    # ── Loop over each study session ──────────────────────────────────────
    for i, sess in enumerate(valid):
        t_key      = str(sess["time"]).split(";")[0].strip()
        s_hour     = SESSION_START.get(t_key, 8)
        s_label    = SESSION_LABEL.get(t_key, "Study session")
        study_mins = int(float(sess["hours"]) * 60)
        session_dt = _hhmm(s_hour)

        # If this session's slot has already passed → start from real now
        # (skip this adjustment when planning for tomorrow — all slots are fresh)
        if not for_tomorrow and session_dt <= real_now:
            session_dt = _adv(real_now, 10)
            rows.append((now, "⏩",
                f"⚠️ {t_key} slot has passed — adjusting to start as soon as possible"))

        # ── Gap filler between sessions ───────────────────────────────────
        if i > 0 and session_dt > now:
            gap_mins = (session_dt.hour - now.hour) * 60 + (session_dt.minute - now.minute)

            # Insert meal if gap > 1h
            if gap_mins >= 60:
                rows.append((_adv(now, 10), "🍽️",
                             "Meal break — eat well and step away from your desk"))
                now = _adv(now, min(55, gap_mins // 2))

            # Insert exercise in gap if not added yet & gap large enough
            if not exercise_added and gap_mins >= 90:
                if exercise_freq in EXERCISE_REGULAR:
                    rows.append((now, "🏃", "Exercise session — 45 min · you train regularly!"))
                    now = _adv(now, 45)
                elif "1" in exercise_freq or "2" in exercise_freq:
                    rows.append((now, "🚶", "Light walk / movement break — 20 min"))
                    now = _adv(now, 20)
                exercise_added = True

            # Rest / free time
            remaining_gap = (session_dt - now)
            if remaining_gap.total_seconds() > 900:  # > 15 min
                rows.append((now, "🛋️", "Free time / rest — recharge before next session"))

        # Snap to session start
        now = session_dt

        # ── Part-time shift: if this session overlaps shift → warn & skip ─
        if part_time_job and shift_start_dt and shift_end_dt:
            sess_end_dt = _adv(session_dt, study_mins)
            if session_dt < shift_end_dt and sess_end_dt > shift_start_dt:
                rows.append((now, "⚠️",
                             f"**Scheduling conflict:** Session overlaps your work shift "
                             f"({_fmt(shift_start_dt)}–{_fmt(shift_end_dt)}). "
                             f"Consider moving this session."))
                continue

        # ── 🆘 Rescue Mode: recovery reset before study block ─────────────
        if focus_level == "Low":
            rows.append((now, "🆘", "**Rescue Mode — Recovery Reset (20 min)**"))
            now = _adv(now, 2)
            rows.append((now, "🛌",
                "Micro-nap — lie down, close eyes, set an alarm for 20 min"))
            now = _adv(now, 20)   # ← was 10, fixed to 20
            rows.append((now, "🧘",
                "Breathe & move — 4-7-8 breathing or a gentle stretch (5 min)"))
            now = _adv(now, 5)
            rows.append((now, "💧",
                "Hydrate & set intention — water + write ONE goal for this session"))
            now = _adv(now, 3)

        # ── Build study blocks — start from `now`, not session_dt ─────────
        # (now may be ahead of session_dt if rescue mode or adjustments applied)
        use_label  = s_label if len(valid) > 1 else ""
        block_start = now  # always use the advanced `now` pointer
        s_rows, now, block_num = _build_study_blocks(
            block_start, study_mins, cfg,
            session_label=use_label,
            block_num_start=block_num,
        )
        rows.extend(s_rows)

    # ── Part-time shift block ─────────────────────────────────────────────
    if part_time_job and shift_start_dt:
        rows.append((_adv(now, 15), "💼",
                     f"**Work shift** — {_fmt(shift_start_dt)} to {_fmt(shift_end_dt)} "
                     f"· no studying during this time"))
        now = _adv(shift_end_dt, 15)

    # ── Exercise after study (if not already added) ───────────────────────
    if not exercise_added:
        now = _adv(now, 15)
        if exercise_freq in EXERCISE_REGULAR:
            rows.append((now, "🏃", "Exercise — 30–45 min · you train regularly, keep it up!"))
            now = _adv(now, 45)
        elif "1" in exercise_freq or "2" in exercise_freq:
            rows.append((now, "🚶", "Light walk — 20 min · movement helps recovery"))
            now = _adv(now, 20)
        else:
            rows.append((now, "🧘", "Gentle stretch — even 10 min helps"))
            now = _adv(now, 10)

    # ── Evening meal ──────────────────────────────────────────────────────
    now = _adv(now, 10)
    rows.append((now, "🍽️", "Dinner / evening meal — eat properly, away from desk"))
    now = _adv(now, 45)

    # ── Wind down ─────────────────────────────────────────────────────────
    rows.append((now, "📵", "Screen-free wind down — no studying or social media"))
    now = _adv(now, 30)
    rows.append((now, "📝", "Tomorrow prep — write 3 goals for tomorrow"))
    now = _adv(now, 15)
    rows.append((now, "😴", "Sleep — aim for 7–8 hours"))

    # ── Build Markdown ────────────────────────────────────────────────────
    sess_labels = " + ".join(
        f"{s['hours']:.1f}h {SESSION_LABEL.get(str(s['time']).split(';')[0].strip(), 'session')}"
        for s in valid
    )

    # AI recommendation badge in header
    rec_line = ""
    if recommended_time:
        rec_line = f"\n> 🤖 **AI recommends:** Best study window today is **{recommended_time}**\n"

    # Rescue mode banner
    rescue_banner = ""
    if focus_level == "Low":
        rescue_banner = (
            "\n> 🆘 **Rescue Mode is active** — 20-min recovery resets have been added "
            "before each study session. Short sprints only today.  \n"
            f"> 💜 *{cfg.get('rescue_tip', '')}*\n"
        )

    header = (
        f"## {cfg['emoji']} Your Personalised Schedule — **{cfg['label']}**\n"
        f"*{sess_labels} · Total: {total_h:.1f} h*\n\n"
    )
    table = "| Time | Activity |\n|------|----------|\n"
    for row_time, icon, label in rows:
        table += f"| {_fmt(row_time)} | {icon} {label} |\n"

    tip  = f"\n> 💡 **Focus tip:** {cfg['tip']}\n"
    dist = f"\n> {DISTRACTION_TIPS.get(distraction, '')}\n" if distraction in DISTRACTION_TIPS else ""

    # Deadline urgency note
    deadline_note = ""
    if deadline_days is not None:
        if deadline_days == 1:
            deadline_note = "\n> 🚨 **Deadline tomorrow!** Every hour counts — prioritise ruthlessly and avoid anything non-essential tonight.\n"
        elif deadline_days <= 3:
            deadline_note = f"\n> ⚡ **{deadline_days} days to deadline** — aim for longer sessions and review high-priority material first.\n"
        elif deadline_days <= 7:
            deadline_note = f"\n> 📌 **{deadline_days} days to deadline** — good time to consolidate notes and practice past papers.\n"
        else:
            deadline_note = f"\n> 🗓️ **{deadline_days} days to deadline** — steady progress now beats last-minute cramming.\n"

    return header + rec_line + rescue_banner + table + tip + dist + deadline_note

"""
log_manager.py — Daily Schedule Log for Student Productivity Scheduler
=======================================================================
Saves each schedule generation as a JSON log entry.
Provides streak, trend, and history helpers for the Progress tab.
"""

import json
import os
from datetime  import date, datetime, timedelta
from pathlib   import Path

# ── Storage location ──────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
LOG_FILE = DATA_DIR / "schedule_log.json"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Read / write ───────────────────────────────────────────────────────────────

def load_log() -> list[dict]:
    """Return all log entries, newest first."""
    _ensure_dir()
    if not LOG_FILE.exists():
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return sorted(data, key=lambda e: e["date"] + e.get("time", ""), reverse=True)
    except Exception:
        return []


def save_entry(
    focus:          str,
    study_hours:    float,
    sleep_hours:    float  = 7.0,
    stress:         int    = 5,
    wellbeing:      int    = 5,
    deadline_days:  int | None = None,
) -> None:
    """Append a new entry to the log file."""
    _ensure_dir()
    entries = load_log()
    today   = date.today().isoformat()
    now_str = datetime.now().strftime("%H:%M")

    # Replace today's entry if it already exists (one per day)
    entries = [e for e in entries if e.get("date") != today]
    entries.append({
        "date":          today,
        "time":          now_str,
        "focus":         focus,
        "study_hours":   round(study_hours, 1),
        "sleep_hours":   round(sleep_hours, 1),
        "stress":        stress,
        "wellbeing":     wellbeing,
        "deadline_days": deadline_days,
    })

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


# ── Analytics ─────────────────────────────────────────────────────────────────

def get_streak(entries: list[dict]) -> int:
    """Consecutive days ending today (or yesterday) that have an entry."""
    if not entries:
        return 0
    today = date.today()
    days  = sorted({date.fromisoformat(e["date"]) for e in entries}, reverse=True)
    if not days or days[0] < today - timedelta(days=1):
        return 0
    streak = 0
    check  = today if days[0] == today else today - timedelta(days=1)
    for d in days:
        if d == check:
            streak += 1
            check  -= timedelta(days=1)
        else:
            break
    return streak


FOCUS_NUM = {"Low": 1, "Medium": 2, "High": 3}


def get_trend_data(entries: list[dict], n: int = 14) -> tuple[list, list, list]:
    """
    Returns (dates, focus_scores, study_hours) for the last n entries,
    oldest first — ready for a matplotlib chart.
    """
    recent = sorted(entries, key=lambda e: e["date"])[-n:]
    dates  = [e["date"] for e in recent]
    scores = [FOCUS_NUM.get(e["focus"], 0) for e in recent]
    hours  = [e.get("study_hours", 0) for e in recent]
    return dates, scores, hours


def build_history_table(entries: list[dict], n: int = 30) -> list[list]:
    """Return a list-of-lists table for the most recent n entries."""
    rows = []
    for e in entries[:n]:
        rows.append([
            e["date"],
            e.get("time", "—"),
            e.get("focus", "—"),
            f"{e.get('study_hours', '—')} hrs",
            f"{e.get('sleep_hours', '—')} hrs",
            str(e.get("stress", "—")) + "/10",
            str(e.get("wellbeing", "—")) + "/10",
        ])
    return rows

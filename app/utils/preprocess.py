"""
preprocess.py
-------------
Loads and cleans both student datasets, engineers a shared 'focus_level'
target label (Low / Medium / High), and returns feature/label arrays for
three training scenarios:
  - load_real()       -> real survey data only (71 rows, richer features)
  - load_synthetic()  -> synthetic dataset only (1001 rows, numeric features)
  - load_combined()   -> merged on shared features (~1072 rows)
"""

import os
import pandas as pd
import numpy as np

# ── Path resolution ──────────────────────────────────────────────────────────
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

REAL_CSV = os.path.join(
    PROJECT_DIR,
    "Daily Habits and Focus Level Study for Students.csv",
)
SYNTH_CSV = os.path.join(PROJECT_DIR, "student_habits_performance.csv")


# ── Encoding helpers ──────────────────────────────────────────────────────────

def _encode_sleep_range(val):
    """Convert text sleep ranges to numeric midpoints."""
    mapping = {
        "less than 5 hours": 4.5,
        "5-6 hours": 5.5,
        "6-7 hours": 6.5,
        "7-8 hours": 7.5,
        "8+ hours": 8.5,
    }
    if pd.isna(val):
        return 6.5  # fallback to average
    return mapping.get(str(val).strip().lower(), 6.5)


def _encode_screen_time(val):
    """Convert text screen-time ranges to numeric midpoints."""
    mapping = {
        "less than 1 hour": 0.5,
        "1-2 hours": 1.5,
        "2-4 hours": 3.0,
        "4-6 hours": 5.0,
        "6+ hours": 7.0,
    }
    if pd.isna(val):
        return 3.0
    return mapping.get(str(val).strip().lower(), 3.0)


def _encode_study_range(val):
    """Convert text study-time ranges to numeric midpoints."""
    mapping = {
        "less than 2 hours": 1.0,
        "2-4 hours": 3.0,
        "4-6 hours": 5.0,
        "6-8 hours": 7.0,
        "8+ hours": 9.0,
    }
    if pd.isna(val):
        return 3.0
    return mapping.get(str(val).strip().lower(), 3.0)


def _encode_distraction(val):
    """Maps phone distraction frequency to 1-4 scale."""
    mapping = {
        "never": 0,
        "rarely": 1,
        "sometimes": 2,
        "often": 3,
        "constantly": 4,
    }
    if pd.isna(val):
        return 2
    return mapping.get(str(val).strip().lower(), 2)


def _encode_exercise_real(val):
    """Maps exercise frequency text to a numeric scale 0-5."""
    mapping = {
        "rarely / never": 0,
        "1-2 days per week": 1,
        "3-4 days per week": 3,
        "5+ days per week": 5,
    }
    if pd.isna(val):
        return 2
    return mapping.get(str(val).strip().lower(), 2)


def _encode_sleep_quality(val):
    """Strips numeric prefix from sleep quality strings."""
    if pd.isna(val):
        return 3
    val_str = str(val).strip()
    try:
        return int(val_str[0])  # e.g. "3 - Average" → 3
    except (ValueError, IndexError):
        return 3


def _focus_from_deep_work(rating):
    """Bin 1-5 Deep Work self-rating into Low / Medium / High."""
    if rating <= 2:
        return "Low"
    elif rating == 3:
        return "Medium"
    else:
        return "High"


def _focus_from_exam_score(score):
    """Bin exam score (0-100) into Low / Medium / High."""
    if score < 55:
        return "Low"
    elif score < 75:
        return "Medium"
    else:
        return "High"


# ── Dataset loaders ───────────────────────────────────────────────────────────

def load_real():
    """
    Load and clean the real survey CSV.
    Features (8): sleep_hours, sleep_quality, stress_level, screen_time,
                  study_hours, exercise_freq, mental_wellbeing, distraction
    Target: focus_level (Low / Medium / High)
    Returns: X (DataFrame), y (Series), feature_names (list)
    """
    df = pd.read_csv(REAL_CSV)

    # Keep only consenting, valid students
    df = df[df.iloc[:, 1].str.contains("Yes", na=False)]
    df = df[df.iloc[:, 2].str.strip().str.lower() == "yes"]  # Is a student

    # Rename for clarity
    col_map = {
        df.columns[7]: "sleep_hours_raw",
        df.columns[8]: "sleep_quality_raw",
        df.columns[9]: "stress_level",
        df.columns[10]: "mental_wellbeing",
        df.columns[11]: "screen_time_raw",
        df.columns[12]: "study_hours_raw",
        df.columns[13]: "exercise_freq_raw",
        df.columns[16]: "distraction_raw",
        df.columns[17]: "deep_work_rating",
    }
    df = df.rename(columns=col_map)

    # Encode features
    df["sleep_hours"]   = df["sleep_hours_raw"].apply(_encode_sleep_range)
    df["sleep_quality"] = df["sleep_quality_raw"].apply(_encode_sleep_quality)
    df["stress_level"]  = pd.to_numeric(df["stress_level"], errors="coerce").fillna(5)
    df["screen_time"]   = df["screen_time_raw"].apply(_encode_screen_time)
    df["study_hours"]   = df["study_hours_raw"].apply(_encode_study_range)
    df["exercise_freq"] = df["exercise_freq_raw"].apply(_encode_exercise_real)
    df["mental_wellbeing"] = pd.to_numeric(df["mental_wellbeing"], errors="coerce").fillna(3)
    df["distraction"]   = df["distraction_raw"].apply(_encode_distraction)

    # Target label
    df["deep_work_rating"] = pd.to_numeric(df["deep_work_rating"], errors="coerce")
    df = df.dropna(subset=["deep_work_rating"])
    df["focus_level"] = df["deep_work_rating"].apply(_focus_from_deep_work)

    feature_names = [
        "sleep_hours", "sleep_quality", "stress_level",
        "screen_time", "study_hours", "exercise_freq",
        "mental_wellbeing", "distraction",
    ]

    X = df[feature_names].copy()
    y = df["focus_level"]
    return X, y, feature_names


def load_synthetic():
    """
    Load and clean the synthetic student habits CSV.
    Features (8): sleep_hours, study_hours, social_media_hours,
                  exercise_freq, mental_health, attendance,
                  netflix_hours, part_time_job
    Target: focus_level derived from exam_score
    Returns: X (DataFrame), y (Series), feature_names (list)
    """
    df = pd.read_csv(SYNTH_CSV)

    # Encode categorical columns
    df["part_time_job_enc"] = df["part_time_job"].map({"Yes": 1, "No": 0}).fillna(0)
    df["diet_quality_enc"] = df["diet_quality"].map({"Poor": 0, "Fair": 1, "Good": 2}).fillna(1)

    # Target
    df["focus_level"] = df["exam_score"].apply(_focus_from_exam_score)

    feature_names = [
        "sleep_hours", "study_hours_per_day", "social_media_hours",
        "exercise_frequency", "mental_health_rating", "attendance_percentage",
        "netflix_hours", "part_time_job_enc",
    ]

    df = df.dropna(subset=feature_names + ["focus_level"])
    X = df[feature_names].copy()
    y = df["focus_level"]
    return X, y, feature_names


def load_combined():
    """
    Merge both datasets on their SHARED features for the combined model.
    Shared features (5): sleep_hours, study_hours, screen_time,
                         exercise_freq, mental_wellbeing
    Both datasets must be mapped to the same column names.
    Returns: X (DataFrame), y (Series), feature_names (list)
    """
    # --- Real survey ---
    df_real = pd.read_csv(REAL_CSV)
    df_real = df_real[df_real.iloc[:, 1].str.contains("Yes", na=False)]
    df_real = df_real[df_real.iloc[:, 2].str.strip().str.lower() == "yes"]

    col_map = {
        df_real.columns[7]:  "sleep_hours_raw",
        df_real.columns[10]: "mental_wellbeing",
        df_real.columns[11]: "screen_time_raw",
        df_real.columns[12]: "study_hours_raw",
        df_real.columns[13]: "exercise_freq_raw",
        df_real.columns[17]: "deep_work_rating",
    }
    df_real = df_real.rename(columns=col_map)

    df_real["sleep_hours"]      = df_real["sleep_hours_raw"].apply(_encode_sleep_range)
    df_real["study_hours"]      = df_real["study_hours_raw"].apply(_encode_study_range)
    df_real["screen_time"]      = df_real["screen_time_raw"].apply(_encode_screen_time)
    df_real["exercise_freq"]    = df_real["exercise_freq_raw"].apply(_encode_exercise_real)
    df_real["mental_wellbeing"] = pd.to_numeric(df_real["mental_wellbeing"], errors="coerce").fillna(3)

    df_real["deep_work_rating"] = pd.to_numeric(df_real["deep_work_rating"], errors="coerce")
    df_real = df_real.dropna(subset=["deep_work_rating"])
    df_real["focus_level"] = df_real["deep_work_rating"].apply(_focus_from_deep_work)

    real_shared = df_real[
        ["sleep_hours", "study_hours", "screen_time", "exercise_freq", "mental_wellbeing", "focus_level"]
    ].copy()
    real_shared["source"] = "real"

    # --- Synthetic dataset ---
    df_synth = pd.read_csv(SYNTH_CSV)
    df_synth["focus_level"] = df_synth["exam_score"].apply(_focus_from_exam_score)

    # Map synthetic columns to shared names
    synth_shared = pd.DataFrame({
        "sleep_hours":      df_synth["sleep_hours"],
        "study_hours":      df_synth["study_hours_per_day"],
        "screen_time":      df_synth["social_media_hours"],
        "exercise_freq":    df_synth["exercise_frequency"],
        "mental_wellbeing": df_synth["mental_health_rating"],
        "focus_level":      df_synth["focus_level"],
    })
    synth_shared["source"] = "synthetic"

    # Merge
    combined = pd.concat([real_shared, synth_shared], ignore_index=True)
    combined = combined.dropna()

    feature_names = ["sleep_hours", "study_hours", "screen_time", "exercise_freq", "mental_wellbeing"]
    X = combined[feature_names].copy()
    y = combined["focus_level"]
    return X, y, feature_names


# ── Utility for Gradio input encoding ────────────────────────────────────────

def encode_user_input_real(sleep, sleep_quality, stress, screen_time,
                           study_hours, exercise, wellbeing, distraction):
    """Encode raw Gradio slider/dropdown values for Model A (real survey model)."""
    return [[sleep, sleep_quality, stress, screen_time,
             study_hours, exercise, wellbeing, distraction]]


def encode_user_input_synthetic(sleep, study_hours, social_media,
                                exercise, mental_health, attendance,
                                netflix, part_time_job):
    """Encode raw Gradio slider/dropdown values for Model B (synthetic model)."""
    return [[sleep, study_hours, social_media, exercise,
             mental_health, attendance, netflix, int(part_time_job)]]


def encode_user_input_combined(sleep, study_hours, screen_time, exercise, wellbeing):
    """Encode raw Gradio slider/dropdown values for Model C (combined model)."""
    return [[sleep, study_hours, screen_time, exercise, wellbeing]]

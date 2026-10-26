import json
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# -------------------------------------------------------------
# Path Resolution relative to scripts/
# -------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
JSON_DIR = os.path.join(OUTPUT_DIR, "Output_JSON")
FEASIBILITY_OUT_DIR = os.path.join(OUTPUT_DIR, "feasibility_results")
MASTER_JSON = os.path.join(JSON_DIR, "master_dataset.json")
SURVEY_JSON = os.path.join(JSON_DIR, "survey_feedback_master.json")

os.makedirs(FEASIBILITY_OUT_DIR, exist_ok=True)


# -------------------------------------------------------------
# Metric 1: Cohort Completion Rate
# Formulation: (Σ trials_completed / (N_participants * 16)) * 100%
# Target Empirical Benchmark: >= 85% across all trials
# -------------------------------------------------------------
def calculate_cohort_completion_rate(data: dict, total_trials_per_p: int = 16) -> dict:
    participants = data["participants"]
    total_completed = sum(p["trials_completed"] for p in participants.values())
    total_expected = len(participants) * total_trials_per_p
    completion_rate = (total_completed / total_expected) * 100.0 if total_expected > 0 else 0.0

    return {
        "metric": "Cohort Completion Rate",
        "value_pct": completion_rate,
        "completed_trials": total_completed,
        "expected_trials": total_expected,
        "benchmark_met": completion_rate >= 85.0
    }


# -------------------------------------------------------------
# Metric 2: Full Session Adherence
# Formulation: (N_finished_all / N_total) * 100%
# Target Empirical Benchmark: >= 80% (at least 4/5 complete)
# -------------------------------------------------------------
def calculate_full_session_adherence(data: dict, total_trials_per_p: int = 16) -> dict:
    participants = data["participants"]
    n_finished_all = sum(
        1 for p in participants.values()
        if p["trials_completed"] >= total_trials_per_p and p["status"] == "completed"
    )
    total_participants = len(participants)
    adherence_rate = (n_finished_all / total_participants) * 100.0 if total_participants > 0 else 0.0

    return {
        "metric": "Full Session Adherence",
        "value_pct": adherence_rate,
        "adherent_participants": n_finished_all,
        "total_participants": total_participants,
        "benchmark_met": adherence_rate >= 80.0
    }


# -------------------------------------------------------------
# Metric 3: Attrition Onset Point
# Formulation: Trial index k in [1, 16] at which early exits occurred
# Identifies cognitive or visual fatigue thresholds
# -------------------------------------------------------------
def find_attrition_onset_points(data: dict) -> dict:
    attrition_events = []
    for pid, p in data["participants"].items():
        if p.get("status") == "early_exit":
            attrition_events.append({
                "participant_id": pid,
                "trial_onset_k": p["trials_completed"]
            })

    return {
        "metric": "Attrition Onset Point",
        "early_exit_count": len(attrition_events),
        "events": attrition_events,
        "interpretation": "No early exits recorded" if not attrition_events else f"Exits at trials: {[e['trial_onset_k'] for e in attrition_events]}"
    }


# -------------------------------------------------------------
# Metric 4: Mean Trial / Session Duration
# Formulation: T_total = (1/N) * Σ total_experiment_duration_sec
# Baseline session duration (min); P4 excluded as outlier
# -------------------------------------------------------------
def calculate_mean_trial_duration(data: dict, exclude_pids: list = None, unit: str = "min") -> dict:
    if exclude_pids is None:
        exclude_pids = []

    # Total experiment session durations (excluding outlier P4)
    session_durations_sec = [
        p["total_experiment_duration_sec"]
        for pid, p in data["participants"].items()
        if str(pid) not in [str(x) for x in exclude_pids]
    ]

    # Individual trial durations (excluding outlier P4)
    individual_trial_durations_sec = [
        s["trial_duration_sec"]
        for s in data["sessions"]
        if str(s["participant_id"]) not in [str(x) for x in exclude_pids]
    ]

    divisor = 60.0 if unit == "min" else 1.0

    mean_session = float(np.mean(session_durations_sec)) / divisor
    std_session = float(np.std(session_durations_sec)) / divisor
    mean_trial_sec = float(np.mean(individual_trial_durations_sec))
    std_trial_sec = float(np.std(individual_trial_durations_sec))

    return {
        "metric": "Mean Duration Analysis",
        "unit": unit,
        "mean_session_duration": mean_session,
        "std_session_duration": std_session,
        "mean_individual_trial_sec": mean_trial_sec,
        "std_individual_trial_sec": std_trial_sec,
        "evaluated_participants": len(session_durations_sec),
        "excluded_outliers": exclude_pids
    }


# -------------------------------------------------------------
# Metric 5: Plot of Average Trial Time Against Trial Index
# Tracks cognitive fatigue, pacing drift, or habituation across trials
# -------------------------------------------------------------
def plot_average_trial_time_against_index(
    data: dict,
    total_trials: int = 16,
    exclude_pids: list = None,
    output_filename: str = "trial_duration_trend.png"
):
    if exclude_pids is None:
        exclude_pids = []

    df = pd.DataFrame(data["sessions"])
    valid_pids = [
        pid for pid in data["participants"].keys()
        if str(pid) not in [str(x) for x in exclude_pids]
    ]

    duration_matrix = np.zeros((len(valid_pids), total_trials))
    for p_idx, pid in enumerate(valid_pids):
        p_sessions = df[df["participant_id"] == pid].sort_values("trial_index")
        duration_matrix[p_idx, :] = p_sessions["trial_duration_sec"].values[:total_trials]

    mean_per_trial = np.mean(duration_matrix, axis=0)
    std_per_trial = np.std(duration_matrix, axis=0)
    trials = np.arange(1, total_trials + 1)

    fig, ax = plt.subplots(figsize=(11, 5.5))

    # Plot individual traces
    for i, pid in enumerate(valid_pids):
        ax.plot(
            trials, duration_matrix[i],
            color="gray", alpha=0.35, linewidth=1.2,
            label="Participant Traces" if i == 0 else ""
        )

    # Plot cohort mean and confidence interval
    ax.plot(trials, mean_per_trial, marker="o", color="#2563eb", linewidth=2.5, label="Cohort Mean (N=4, P4 Excluded)")
    ax.fill_between(trials, mean_per_trial - std_per_trial, mean_per_trial + std_per_trial, color="#2563eb", alpha=0.15, label="±1 SD")

    ax.set_title(f"Per-Trial Duration Trend Across 16 Trials (Participant 4 Excluded as Outlier)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Trial Index (1–16)", fontsize=11)
    ax.set_ylabel("Trial Duration (seconds)", fontsize=11)
    ax.set_xticks(trials)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", framealpha=0.9)

    out_path = os.path.join(FEASIBILITY_OUT_DIR, output_filename)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"Saved Average Trial Duration Plot to: {out_path}")


# -------------------------------------------------------------
# Metric 6: Data Persistence Rate
# Formulation: (Sessions Recorded on Disk / Total Completed Submissions) * 100%
# Target Empirical Benchmark: 100% persistence rate
# -------------------------------------------------------------
def calculate_data_persistence_rate(data: dict) -> dict:
    sessions_recorded = len(data.get("sessions", []))
    total_completed = sum(p.get("trials_completed", 0) for p in data.get("participants", {}).values())
    rate = (sessions_recorded / total_completed) * 100.0 if total_completed > 0 else 0.0

    return {
        "metric": "Data Persistence Rate",
        "value_pct": rate,
        "sessions_recorded_on_disk": sessions_recorded,
        "total_completed_submissions": total_completed,
        "benchmark_met": rate == 100.0
    }


# -------------------------------------------------------------
# Metric 7: Average Ease of Use Score
# Formulation: (1 / N_respondents) * Σ ease_of_use_score
# Target Empirical Benchmark: >= 7.0 / 10 (Usability Acceptance Threshold)
# -------------------------------------------------------------
def calculate_average_ease_of_use(survey_path: str = SURVEY_JSON, target_benchmark: float = 7.0) -> dict:
    if not os.path.exists(survey_path):
        raise FileNotFoundError(f"Cannot find survey feedback file at {survey_path}")

    with open(survey_path, "r") as f:
        survey_data = json.load(f)

    responses = survey_data.get("responses", [])
    if not responses:
        return {
            "metric": "Average Ease of Use Score",
            "mean": 0.0,
            "std": 0.0,
            "median": 0.0,
            "iqr": 0.0,
            "min": 0,
            "max": 0,
            "respondent_count": 0,
            "benchmark_met": False
        }

    scores = np.array([r["ease_of_use_score"] for r in responses if "ease_of_use_score" in r])
    mean_score = float(np.mean(scores))
    std_score = float(np.std(scores))
    median_score = float(np.median(scores))
    iqr_score = float(np.percentile(scores, 75) - np.percentile(scores, 25))

    return {
        "metric": "Average Ease of Use Score",
        "mean": mean_score,
        "std": std_score,
        "median": median_score,
        "iqr": iqr_score,
        "min": int(np.min(scores)),
        "max": int(np.max(scores)),
        "respondent_count": len(scores),
        "target_benchmark": target_benchmark,
        "benchmark_met": mean_score >= target_benchmark
    }


# =============================================================
# Main Suite Execution
# =============================================================
if __name__ == "__main__":
    if not os.path.exists(MASTER_JSON):
        raise FileNotFoundError(f"Cannot find dataset at {MASTER_JSON}")

    with open(MASTER_JSON, "r") as f:
        dataset = json.load(f)

    print("=" * 70)
    print("ROBODEL PILOT STUDY: FEASIBILITY METRICS SUITE")
    print("=" * 70)

    # 1. Cohort Completion Rate
    m1 = calculate_cohort_completion_rate(dataset, total_trials_per_p=16)
    print(f"1. Cohort Completion Rate  : {m1['value_pct']:.2f}% ({m1['completed_trials']}/{m1['expected_trials']} trials) [Benchmark >= 85%: {m1['benchmark_met']}]")

    # 2. Full Session Adherence
    m2 = calculate_full_session_adherence(dataset, total_trials_per_p=16)
    print(f"2. Full Session Adherence  : {m2['value_pct']:.2f}% ({m2['adherent_participants']}/{m2['total_participants']} participants) [Benchmark >= 80%: {m2['benchmark_met']}]")

    # 3. Attrition Onset Point
    m3 = find_attrition_onset_points(dataset)
    print(f"3. Attrition Onset Point   : {m3['interpretation']}")

    # 4. Mean Duration (P4 Excluded)
    m4 = calculate_mean_trial_duration(dataset, exclude_pids=["4"], unit="min")
    print(f"4. Mean Session Duration   : {m4['mean_session_duration']:.2f} ± {m4['std_session_duration']:.2f} min (N={m4['evaluated_participants']}, P4 Excluded)")
    print(f"   Mean Single Trial Time  : {m4['mean_individual_trial_sec']:.2f} ± {m4['std_individual_trial_sec']:.2f} sec")

    # 5. Plot of Average Trial Time vs Index
    plot_average_trial_time_against_index(dataset, total_trials=16, exclude_pids=["4"])

    # 6. Data Persistence Rate
    m6 = calculate_data_persistence_rate(dataset)
    print(f"6. Data Persistence Rate   : {m6['value_pct']:.2f}% ({m6['sessions_recorded_on_disk']}/{m6['total_completed_submissions']}) [Benchmark 100%: {m6['benchmark_met']}]")

    # 7. Average Ease of Use Score
    m7 = calculate_average_ease_of_use(SURVEY_JSON, target_benchmark=7.0)
    print(f"7. Average Ease of Use     : {m7['mean']:.2f} / 10.0 (SD: {m7['std']:.2f}, Range: {m7['min']}–{m7['max']}) [Benchmark >= 7.0: {m7['benchmark_met']}]")
    print("=" * 70)
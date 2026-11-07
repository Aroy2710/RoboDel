TARGET_PRESENT_MAP = {
    1: "No", 2: "No", 3: "No", 4: "No", 5: "No",
    6: "Yes", 7: "No", 8: "No", 9: "Yes", 10: "No",
    11: "Yes", 12: "No", 13: "Yes", 14: "Yes", 15: "No", 16: "Yes"
}

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

def calculate_cohort_completion_rate(data: dict, total_trials_per_p: int = 16, exclude_pids: list = None) -> dict:
    if exclude_pids is None: exclude_pids = []
    participants = {k: v for k, v in data.get("participants", {}).items() if str(k) not in exclude_pids}
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

def find_attrition_onset_points(data: dict, exclude_pids: list = None) -> dict:
    if exclude_pids is None: exclude_pids = []
    participants = {k: v for k, v in data.get("participants", {}).items() if str(k) not in exclude_pids}
    attrition_events = []
    for pid, p in participants.items():
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

def calculate_mean_trial_duration(data: dict, exclude_pids: list = None, unit: str = "min") -> dict:
    if exclude_pids is None: exclude_pids = []

    session_durations_sec = [
        p["total_experiment_duration_sec"]
        for pid, p in data.get("participants", {}).items()
        if str(pid) not in exclude_pids
    ]

    individual_trial_durations_sec = [
        s["trial_duration_sec"]
        for s in data.get("sessions", [])
        if str(s["participant_id"]) not in exclude_pids
    ]

    divisor = 60.0 if unit == "min" else 1.0

    mean_session = float(np.mean(session_durations_sec)) / divisor if session_durations_sec else 0.0
    std_session = float(np.std(session_durations_sec)) / divisor if session_durations_sec else 0.0
    mean_trial_sec = float(np.mean(individual_trial_durations_sec)) if individual_trial_durations_sec else 0.0
    std_trial_sec = float(np.std(individual_trial_durations_sec)) if individual_trial_durations_sec else 0.0

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

def plot_average_trial_time_against_index(
    data: dict,
    total_trials: int = 16,
    exclude_pids: list = None,
    output_filename: str = "trial_duration_trend.png"
):
    if exclude_pids is None:
        exclude_pids = []

    sessions_filtered = [s for s in data.get("sessions", []) if str(s["participant_id"]) not in exclude_pids]
    if not sessions_filtered:
        return
        
    df = pd.DataFrame(sessions_filtered)
    
    valid_pids = [
        pid for pid in data.get("participants", {}).keys()
        if str(pid) not in exclude_pids
    ]

    duration_matrix = np.zeros((len(valid_pids), total_trials))
    for p_idx, pid in enumerate(valid_pids):
        p_sessions = df[df["participant_id"] == pid].sort_values("trial_index")
        if not p_sessions.empty:
            duration_matrix[p_idx, :len(p_sessions)] = p_sessions["trial_duration_sec"].values[:total_trials]

    mean_per_trial = np.mean(duration_matrix, axis=0)
    std_per_trial = np.std(duration_matrix, axis=0)
    trials = np.arange(1, total_trials + 1)

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, pid in enumerate(valid_pids):
        ax.plot(
            trials, duration_matrix[i],
            color="gray", alpha=0.30, linewidth=1.1,
            label="Individual Tester Runs" if i == 0 else ""
        )

    ax.plot(trials, mean_per_trial, color="#4b5563", linewidth=2.0, linestyle="--", label="Average Session Trend", zorder=3)
    ax.fill_between(trials, mean_per_trial - std_per_trial, mean_per_trial + std_per_trial, color="#4b5563", alpha=0.10, zorder=2)

    for i, trial_idx in enumerate(trials):
        status = TARGET_PRESENT_MAP.get(int(trial_idx), "No")
        color = "#2563eb" if status == "Yes" else "#dc2626"
        p_label = "Target Present (Yes)" if status == "Yes" and trial_idx == 6 else ("Target Absent (No)" if status == "No" and trial_idx == 1 else "")
        ax.scatter(trial_idx, mean_per_trial[i], color=color, s=80, zorder=5, label=p_label if p_label else "")

    ax.set_title(f"Per-Trial Duration Trend Across {total_trials} Trials", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Trial Index (1–16)", fontsize=11)
    ax.set_ylabel("Trial Duration (seconds)", fontsize=11)
    ax.set_xticks(trials)
    ax.grid(True, linestyle="--", alpha=0.5)
    
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="upper right", framealpha=0.9)

    out_path = os.path.join(FEASIBILITY_OUT_DIR, output_filename)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"Saved Average Trial Duration Plot to: {out_path}")

def calculate_data_persistence_rate(data: dict, exclude_pids: list = None) -> dict:
    if exclude_pids is None: exclude_pids = []
    participants = {k: v for k, v in data.get("participants", {}).items() if str(k) not in exclude_pids}
    sessions_recorded = sum(1 for s in data.get("sessions", []) if str(s.get("participant_id")) not in exclude_pids)
    total_completed = sum(p.get("trials_completed", 0) for p in participants.values())
    rate = (sessions_recorded / total_completed) * 100.0 if total_completed > 0 else 0.0

    return {
        "metric": "Data Persistence Rate",
        "value_pct": rate,
        "sessions_recorded_on_disk": sessions_recorded,
        "total_completed_submissions": total_completed,
        "benchmark_met": rate == 100.0
    }

def calculate_average_ease_of_use(survey_path: str = SURVEY_JSON, target_benchmark: float = 7.0, exclude_pids: list = None) -> dict:
    if exclude_pids is None: exclude_pids = []
    if not os.path.exists(survey_path):
        return {
            "metric": "Average Ease of Use Score",
            "mean": 0.0, "std": 0.0, "median": 0.0, "iqr": 0.0,
            "min": 0, "max": 0, "respondent_count": 0, "benchmark_met": False
        }

    with open(survey_path, "r") as f:
        survey_data = json.load(f)

    responses = survey_data.get("responses", [])
    valid_responses = [r for r in responses if str(r.get("participant_id", "")) not in exclude_pids]
    
    if not valid_responses:
        return {
            "metric": "Average Ease of Use Score",
            "mean": 0.0, "std": 0.0, "median": 0.0, "iqr": 0.0,
            "min": 0, "max": 0, "respondent_count": 0, "benchmark_met": False
        }

    scores = np.array([r["ease_of_use_score"] for r in valid_responses if "ease_of_use_score" in r])
    if len(scores) == 0:
        scores = np.array([0])
        
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
    EXCLUDE = ["4"]
    
    if os.path.exists(MASTER_JSON):
        with open(MASTER_JSON, "r") as f:
            dataset = json.load(f)

        print("=" * 70)
        print("ROBODEL PILOT STUDY: FEASIBILITY METRICS SUITE")
        print("=" * 70)

        m1 = calculate_cohort_completion_rate(dataset, total_trials_per_p=16, exclude_pids=EXCLUDE)
        print(f"1. Cohort Completion Rate  : {m1['value_pct']:.2f}% ({m1['completed_trials']}/{m1['expected_trials']} trials) [Benchmark >= 85%: {m1['benchmark_met']}]")

        m3 = find_attrition_onset_points(dataset, exclude_pids=EXCLUDE)
        print(f"2. Attrition Onset Point   : {m3['interpretation']}")

        m4 = calculate_mean_trial_duration(dataset, exclude_pids=EXCLUDE, unit="min")
        print(f"3. Mean Session Duration   : {m4['mean_session_duration']:.2f} ± {m4['std_session_duration']:.2f} min (N={m4['evaluated_participants']})")
        print(f"   Mean Single Trial Time  : {m4['mean_individual_trial_sec']:.2f} ± {m4['std_individual_trial_sec']:.2f} sec")

        plot_average_trial_time_against_index(dataset, total_trials=16, exclude_pids=EXCLUDE)

        m6 = calculate_data_persistence_rate(dataset, exclude_pids=EXCLUDE)
        print(f"4. Data Persistence Rate   : {m6['value_pct']:.2f}% ({m6['sessions_recorded_on_disk']}/{m6['total_completed_submissions']}) [Benchmark 100%: {m6['benchmark_met']}]")

        m7 = calculate_average_ease_of_use(SURVEY_JSON, target_benchmark=7.0, exclude_pids=EXCLUDE)
        print(f"5. Average Ease of Use     : {m7['mean']:.2f} / 10.0 (SD: {m7['std']:.2f}, Range: {m7['min']}–{m7['max']}) [Benchmark >= 7.0: {m7['benchmark_met']}]")
        print("=" * 70)

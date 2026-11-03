import json
import os
import numpy as np

# -------------------------------------------------------------
# Path Resolution relative to scripts/
# -------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MASTER_JSON = os.path.join(PROJECT_ROOT, "output", "Output_JSON", "master_dataset.json")

def calculate_average_fixation_points(master_json_path, exclude_pids=None):
    if exclude_pids is None:
        exclude_pids = ["4"]
        
    if not os.path.exists(master_json_path):
        raise FileNotFoundError(f"Dataset not found at {master_json_path}")
        
    with open(master_json_path, "r") as f:
        data = json.load(f)
        
    sessions = data.get("sessions", [])
    fixation_counts = []

    for s in sessions:
        if str(s.get("participant_id")) in [str(x) for x in exclude_pids]:
            continue
            
        telemetry = s.get("mouse_telemetry", {})
        x_coords = np.array(telemetry.get("X", []))
        y_coords = np.array(telemetry.get("Y", []))
        
        # Count valid coordinate points where both X and Y are greater than 0
        valid_pts = np.sum((x_coords > 0) & (y_coords > 0))
        fixation_counts.append(valid_pts)

    if not fixation_counts:
        print("No valid sessions found.")
        return

    mean_pts = np.mean(fixation_counts)
    std_pts = np.std(fixation_counts)
    eval_sessions = len(fixation_counts)

    print("=" * 60)
    print("ROBODEL: COHORT FIXATION POINTS ANALYSIS")
    print("=" * 60)
    print(f"Evaluated Sessions: {eval_sessions}")
    print(f"Average Valid Fixation Points per Session: {mean_pts:.2f} ± {std_pts:.2f}")
    print("=" * 60)

    return {
        "mean": mean_pts,
        "std": std_pts,
        "evaluated_sessions": eval_sessions
    }

if __name__ == "__main__":
    calculate_average_fixation_points(MASTER_JSON)
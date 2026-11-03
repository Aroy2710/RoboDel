import json
import os
from collections import Counter

# Path Resolution relative to scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MASTER_JSON = os.path.join(PROJECT_ROOT, "output", "Output_JSON", "master_dataset.json")

# Load master dataset
with open(MASTER_JSON, "r") as f:
    data = json.load(f)

sessions = data.get("sessions", [])

# Dictionary to store removed object labels per trial index / scene name
# Excluding participant 4 as per study parameters
trial_removals = {}

for s in sessions:
    if str(s.get("participant_id")) == "4":
        continue
    
    trial_idx = s.get("trial_index")
    scene_name = s.get("base_scene_name")
    target_obj = s.get("target_object")
    
    key = (trial_idx + 1, scene_name, target_obj)
    if key not in trial_removals:
        trial_removals[key] = []
        
    for obj in s.get("removed_objects", []):
        label = obj.get("label")
        # Clean up instance suffixes (e.g. 'Laptop_1' -> 'Laptop')
        base_label = label.rsplit("_", 1)[0] if "_" in label else label
        trial_removals[key].append(base_label)

# Compile the most common object deleted for each trial
results = []
for key, labels in sorted(trial_removals.items()):
    t_idx, scene, target = key
    counts = Counter(labels)
    most_common_obj, frequency = counts.most_common(1)[0] if counts else ("None", 0)
    
    results.append({
        "trial_number": t_idx,
        "scene": scene,
        "target": target,
        "most_common_deleted": most_common_obj,
        "count": frequency,
        "all_counts": counts.most_common()
    })

# Print out the results as a formatted table list
print(f"{'Trial':<6} | {'Scene Name':<30} | {'Target':<12} | {'Most Common Deleted Object':<25} | {'Count'}")
print("-" * 85)
for r in results:
    print(f"{r['trial_number']:<6} | {r['scene']:<30} | {r['target']:<12} | {r['most_common_deleted']:<25} | {r['count']}")
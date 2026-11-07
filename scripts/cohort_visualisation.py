import json
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import gaussian_filter

# -------------------------------------------------------------
# Path Resolution relative to scripts/
# -------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
JSON_DIR = os.path.join(OUTPUT_DIR, "Output_JSON")
SCENES_DIR = os.path.join(PROJECT_ROOT, "public", "Prerendered_Scenes")
MASTER_JSON = os.path.join(JSON_DIR, "master_dataset.json")

# Dedicated output directories
HEATMAP_OUT_DIR = os.path.join(OUTPUT_DIR, "average_heatmap")
SCANPATH_OUT_DIR = os.path.join(OUTPUT_DIR, "average_scanpath")

TRIAL_SEQUENCE = [
    "Trial_01_LivingRoom_FP205", "Trial_02_BathRoom_FP403", "Trial_03_Kitchen_FP5",
    "Trial_04_Kitchen_FP6", "Trial_05_Bedroom_FP304", "Trial_06_Bathroom_FP401",
    "Trial_07_LivingRoom_FP204", "Trial_08_Bedroom_FP301", "Trial_09_Bathroom_FP404",
    "Trial_10_Bathroom_FP402", "Trial_11_Kitchen_FP7", "Trial_12_LivingRoom_FP201",
    "Trial_13_Bedroom_FP303", "Trial_14_LivingRoom_FP203", "Trial_15_Kitchen_FP8",
    "Trial_16_Bedroom_FP302"
]

TARGET_PRESENT_MAP = {
    1: "No", 2: "No", 3: "No", 4: "No", 5: "No",
    6: "Yes", 7: "No", 8: "No", 9: "Yes", 10: "No",
    11: "Yes", 12: "No", 13: "Yes", 14: "Yes", 15: "No", 16: "Yes"
}

def load_trial_data(trial_index):
    """Loads JSON data and filters for the specified trial, strictly excluding Participant 4."""
    if not (1 <= trial_index <= 16):
        raise ValueError("Trial number must be between 1 and 16.")
        
    trial_name = TRIAL_SEQUENCE[trial_index - 1]
    
    if not os.path.exists(MASTER_JSON):
        raise FileNotFoundError(f"Dataset not found at {MASTER_JSON}")
        
    with open(MASTER_JSON, "r") as f:
        data = json.load(f)
        
    trial_sessions = [s for s in data.get("sessions", []) 
                      if s.get("base_scene_name") == trial_name and str(s.get("participant_id")) != "4"]
                      
    if not trial_sessions:
        raise ValueError(f"No valid data found for trial: {trial_name} (after excluding P4)")
        
    return trial_name, trial_sessions

def add_target_info_annotation(ax, trial_index, target_obj):
    """Adds a high-contrast text overlay indicating the Target Name and if it was present."""
    status = TARGET_PRESENT_MAP.get(trial_index, "Unknown")
    text_str = f"Target: {target_obj.capitalize()}\nTarget Present: {status}"
    
    ax.text(0.02, 0.96, text_str, transform=ax.transAxes, 
            fontsize=13, fontweight='bold', color='white', verticalalignment='top',
            bbox=dict(facecolor='black', alpha=0.75, edgecolor='none', pad=6), zorder=10)

def generate_cohort_heatmap(trial_index, sigma=3.5, alpha=0.55):
    """Generates an equally-weighted Average Heatmap across all participants."""
    os.makedirs(HEATMAP_OUT_DIR, exist_ok=True)
    trial_name, trial_sessions = load_trial_data(trial_index)

    # Use the initial observation image (obs.jpg) for the background
    img_path = os.path.join(SCENES_DIR, trial_name, "obs.jpg")
    bg_img = Image.open(img_path)
    img_w, img_h = bg_img.size

    target_obj = trial_sessions[0].get("target_object", "Unknown")
    individual_heatmaps = []

    for session in trial_sessions:
        x_coords = np.array(session["mouse_telemetry"]["X"])
        y_coords = np.array(session["mouse_telemetry"]["Y"])
        valid_idx = (x_coords > 0) & (y_coords > 0)
        x_coords, y_coords = x_coords[valid_idx], y_coords[valid_idx]
            
        if len(x_coords) > 0:
            bins_x, bins_y = 128, 72
            heatmap_grid, _, _ = np.histogram2d(x_coords, y_coords, bins=[bins_x, bins_y], range=[[0, img_w], [0, img_h]])
            heatmap_smoothed = gaussian_filter(heatmap_grid.T, sigma=sigma)
            
            # Normalize individual heatmap so each participant contributes equally
            max_val = heatmap_smoothed.max()
            if max_val > 0:
                individual_heatmaps.append(heatmap_smoothed / max_val)

    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor('black')
    ax.imshow(bg_img, extent=[0, img_w, img_h, 0])

    if individual_heatmaps:
        average_heatmap = np.mean(individual_heatmaps, axis=0)
        heatmap_masked = np.ma.masked_where(average_heatmap < 0.05, average_heatmap)
        
        im = ax.imshow(heatmap_masked, extent=[0, img_w, img_h, 0], cmap="jet", alpha=alpha, origin="upper", zorder=3)
        cbar = fig.colorbar(im, ax=ax, fraction=0.032, pad=0.02)
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        cbar.set_label("Equally Weighted Average Telemetry Point Density", fontsize=12, fontweight="bold", color='white')

    add_target_info_annotation(ax, trial_index, target_obj)
    
    ax.set_xlim(0, img_w)
    ax.set_ylim(img_h, 0)
    ax.axis("off")

    out_path = os.path.join(HEATMAP_OUT_DIR, f"{trial_name}_average_heatmap.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved average heatmap to: {out_path}")

def generate_cohort_scanpath(trial_index):
    """Calculates and plots a single average scanpath using temporal interpolation."""
    os.makedirs(SCANPATH_OUT_DIR, exist_ok=True)
    trial_name, trial_sessions = load_trial_data(trial_index)

    # Use the initial observation image (obs.jpg) for the background
    img_path = os.path.join(SCENES_DIR, trial_name, "obs.jpg")
    bg_img = Image.open(img_path)
    img_w, img_h = bg_img.size

    target_obj = trial_sessions[0].get("target_object", "Unknown")
    
    all_interp_x = []
    all_interp_y = []
    trial_durations_sec = []
    
    normalized_time_axis = np.linspace(0, 1, 100)

    for session in trial_sessions:
        x = np.array(session["mouse_telemetry"]["X"])
        y = np.array(session["mouse_telemetry"]["Y"])
        t = np.array(session["mouse_telemetry"]["T"])
        
        valid_idx = (x > 0) & (y > 0)
        x, y, t = x[valid_idx], y[valid_idx], t[valid_idx]
        
        if len(x) > 1 and t.max() > t.min():
            trial_durations_sec.append((t.max() - t.min()) / 1000.0)
            t_norm = (t - t.min()) / (t.max() - t.min())
            
            interp_x = np.interp(normalized_time_axis, t_norm, x)
            interp_y = np.interp(normalized_time_axis, t_norm, y)
            
            all_interp_x.append(interp_x)
            all_interp_y.append(interp_y)

    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor('black')
    ax.imshow(bg_img, extent=[0, img_w, img_h, 0])

    if all_interp_x and all_interp_y:
        avg_x = np.mean(all_interp_x, axis=0)
        avg_y = np.mean(all_interp_y, axis=0)
        mean_trial_time = np.mean(trial_durations_sec)

        cmap = plt.cm.plasma
        norm = plt.Normalize(vmin=0.0, vmax=1.0) 

        for i in range(len(avg_x) - 1):
            ax.plot([avg_x[i], avg_x[i+1]], [avg_y[i], avg_y[i+1]], 
                    color=cmap(norm(normalized_time_axis[i])), linewidth=3.0, alpha=0.9, zorder=3)
        
        ax.scatter(avg_x, avg_y, c=normalized_time_axis, cmap=cmap, norm=norm, s=40, alpha=1.0, zorder=4)
        
        ax.scatter([avg_x[0]], [avg_y[0]], color="#00ff66", s=140, edgecolors="black", linewidth=1.5, zorder=5)
        ax.scatter([avg_x[-1]], [avg_y[-1]], color="#ff2222", s=140, edgecolors="white", linewidth=1.5, zorder=5)

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0.0, vmax=mean_trial_time))
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.032, pad=0.02)
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        cbar.set_label("Mean Elapsed Search Time (seconds)", fontsize=12, fontweight="bold", color='white')

    # Add Legend just for Start/End
    handles = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#00ff66', markeredgecolor='black', markersize=9),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#ff2222', markeredgecolor='white', markersize=9)
    ]
    labels = ["Average Search Start", "Average Search End"]
    ax.legend(handles=handles, labels=labels, loc="lower right", facecolor="white", framealpha=0.95, fontsize=11)

    add_target_info_annotation(ax, trial_index, target_obj)
    
    ax.set_xlim(0, img_w)
    ax.set_ylim(img_h, 0)
    ax.axis("off")

    out_path = os.path.join(SCANPATH_OUT_DIR, f"{trial_name}_average_scanpath.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved average scanpath to: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate True Average Heatmaps and Scanpaths for RoboDel Trials.")
    parser.add_argument("trial_number", type=int, choices=range(1, 17),
                        help="The trial number (1-16) to visualize across the cohort.")
    
    args = parser.parse_args()
    
    print(f"Generating Visualizations for Trial {args.trial_number}...")
    generate_cohort_heatmap(args.trial_number)
    generate_cohort_scanpath(args.trial_number)
    print("Done.")
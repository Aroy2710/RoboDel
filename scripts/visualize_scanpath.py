import json
import os
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
from PIL import Image

# -------------------------------------------------------------
# Configuration: Specify the exact target image from Output_Images
# -------------------------------------------------------------
IMAGE_FILENAME = "pid_5_trial_01_Trial_01_LivingRoom_FP205_session_1792896955.jpg"

# Path definitions relative to scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
JSON_DIR = os.path.join(OUTPUT_DIR, "Output_JSON")
IMG_DIR = os.path.join(OUTPUT_DIR, "Output_Images")
SCANPATH_OUT_DIR = os.path.join(OUTPUT_DIR, "scan_path results")
MASTER_JSON = os.path.join(JSON_DIR, "master_dataset.json")

def visualize_single_scanpath(image_filename):
    os.makedirs(SCANPATH_OUT_DIR, exist_ok=True)
    img_path = os.path.join(IMG_DIR, image_filename)

    if not os.path.exists(img_path):
        raise FileNotFoundError(f"Image not found at {img_path}")
    if not os.path.exists(MASTER_JSON):
        raise FileNotFoundError(f"Dataset not found at {MASTER_JSON}")

    with open(MASTER_JSON, "r") as f:
        data = json.load(f)

    # Match trial session via session_id inside the filename
    session = next((s for s in data["sessions"] if s.get("session_id") in image_filename), None)
    if not session:
        raise ValueError(f"Could not find matching session in JSON for {image_filename}")

    # Extract coordinate telemetry
    telemetry = session["mouse_telemetry"]
    raw_x = np.array(telemetry["X"])
    raw_y = np.array(telemetry["Y"])
    raw_t = np.array(telemetry["T"])

    valid_idx = (raw_x > 0) & (raw_y > 0)
    x, y, t = raw_x[valid_idx], raw_y[valid_idx], raw_t[valid_idx]

    bg_img = Image.open(img_path)
    img_w, img_h = bg_img.size

    fig, ax = plt.subplots(figsize=(13, 7.5))
    ax.imshow(bg_img, extent=[0, img_w, img_h, 0])

    # Convert relative milliseconds to seconds
    t_seconds = (t - t.min()) / 1000.0
    total_duration = t_seconds.max() if len(t_seconds) > 0 else 1.0

    cmap = plt.cm.plasma
    norm = plt.Normalize(vmin=0.0, vmax=total_duration)

    if len(x) > 1:
        # Sequential connected lines coloured chronologically
        for i in range(len(x) - 1):
            line_color = cmap(norm(t_seconds[i]))
            ax.plot([x[i], x[i+1]], [y[i], y[i+1]], color=line_color, linewidth=2.2, alpha=0.9)

        ax.scatter(x, y, c=t_seconds, cmap=cmap, norm=norm, s=35, zorder=3)
        ax.scatter([x[0]], [y[0]], color="#00ff66", s=120, edgecolors="black", linewidth=1.5, label="Start Point (t = 0s)", zorder=5)
        ax.scatter([x[-1]], [y[-1]], color="#ff2222", s=120, edgecolors="white", linewidth=1.5, label=f"Search End (t = {total_duration:.1f}s)", zorder=5)

    # -------------------------------------------------------------
    # Bounding Box Logic: Support overlapping Target and Removed boxes
    # -------------------------------------------------------------
    target_obj = session.get("target_object", "").lower()
    has_target = False
    has_removed_items = False
    target_was_removed = False

    for obj in session.get("removed_objects", []):
        bb = obj["bounding_box"]
        is_target = target_obj in obj["label"].lower()
        has_removed_items = True

        if is_target:
            has_target = True
            target_was_removed = True
            
            # 1. Cyan Dashed Box (Target identity)
            rect_target = plt.Rectangle(
                (bb["x"], bb["y"]), bb["width"], bb["height"],
                linewidth=2.5,
                edgecolor="#00ffff",
                facecolor="none",
                linestyle="--",
                zorder=6
            )
            ax.add_patch(rect_target)

            # 2. Overlapping Yellow Dotted Box (Slight 2px inset/outset so both are visible)
            rect_removed = plt.Rectangle(
                (bb["x"] - 2, bb["y"] - 2), bb["width"] + 4, bb["height"] + 4,
                linewidth=2.0,
                edgecolor="#ffff00",
                facecolor="none",
                linestyle=":",
                zorder=7
            )
            ax.add_patch(rect_removed)
        else:
            # Distractor object removed
            rect_removed = plt.Rectangle(
                (bb["x"], bb["y"]), bb["width"], bb["height"],
                linewidth=1.8,
                edgecolor="#ffff00",
                facecolor="none",
                linestyle=":",
                zorder=6
            )
            ax.add_patch(rect_removed)

    # Build Legend
    handles, labels = ax.get_legend_handles_labels()

    if has_target:
        target_handle = mlines.Line2D([], [], color='#00ffff', linestyle='--', linewidth=2.5, label=f"Target ({session.get('target_object')})")
        handles.append(target_handle)
        labels.append(f"Target ({session.get('target_object')})")

    if has_removed_items:
        removed_handle = mlines.Line2D([], [], color='#ffff00', linestyle=':', linewidth=2.0, label="Object Removed in Phase 2")
        handles.append(removed_handle)
        labels.append("Object Removed in Phase 2")

    ax.legend(
        handles=handles,
        labels=labels,
        loc="lower right",
        facecolor="white",
        framealpha=0.92,
        fontsize=10,
        edgecolor="#cccccc"
    )

    # Attach chronological colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.032, pad=0.02)
    cbar.set_label("Elapsed Search Time (seconds)", fontsize=11, fontweight="bold")
    cbar.ax.tick_params(labelsize=10)

    ax.set_xlim(0, img_w)
    ax.set_ylim(img_h, 0)
    ax.axis("off")

    base_name, _ = os.path.splitext(image_filename)
    dest_path = os.path.join(SCANPATH_OUT_DIR, f"{base_name}_scanpath.png")

    plt.tight_layout()
    plt.savefig(dest_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved scanpath with overlapping highlights to: {dest_path}")

if __name__ == "__main__":
    visualize_single_scanpath(IMAGE_FILENAME)
import json
import os
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

# -------------------------------------------------------------
# Configuration: Target image from Output_Images
# -------------------------------------------------------------
IMAGE_FILENAME = "pid_2_trial_01_Trial_01_LivingRoom_FP205_session_1792800193.jpg"

# Path definitions relative to scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
JSON_DIR = os.path.join(OUTPUT_DIR, "Output_JSON")
IMG_DIR = os.path.join(OUTPUT_DIR, "Output_Images")
HEATMAP_OUT_DIR = os.path.join(OUTPUT_DIR, "heatmap results")
MASTER_JSON = os.path.join(JSON_DIR, "master_dataset.json")

def visualize_single_heatmap(image_filename, sigma=3.2, alpha=0.55):
    os.makedirs(HEATMAP_OUT_DIR, exist_ok=True)
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

    valid_idx = (raw_x > 0) & (raw_y > 0)
    x, y = raw_x[valid_idx], raw_y[valid_idx]

    bg_img = Image.open(img_path)
    img_w, img_h = bg_img.size

    fig, ax = plt.subplots(figsize=(13, 7.5))
    ax.imshow(bg_img, extent=[0, img_w, img_h, 0])

    # -------------------------------------------------------------
    # 2D Kernel Density Estimation (Gaussian KDE)
    # -------------------------------------------------------------
    if len(x) > 0:
        bins_x, bins_y = 128, 72
        heatmap_grid, _, _ = np.histogram2d(x, y, bins=[bins_x, bins_y], range=[[0, img_w], [0, img_h]])
        heatmap_smoothed = gaussian_filter(heatmap_grid.T, sigma=sigma)

        # Normalize density between 0 and 1
        max_val = heatmap_smoothed.max()
        if max_val > 0:
            heatmap_norm = heatmap_smoothed / max_val
        else:
            heatmap_norm = heatmap_smoothed

        # Mask regions below 6% density so background scene remains visible
        heatmap_masked = np.ma.masked_where(heatmap_norm < 0.06, heatmap_norm)
        im = ax.imshow(heatmap_masked, extent=[0, img_w, img_h, 0], cmap="jet", alpha=alpha, origin="upper", zorder=3)

        # Attach density colorbar
        cbar = fig.colorbar(im, ax=ax, fraction=0.032, pad=0.02)
        cbar.set_label("Relative Fixation Density", fontsize=11, fontweight="bold")
        cbar.ax.tick_params(labelsize=10)

    # -------------------------------------------------------------
    # Bounding Box Logic: Overlapping Target & Removed Highlights
    # -------------------------------------------------------------
    target_obj = session.get("target_object", "").lower()
    has_target = False
    has_removed_items = False

    for obj in session.get("removed_objects", []):
        bb = obj["bounding_box"]
        is_target = target_obj in obj["label"].lower()
        has_removed_items = True

        if is_target:
            has_target = True
            # Cyan dashed line for Target Object identity
            rect_target = plt.Rectangle(
                (bb["x"], bb["y"]), bb["width"], bb["height"],
                linewidth=2.5,
                edgecolor="#00ffff",
                facecolor="none",
                linestyle="--",
                zorder=6
            )
            ax.add_patch(rect_target)

            # Overlapping yellow dotted line for removal
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
    handles = []
    labels = []

    if has_target:
        target_handle = mlines.Line2D([], [], color='#00ffff', linestyle='--', linewidth=2.5, label=f"Target ({session.get('target_object')})")
        handles.append(target_handle)
        labels.append(f"Target ({session.get('target_object')})")

    if has_removed_items:
        removed_handle = mlines.Line2D([], [], color='#ffff00', linestyle=':', linewidth=2.0, label="Object Removed in Phase 2")
        handles.append(removed_handle)
        labels.append("Object Removed in Phase 2")

    if handles:
        ax.legend(
            handles=handles,
            labels=labels,
            loc="lower right",
            facecolor="white",
            framealpha=0.92,
            fontsize=10,
            edgecolor="#cccccc"
        )

    ax.set_xlim(0, img_w)
    ax.set_ylim(img_h, 0)
    ax.axis("off")

    base_name, _ = os.path.splitext(image_filename)
    dest_path = os.path.join(HEATMAP_OUT_DIR, f"{base_name}_heatmap.png")

    plt.tight_layout()
    plt.savefig(dest_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved clearly labelled heatmap to: {dest_path}")

if __name__ == "__main__":
    visualize_single_heatmap(IMAGE_FILENAME)
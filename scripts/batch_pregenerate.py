import os
import sys
import json
import argparse
import itertools
import shutil
from PIL import Image

# Add repository root to Python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from thor3d import ThorRenderer

def main():
    parser = argparse.ArgumentParser(description="AI2-THOR Batch Combinatorial Generator")
    parser.add_argument("--scene", default="FloorPlan1", help="The AI2-THOR scene to load (e.g., FloorPlan1)")
    parser.add_argument("--trial", default="Trial_1_FP1_Island", help="The output folder name (e.g., Trial_1_FP1_Island)")
    
    # Camera Telemetry Arguments
    parser.add_argument("--x", type=float, default=-1.25, help="Camera X position")
    parser.add_argument("--y", type=float, default=0.901, help="Camera Y position")
    parser.add_argument("--z", type=float, default=0.0, help="Camera Z position")
    parser.add_argument("--rotX", type=float, default=0.0, help="Camera X rotation")
    parser.add_argument("--rotY", type=float, default=90.0, help="Camera Y rotation")
    parser.add_argument("--rotZ", type=float, default=0.0, help="Camera Z rotation")
    parser.add_argument("--horizon", type=float, default=0.0, help="Camera horizon angle")
    
    # Target Objects Argument
    parser.add_argument("--targets", nargs='+', default=["Apple", "Bowl", "Bread", "Tomato", "Book", "Card"], 
                        help="Space-separated list of target objects to detect and ablate")
                        
    # Added Debug Flag
    parser.add_argument("--list-objects", action="store_true", help="Only output visible objects from this coordinate and exit")

    args = parser.parse_args()

    # Dynamic path: resolves to <this_repo>/public/Prerendered_Scenes/<trial>
    out_dir = os.path.join(REPO_ROOT, "public", "Prerendered_Scenes", args.trial)
    
    # Only clear directories if we are doing a full generation run
    if not args.list_objects:
        if os.path.exists(out_dir):
            print(f"Clearing existing contents in {out_dir}...")
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        print(f"Initializing {args.scene} -> Saving to {out_dir}")
    else:
        print(f"Probing {args.scene} for visible objects...")

    with ThorRenderer(width=1024, height=576, gpu_device=1, quality="Ultra") as r:
        r.controller.reset(
            scene=args.scene, 
            snapToGrid=False,
            renderInstanceSegmentation=True
        )
        
        event = r.controller.step(
            action="TeleportFull",
            x=args.x,
            y=args.y,
            z=args.z,
            rotation=dict(x=args.rotX, y=args.rotY, z=args.rotZ),
            horizon=args.horizon,
            standing=True
        )

        live_objects = event.metadata['objects']
        detections2D = event.instance_detections2D
        
        # Extract and sort all unique object types visible to the camera
        visible_types = sorted(list(set(o['objectType'] for o in live_objects if o['objectId'] in detections2D)))
        
        # 1. Early Exit Condition for Probing
        if args.list_objects:
            print("\n=== VISIBLE OBJECTS FOUND ===")
            for obj_type in visible_types:
                print(f" - {obj_type}")
            print("=============================\nExiting probe mode. No files were generated.")
            return

        # 2. Save base image as JPEG with 85% quality compression
        base_path = os.path.join(out_dir, "base.jpg")
        Image.fromarray(event.frame).save(base_path, format="JPEG", quality=85)
        print(f"Saved base image: {base_path}")

        # 3. Extract Native 2D Bounding Boxes
        target_types = set(args.targets)
        
        target_objects = [
            o for o in live_objects 
            if o['objectType'] in target_types and o['objectId'] in detections2D
        ]
        
        bboxes_data = []
        items = []

        for idx, obj in enumerate(target_objects):
            obj_id = obj['objectId']
            obj_type = obj['objectType']
            
            items.append((obj_type.lower(), obj_id))
            
            start_x, start_y, end_x, end_y = detections2D[obj_id]
            bboxes_data.append({
                "id": idx + 1,
                "label": obj_type,
                "x": int(start_x),
                "y": int(start_y),
                "width": int(end_x - start_x),
                "height": int(end_y - start_y),
                "isClicked": False
            })
        
        print(f"Target items detected ({len(items)}): {[label for label, _ in items]}")

        bbox_path = os.path.join(out_dir, "bounding_boxes.json")
        with open(bbox_path, 'w') as f:
            json.dump(bboxes_data, f, indent=4)
        print(f"Saved native bounding boxes to: {bbox_path}")

        # 4. Combinatorial Image Generation
        total_generated = 0
        for k in range(1, len(items) + 1):
            for combo in itertools.combinations(items, k):
                # Ensure all items are enabled before processing combination
                for _, obj_id in items:
                    r.controller.step(action="EnableObject", objectId=obj_id)

                # Disable combination targets
                for _, obj_id in combo:
                    r.controller.step(action="DisableObject", objectId=obj_id)

                labels_removed = sorted([label for label, _ in combo])
                filename = f"removed_{'_'.join(labels_removed)}.jpg"
                
                Image.fromarray(r.controller.last_event.frame).save(
                    os.path.join(out_dir, filename), 
                    format="JPEG", 
                    quality=85
                )
                print(f"-> Generated {filename}")
                total_generated += 1

        for _, obj_id in items:
            r.controller.step(action="EnableObject", objectId=obj_id)

        print(f"\nCompleted {args.trial}. {total_generated} permutations saved.")

if __name__ == "__main__":
    main()
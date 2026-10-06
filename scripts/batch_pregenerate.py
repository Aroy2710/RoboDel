import os
import sys
import json
import argparse
import itertools
import shutil
import random
from PIL import Image

# Add repository root to Python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from thor3d import ThorRenderer

def main():
    parser = argparse.ArgumentParser(description="AI2-THOR / ProcTHOR Batch Combinatorial Generator")
    
    # Environment Selector
    parser.add_argument("--dataset-type", choices=["ithor", "procthor"], default="ithor",
                        help="Choose between standard iTHOR scenes or ProcTHOR procedural houses")
    parser.add_argument("--scene", default="FloorPlan1", 
                        help="The iTHOR scene to load when using --dataset-type ithor (e.g., FloorPlan1, FloorPlan202)")
    parser.add_argument("--procthor-house-id", type=int, default=0,
                        help="Integer house index from procthor-10k dataset when using --dataset-type procthor")
    parser.add_argument("--procthor-split", default="train", choices=["train", "val", "test"],
                        help="Dataset split to sample ProcTHOR houses from")
    parser.add_argument("--scene-path", default=None,
                        help="Direct path to a custom ProcTHOR JSON file (e.g., custom_scenes/classroom_1.json)")

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
    
    # Dual Functionality for Observation Image
    parser.add_argument("--random-obs", action="store_true", 
                        help="Generate obs.jpg by randomly selecting a combination with 2-5 objects removed.")
    parser.add_argument("--exclude-obs", nargs='+', default=[], 
                        help="Generate obs.jpg by explicitly removing a space-separated list of object types or exact labels (e.g., Chair chair_2).")
                        
    # Debug Flag
    parser.add_argument("--list-objects", action="store_true", help="Only output visible objects from this coordinate and exit")

    args = parser.parse_args()

    # Dynamic path: resolves to <this_repo>/public/Prerendered_Scenes/<trial>
    out_dir = os.path.join(REPO_ROOT, "public", "Prerendered_Scenes", args.trial)
    
    # Only clear directories if performing a full generation run
    if not args.list_objects:
        if os.path.exists(out_dir):
            print(f"Clearing existing contents in {out_dir}...")
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        print(f"Initializing ({args.dataset_type}) -> Saving to {out_dir}")
    else:
        print(f"Probing scene for visible objects...")

    with ThorRenderer(width=1024, height=576, gpu_device=1, quality="High") as r:
        controller = r.controller

        # 1. Branch between iTHOR and ProcTHOR Scene Initialisation
        if args.dataset_type == "ithor":
            controller.reset(
                scene=args.scene, 
                snapToGrid=False,
                renderInstanceSegmentation=True,
                autoSimulation=False
            )
        else:
            if args.scene_path and os.path.exists(args.scene_path):
                print(f"Loading custom ProcTHOR layout from {args.scene_path}...")
                with open(args.scene_path, "r") as f:
                    house = json.load(f)
            else:
                try:
                    import prior
                except ImportError:
                    print("Error: The 'prior' package is required for ProcTHOR. Install it via: pip install prior")
                    sys.exit(1)
                
                print(f"Loading ProcTHOR house ID {args.procthor_house_id} from split '{args.procthor_split}'...")
                dataset = prior.load_dataset("procthor-10k")
                house = dataset[args.procthor_split][args.procthor_house_id]
            
            controller.reset(scene="Procedural", renderInstanceSegmentation=True, autoSimulation=False)
            controller.step(action="CreateHouse", house=house)
        
        # 2. Freeze Unity physics engine to prevent object shifting/dropping
        controller.step(action="PausePhysicsAutoSim")

        # 3. Teleport to target camera coordinates
        event = controller.step(
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
        
        # Early Exit Condition for Probing
        if args.list_objects:
            print("\n=== VISIBLE OBJECTS FOUND ===")
            for obj_type in visible_types:
                print(f" - {obj_type}")
            print("=============================\nExiting probe mode. No files were generated.")
            return

        # 4. Save full interactive base image as int.jpg
        int_path = os.path.join(out_dir, "int.jpg")
        Image.fromarray(event.frame).save(int_path, format="JPEG", quality=85)
        print(f"Saved interactive base image: {int_path}")

        # 5. Extract Native 2D Bounding Boxes
        target_types = set(args.targets)
        
        target_objects = [
            o for o in live_objects 
            if o['objectType'] in target_types and o['objectId'] in detections2D
        ]
        
        bboxes_data = []
        items = []
        type_counters = {} 

        for idx, obj in enumerate(target_objects):
            obj_id = obj['objectId']
            obj_type = obj['objectType']
            
            type_counters[obj_type] = type_counters.get(obj_type, 0) + 1
            
            unique_lower_label = f"{obj_type.lower()}_{type_counters[obj_type]}"
            unique_display_label = f"{obj_type}_{type_counters[obj_type]}"
            
            items.append((unique_lower_label, obj_id, obj_type))
            
            start_x, start_y, end_x, end_y = detections2D[obj_id]
            bboxes_data.append({
                "id": idx + 1,
                "label": unique_display_label, 
                "x": int(start_x),
                "y": int(start_y),
                "width": int(end_x - start_x),
                "height": int(end_y - start_y),
                "isClicked": False
            })
        
        print(f"Target items detected ({len(items)}): {[label for label, _, _ in items]}")

        if not items:
            print("[Error] No target objects were found visible at this camera viewpoint.")
            return

        bbox_path = os.path.join(out_dir, "bounding_boxes.json")
        with open(bbox_path, 'w') as f:
            json.dump(bboxes_data, f, indent=4)
        print(f"Saved native bounding boxes to: {bbox_path}")

        # 6. Combinatorial Image Generation
        total_generated = 0
        valid_obs_candidates = []

        for k in range(1, len(items) + 1):
            for combo in itertools.combinations(items, k):
                # Ensure all items are enabled before processing combination
                for _, obj_id, _ in items:
                    controller.step(action="EnableObject", objectId=obj_id)

                # Disable combination targets
                for _, obj_id, _ in combo:
                    controller.step(action="DisableObject", objectId=obj_id)

                labels_removed = sorted([label for label, _, _ in combo])
                filename = f"removed_{'_'.join(labels_removed)}.jpg"
                file_path = os.path.join(out_dir, filename)
                
                Image.fromarray(controller.last_event.frame).save(
                    file_path, 
                    format="JPEG", 
                    quality=85
                )
                print(f"-> Generated {filename}")
                
                if 2 <= k <= 5:
                    valid_obs_candidates.append(file_path)

                total_generated += 1
                
        # 7. Determine the Default obs.jpg Configuration
        if args.exclude_obs:
            requested_args = [t.lower() for t in args.exclude_obs]
            explicit_labels = []
            available_items = list(items)
            
            for req in requested_args:
                match = next((item for item in available_items if item[0].lower() == req), None)
                if not match:
                    default_instance_label = f"{req}_1"
                    match = next((item for item in available_items if item[0].lower() == default_instance_label), None)
                if not match:
                    match = next((item for item in available_items if item[2].lower() == req), None)
                
                if match:
                    explicit_labels.append(match[0])
                    available_items.remove(match)
                else:
                    print(f"-> WARNING: Could not find available match for requested removal: {req}")
            
            explicit_labels.sort()
            
            if explicit_labels:
                filename = f"removed_{'_'.join(explicit_labels)}.jpg"
                target_file = os.path.join(out_dir, filename)
                
                if os.path.exists(target_file):
                    shutil.copy(target_file, os.path.join(out_dir, "obs.jpg"))
                    print(f"-> Duplicated {filename} as obs.jpg (Explicit Exclude Mode)")
                else:
                    print(f"-> WARNING: Requested explicit combination {filename} was not generated.")
            else:
                print("-> WARNING: None of the requested explicit objects were successfully matched.")
                
        elif args.random_obs or not args.exclude_obs:
            if valid_obs_candidates:
                chosen_obs = random.choice(valid_obs_candidates)
                shutil.copy(chosen_obs, os.path.join(out_dir, "obs.jpg"))
                print(f"-> Duplicated {os.path.basename(chosen_obs)} as obs.jpg (Random Mode)")

        # Re-enable all objects after run
        for _, obj_id, _ in items:
            controller.step(action="EnableObject", objectId=obj_id)

        print(f"\nCompleted {args.trial}. {total_generated} permutations saved.")

if __name__ == "__main__":
    main()
import argparse
import sys
import re

def list_ithor():
    print("=" * 60)
    print("                AVAILABLE iTHOR SCENES                ")
    print("=" * 60)
    
    categories = {
        "Kitchen": [f"FloorPlan{i}" for i in range(1, 31)],
        "Living Room": [f"FloorPlan{i}" for i in range(201, 231)],
        "Bedroom": [f"FloorPlan{i}" for i in range(301, 331)],
        "Bathroom": [f"FloorPlan{i}" for i in range(401, 431)],
    }

    for cat_name, scenes in categories.items():
        print(f"\n--- {cat_name.upper()} ({len(scenes)} scenes) ---")
        print(f"  Train (1-20): {', '.join(scenes[:20])}")
        print(f"  Val   (21-25): {', '.join(scenes[20:25])}")
        print(f"  Test  (26-30): {', '.join(scenes[25:])}")
        
    print("\nRun example with iTHOR:")
    print("  python scripts/batch_pregenerate.py --dataset-type ithor --scene FloorPlan201 ...")


def extract_object_tokens(house):
    """
    Extracts all possible object type identifiers from a house dict,
    handling objectType, assetId, and procedural object id strings.
    """
    tokens = set()
    for obj in house.get("objects", []):
        # 1. Direct objectType if present
        if "objectType" in obj and obj["objectType"]:
            tokens.add(obj["objectType"].lower())
            
        # 2. Extract from id (e.g., 'DiningTable|surface|2|3' -> 'DiningTable')
        obj_id = obj.get("id", "")
        if obj_id:
            root = obj_id.split("|")[0].split("_")[0]
            tokens.add(root.lower())

        # 3. Extract from assetId (e.g., 'Laptop_01' -> 'Laptop')
        asset_id = obj.get("assetId", "")
        if asset_id:
            root = re.split(r'[-_0-9]', asset_id)[0]
            tokens.add(root.lower())

    return tokens


def list_procthor(split="train", limit=10, max_scan=500):
    print("\n" + "=" * 60)
    print(f"         SEARCHING ProcTHOR-10K ({split.upper()} SPLIT)         ")
    print("=" * 60)

    try:
        import prior
    except ImportError:
        print("\n[ERROR] The 'prior' package is required to inspect ProcTHOR.")
        print("Install it with: pip install prior\n")
        return

    print(f"Fetching dataset split '{split}' via prior...")
    dataset = prior.load_dataset("procthor-10k")
    split_data = dataset[split]
    total_houses = len(split_data)
    print(f"Total houses in {split} split: {total_houses}")
    print(f"Scanning up to {min(max_scan, total_houses)} houses to find target rooms...\n")

    # Lowercase tokens for robust substring matching
    signatures = {
        "Dining Room": {"diningtable", "chair"},
        "Home Office": {"desk", "laptop"},
        "Library / Reading Area": {"bookshelf", "book"},
        "Study / Classroom Setup": {"desk", "chair", "pen"}
    }

    matches = {cat: [] for cat in signatures}

    for idx in range(min(max_scan, total_houses)):
        house = split_data[idx]
        tokens = extract_object_tokens(house)

        for cat_name, required_tokens in signatures.items():
            if len(matches[cat_name]) < limit:
                if required_tokens.issubset(tokens):
                    matches[cat_name].append(idx)

    for cat_name, house_ids in matches.items():
        print(f"\n--- {cat_name.upper()} ---")
        if house_ids:
            print(f"  Matching House IDs: {house_ids}")
            print(f"  Test with: python scripts/web_explorer.py --dataset-type procthor --procthor-house-id {house_ids[0]} --procthor-split {split}")
        else:
            print("  No houses found matching all signature objects within scan limit.")

    print("\nProcTHOR-10k available index range:")
    print(f"  --procthor-house-id 0 to {total_houses - 1}")


def main():
    parser = argparse.ArgumentParser(description="List available environments for iTHOR and ProcTHOR")
    parser.add_argument("--mode", choices=["all", "ithor", "procthor"], default="all",
                        help="Choose which environment catalog to display")
    parser.add_argument("--split", choices=["train", "val", "test"], default="train",
                        help="ProcTHOR split to query")
    parser.add_argument("--limit", type=int, default=5,
                        help="Number of candidate ProcTHOR house IDs to show per category")
    parser.add_argument("--max-scan", type=int, default=400,
                        help="Number of houses to inspect in the ProcTHOR dataset")
    args = parser.parse_args()

    if args.mode in ["all", "ithor"]:
        list_ithor()
        
    if args.mode in ["all", "procthor"]:
        list_procthor(split=args.split, limit=args.limit, max_scan=args.max_scan)

if __name__ == "__main__":
    main()
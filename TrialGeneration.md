For the initial set, using standard iTHOR scenes avoids procedural generation dependencies and allows direct verification of environments, camera coordinates, and object ablations.

Covering the 4 domestic categories with 4 distinct scenes each yields 16 total iTHOR scenes (or 12 if selecting 3 per category):

### 16 Core iTHOR Scenes Setup (4 Scenes × 4 Categories)

| Category | Scene 1 | Scene 2 | Scene 3 | Scene 4 |
| --- | --- | --- | --- | --- |
| **Kitchen** | `FloorPlan5` | `FloorPlan6` | `FloorPlan7` | `FloorPlan8` |
| **Living Room** | `FloorPlan201` | `FloorPlan202` | `FloorPlan203` | `FloorPlan204` |
| **Bedroom** | `FloorPlan301` | `FloorPlan302` | `FloorPlan303` | `FloorPlan304` |
| **Bathroom** | `FloorPlan401` | `FloorPlan402` | `FloorPlan403` | `FloorPlan404` |

---

### Step-by-Step Execution Workflow for Each Scene

For every scene in this set, follow this three-step sequence:

#### 1. Interactive Camera Positioning

Launch `web_explorer.py` to position the camera toward a dense surface (table, counter, desk, or vanity) and note the HUD coordinates:

```bash
python scripts/web_explorer.py FloorPlan1

```

*Note down:* `X`, `Y`, `Z`, `Rotation`, `Horizon`.

#### 2. Probe Visible Target Candidates

Run `batch_pregenerate_2.py` with `--list-objects` to verify visible items from that exact viewpoint:

```bash
python scripts/batch_pregenerate_2.py \
  --dataset-type ithor \
  --scene FloorPlan1 \
  --x <X> --y <Y> --z <Z> --rotY <ROT> --horizon <HOR> \
  --list-objects

```

Select 5 to 8 visible items from the output list (e.g., small appliances, dishware, or tabletop props).

#### 3. Execute Full Batch Generation

Run the full combinatorial permutation generation with `--random-obs` (or explicit `--exclude-obs`):

```bash
python scripts/batch_pregenerate_2.py \
  --dataset-type ithor \
  --scene FloorPlan1 \
  --trial Trial_Kitchen_FP1 \
  --x <X> --y <Y> --z <Z> --rotY <ROT> --horizon <HOR> \
  --targets <TARGET_1> <TARGET_2> <TARGET_3> <TARGET_4> <TARGET_5> \
  --random-obs

```

---

 pseudo-randomized sequence for the 16 iTHOR scenes designed to avoid consecutive room types, keeping visual layouts and themes consistently alternating:

| Run # | Trial Directory | Scene ID | Room Category |
| --- | --- | --- | --- |
| **01** | `Trial_01_LivingRoom_FP202` | `FloorPlan205` | Living Room |
| **02** | `Trial_02_Bathroom_FP403` | `FloorPlan403` | Bathroom |
| **03** | `Trial_03_Kitchen_FP1` | `FloorPlan5` | Kitchen |
| **04** | `Trial_04_Kitchen_FP2` | `FloorPlan6` | Kitchen |
| **05** | `Trial_05_Bedroom_FP304` | `FloorPlan304` | Bedroom |
| **06** | `Trial_06_Bathroom_FP401` | `FloorPlan401` | Bathroom |
| **07** | `Trial_07_LivingRoom_FP204` | `FloorPlan204` | Living Room |
| **08** | `Trial_08_Bedroom_FP301` | `FloorPlan301` | Bedroom |
| **09** | `Trial_09_Bathroom_FP404` | `FloorPlan404` | Bathroom |
| **10** | `Trial_10_Bathroom_FP402` | `FloorPlan402` | Bathroom |
| **11** | `Trial_11_Kitchen_FP3` | `FloorPlan7` | Kitchen |
| **12** | `Trial_12_LivingRoom_FP201` | `FloorPlan201` | Living Room |
| **13** | `Trial_13_Bedroom_FP303` | `FloorPlan303` | Bedroom |
| **14** | `Trial_14_LivingRoom_FP203` | `FloorPlan203` | Living Room |
| **15** | `Trial_15_Kitchen_FP4` | `FloorPlan8` | Kitchen |
| **16** | `Trial_16_Bedroom_FP302` | `FloorPlan302` | Bedroom |
---

# Trial Configs

## Trial 1

```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan205 \
  --x -3.25 --y 0.9011 --z 3 --rotY 90 --horizon 0 \
  --list-objects
```


```bash
python scripts/batch_pregenerate.py \
  --dataset-type ithor \
  --scene FloorPlan205 \
  --trial Trial_1_Living_Room \
  --x -3.25 --y 0.9011 --z 3 --rotY 90 --horizon 0 \
  --targets Laptop Ottoman Painting Statue WateringCan GarbageCan HousePlant Window DiningTable SideTable\
  --random-obs
```
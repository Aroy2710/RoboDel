
---

### 1. `batch_pregenerate.py`

Used for offline trial generation, native 2D bounding-box extraction, combinatorial image generation, and `obs.jpg` baseline selection.

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `--dataset-type` | `str` (`ithor` | `procthor`) | `ithor` | Selects whether to load static iTHOR floor plans or ProcTHOR procedural houses. |
| `--scene` | `str` | `FloorPlan1` | The scene name to load when using `--dataset-type ithor` (e.g., `FloorPlan1` to `FloorPlan430`). |
| `--procthor-house-id` | `int` | `0` | The integer index of the house when using `--dataset-type procthor` (e.g., `0` to `9999`). |
| `--procthor-split` | `str` (`train` | `val` | `test`) | `train` | Dataset split to load the ProcTHOR house from. |
| `--trial` | `str` | `Trial_1_FP1_Island` | Output directory name under `public/Prerendered_Scenes/<trial>`. |
| `--x` | `float` | `-1.25` | Agent camera X position. |
| `--y` | `float` | `0.901` | Agent camera Y position (eye height). |
| `--z` | `float` | `0.0` | Agent camera Z position. |
| `--rotX` | `float` | `0.0` | Agent camera X rotation. |
| `--rotY` | `float` | `90.0` | Agent camera Y rotation (azimuth / compass heading: `0`, `90`, `180`, `270`). |
| `--rotZ` | `float` | `0.0` | Agent camera Z rotation. |
| `--horizon` | `float` | `0.0` | Camera pitch angle (e.g., `0`, `30`, `-30`). |
| `--targets` | `list[str]` | `Apple Bowl Bread Tomato Book Card` | Space-separated list of target object categories to detect and ablate. |
| `--random-obs` | flag (`store_true`) | `False` | Generates `obs.jpg` by randomly selecting a permutation missing 2 to 5 objects. |
| `--exclude-obs` | `list[str]` | `[]` | Explicit objects to ablate in `obs.jpg` (e.g., `Chair Bowl`). Generic names target instance `_1`. |
| `--list-objects` | flag (`store_true`) | `False` | Debug mode. Prints all visible objects from the given camera view and exits without saving files. |

---

### 2. `web_explorer.py`

Used for manual interactive camera positioning, viewpoint navigation, and telemetry readout in the browser.

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `scene` (Positional) | `str` | `FloorPlan1` | The floor plan to load when running standard iTHOR (e.g., `FloorPlan401`). |
| `--dataset-type` | `str` (`ithor` | `procthor`) | `ithor` | Switches between standard iTHOR scenes and ProcTHOR houses. |
| `--procthor-house-id` | `int` | `0` | Integer index of the ProcTHOR house to load. |
| `--procthor-split` | `str` (`train` | `val` | `test`) | `train` | Split to load the house from when using ProcTHOR. |
| `--port` | `int` | `8001` | Local port for the FastAPI/Uvicorn live web stream. |

---

### 3. `list_available_environments.py`

Used for inspecting standard iTHOR rooms and scanning ProcTHOR-10k for specific room signatures.

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `--mode` | `str` (`all` | `ithor` | `procthor`) | `all` | Choose which scene catalog to inspect. |
| `--split` | `str` (`train` | `val` | `test`) | `train` | ProcTHOR dataset split to query. |
| `--limit` | `int` | `8` | Maximum number of candidate house IDs to return per category. |
| `--max-scan` | `int` | `400` | Number of houses in the dataset to inspect for matching object signatures. |
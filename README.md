# Installing Libraries 
Install annaconda or annaconda mini for the virtual environment 
### Step 1 — Python environment

```bash
cd RoboDel
conda create -y -n robodel python=3.10
conda activate robodel
pip install -r requirements.txt

# vulkaninfo is a binary, not a pip package; xorg-libxext is needed in step 3
conda install -y -c conda-forge vulkan-tools xorg-libxext

```

### Step 2 — Unity build

The first run downloads AI2-THOR's Unity build (~800 MB zipped, 1.1 GB unpacked)
into `~/.ai2thor`. Fetch it up front so the first render can't time out:

```bash
python -c "
from ai2thor.controller import Controller
from ai2thor.platform import CloudRendering
Controller(platform=CloudRendering, download_only=True)"

```

It lands in `~/.ai2thor/releases/thor-CloudRendering-<commit>/`, where `<commit>`
is the build pinned by the installed `ai2thor` (5.0.0 →
`f0825767cd50d69f666c7f282e54abfe58f1e917`). The path is hardcoded, so to keep
the build off your home partition, symlink `~/.ai2thor` elsewhere *before*
downloading.

Rendering uses AI2-THOR's `CloudRendering` platform — headless Vulkan, no X
server required.

### Step 3 — Graphics libraries, if the container lacks them

Run `vulkaninfo --summary` first. If it lists your NVIDIA GPU under `Devices:`,
skip to step 4. If it lists only `llvmpipe` (Mesa's CPU rasterizer) or nothing,
read on.

A GPU container image often ships CUDA and nothing else. The NVIDIA driver
libraries get mounted in by the container runtime, but the userspace they depend
on is absent, and the failure surfaces far from its cause:

```
RuntimeError: Could not find a Vulkan device corresponding to the CUDA device
with UUID <uuid>.

```

That is AI2-THOR reporting that `vulkaninfo` showed it no NVIDIA device. CUDA
works throughout — `nvidia-smi` and `cuInit` are fine — because only the
*graphics* path is broken. Two libraries are usually missing, and neither needs
root to supply:

* **`libXext.so.6`**, a hard `DT_NEEDED` of `libGLX_nvidia.so.0`. Without it the
loader cannot open the ICD at all and logs `Failed to CreateInstance in ICD`.
* **libglvnd** (`libGL.so.1`, `libEGL.so.1`, `libGLdispatch.so.0`,
`libGLX.so.0`, `libOpenGL.so.0`). `libGLX_nvidia.so.0` is a GLVND *vendor*
library and refuses to initialize without the dispatch layer even when it is
being used purely as a Vulkan ICD — `vk_icdNegotiateLoaderICDInterfaceVersion`
returns `-3` (`VK_ERROR_INITIALIZATION_FAILED`) and every entry point comes
back NULL. This one is easy to misdiagnose: no file access fails, and the
driver never touches `/dev/nvidia*`, so `strace` shows nothing obviously wrong.

Stage both into one directory and put it on `LD_LIBRARY_PATH`:

```bash
conda create -y -p /tmp/glvnd -c conda-forge \
    libglvnd-cos7-x86_64 libglvnd-glx-cos7-x86_64 \
    libglvnd-egl-cos7-x86_64 libglvnd-opengl-cos7-x86_64
mkdir -p ~/.local/vulkanfix/lib
cp -P /tmp/glvnd/x86_64-conda-linux-gnu/sysroot/usr/lib64/lib{GL,EGL,GLX,GLdispatch,OpenGL}.so* \
      ~/.local/vulkanfix/lib/
cp -P $CONDA_PREFIX/lib/libXext.so.6* ~/.local/vulkanfix/lib/   # conda install -c conda-forge xorg-libxext

export LD_LIBRARY_PATH=~/.local/vulkanfix/lib
vulkaninfo --summary        # should now list your NVIDIA device

```

Make it automatic so every shell inherits it, rather than exporting by hand:

```bash
mkdir -p $CONDA_PREFIX/etc/conda/{activate,deactivate}.d

cat > $CONDA_PREFIX/etc/conda/activate.d/thor3d_vulkan.sh <<'EOF'
export _THOR3D_OLD_LD_LIBRARY_PATH="${LD_LIBRARY_PATH-}"
export LD_LIBRARY_PATH="$HOME/.local/vulkanfix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
EOF

cat > $CONDA_PREFIX/etc/conda/deactivate.d/thor3d_vulkan.sh <<'EOF'
if [ -n "${_THOR3D_OLD_LD_LIBRARY_PATH+x}" ]; then
    if [ -z "$_THOR3D_OLD_LD_LIBRARY_PATH" ]; then unset LD_LIBRARY_PATH
    else export LD_LIBRARY_PATH="$_THOR3D_OLD_LD_LIBRARY_PATH"; fi
    unset _THOR3D_OLD_LD_LIBRARY_PATH
fi
EOF

```

`activate.d` runs only at activation, so re-activate before testing:
`conda deactivate && conda activate thor3d`.

### Step 4 — GPU index

Find which CUDA index has a working Vulkan device, because it is often not 0:

```bash
nvidia-smi -L                                             # CUDA index -> GPU-<uuid>
vulkaninfo --summary | grep -E "^GPU[0-9]|deviceUUID"     # Vulkan index -> deviceUUID

```

Match the UUIDs. The CUDA index whose UUID appears in the `vulkaninfo` output is
the one to pass as `--gpu`. A GPU listed by `nvidia-smi` but absent from
`vulkaninfo` cannot render — a faulty card, or one the container exposes for
compute only.

If *every* GPU matches, AI2-THOR builds the mapping itself and there is nothing
to do. If any GPU is unmatched it raises regardless of which index you asked for,
because it insists on mapping all of them:

```
RuntimeError: Could not find a Vulkan device corresponding to the CUDA device
with UUID <uuid>.

```

Write the map by hand to bypass that. It is the only thing AI2-THOR's
`-force-device-index` flag is derived from:

```bash
echo '{"1": 0}' > ~/.ai2thor/cuda-vulkan-mapping.json   # CUDA 1 -> Vulkan 0

```

This ensures that files such as `batch_pregenerate.py` use gpu1.

---

# How to run RoboDel (user interface)

Once all the libraries and gpu mapping are completed, run the application by using two terminals.

In the first terminal, this enables the save functionality in the user interface:

```bash
cd RoboDel
conda activate robodel
python local_server.py 

```

In the second terminal, this enables the workflow of the application:

```bash
cd RoboDel
conda activate robodel
npm install
npm start

```

## Experimental Procedure (Participant Workflow)

When the application is running, participants will progress through the following standardized trial flow:

1. **Setup:** The participant enters their Participant ID and is shown a specific target object to locate (e.g., "Pan").
2. **Pre-Stimulus:** A 500ms blank screen clears visual persistence, followed immediately by a 500ms red fixation cross to center the participant's gaze.
3. **Observation Phase:** The scene appears heavily blurred. Moving the mouse simulates a 2.5-degree foveal window, unblurring the image around the cursor in real-time. Background telemetry captures the cursor's (X, Y) coordinates every 300ms.
4. **Interactive Phase:** The participant presses `Enter` to transition to the ablation workspace. They click green bounding boxes to select and remove objects that were *not* present in the original blurred image.
5. **Data Collection:** Clicking "Save" securely POSTs the final modified image, removed labels, and mouse telemetry arrays back to the local `output/` directory.

---

# How to generate new trials

## Using web_explorer.py

If you want to add a specific part of a FloorPlan for example `FloorPlan7`, use `web_explorer.py` to navigate the scene.

In a new terminal run:

```bash
cd RoboDel
conda activate robodel
python scripts/web_explorer.py FloorPlan7

```

The web explorer will open on port 8001. Explore the FloorPlan keeping note of the X, Y, Z, rotation, and horizon.

* **X, Y, Z** denote the location of the camera.
* **Rotation** defines rotating in increments of 90 degrees along the y-axis.
* **Horizon** refers to the angle moved up and down by the camera.
* `0` degrees: The camera is looking perfectly straight ahead, parallel to the floor.
* Positive values (e.g., `30`): The camera tilts down toward the floor.
* Negative values (e.g., `-30`): The camera tilts up toward the ceiling.



For the trial, assume we find a suitable viewpoint with the following parameters:

* x = -0.25
* y = 0.901
* z = 0.25
* Rotation = 270
* Horizon = 0

We will use these coordinates to generate variants of this image that exclude some of the objects visible in the image.

To first find what objects we are dealing with, we will pass these parameters to `batch_pregenerate.py`. In a new terminal run the following:

```bash
cd RoboDel
conda activate robodel
python scripts/batch_pregenerate.py \
  --scene FloorPlan7 \
  --x -0.25 \
  --y 0.901 \
  --z 0.25 \
  --rotY 270 \
  --horizon 0 \
  --list-objects

```

You should get the following output:

```text
Probing FloorPlan7 for visible objects...

=== VISIBLE OBJECTS FOUND ===
 - Book
 - Bowl
 - Bread
 - Cabinet
 - Chair
 - CoffeeMachine
 - CounterTop
 - Cup
 - DiningTable
 - Drawer
 - Egg
 - Floor
 - HousePlant
 - Lettuce
 - Pot
 - Window
=============================
Exiting probe mode. No files were generated.

```

For this example we are going to choose Book, Bowl, Bread, Chair, Cup, Egg, and HousePlant as the objects. There are 7 objects in total, so there will be 2^7 combinations to generate.

*Note: Sometimes these environments have multiple objects with the same name like Vase. In that case, there can be more than 2^7 combinations. When `batch_pregenerate.py` is running, it will display the exact number of objects its working with.*

With these objects in mind, run the following command in the same terminal:

```bash
python scripts/batch_pregenerate.py \
  --scene FloorPlan7 \
  --trial Trial_x_FP7_Counter \
  --x -0.25 \
  --y 0.901 \
  --z 0.25 \
  --rotY 270 \
  --horizon 0 \
  --targets Book Bowl Bread Chair Cup Egg HousePlant

```

The pregenerated variants will be stored in `public/Prerendered_Scenes` inside the folder `Trial_x_FP7_Counter`. Every time `batch_pregenerate.py` is run to generate images, the previous output in that target directory is cleared to avoid cluttering and to save time.

Here is a snippet of the output:

```text
Clearing existing contents in /data/roy/RoboDel/public/Prerendered_Scenes/Trial_x_FP7_Counter...
Initializing FloorPlan7 -> Saving to /data/roy/RoboDel/public/Prerendered_Scenes/Trial_x_FP7_Counter
Saved base image: /data/roy/RoboDel/public/Prerendered_Scenes/Trial_x_FP7_Counter/base.jpg
Target items detected (9): ['book_1', 'bowl_1', 'bread_1', 'chair_1', 'chair_2', 'chair_3', 'cup_1', 'egg_1', 'houseplant_1']
Saved native bounding boxes to: /data/roy/RoboDel/public/Prerendered_Scenes/Trial_x_FP7_Counter/bounding_boxes.json
-> Generated removed_book_1.jpg
-> Generated removed_bowl_1.jpg

```

Here there were multiple objects that shared the same name (like 3 chairs), hence there are actually 9 objects to consider, giving us 2^9 combinations.

## Updating the React Application

To ensure the user interface includes this new trial, add `"Trial_x_FP7_Counter"` to `TRIAL_SEQUENCE` and a corresponding target object (e.g., `"Egg"`) to the `TARGET_SEQUENCE` in `src/App.js`.

**Both arrays must be updated identically to prevent the application from crashing:**

```javascript
const TRIAL_SEQUENCE = [
  "Trial_1_FP1_Island",
  "Trial_2_FP207_LivingRoom",
  "Trial_x_FP7_Counter"
];

const TARGET_SEQUENCE = [
  "Pan",
  "Bottle",
  "Egg" 
];

```

The trials are shown sequentially in the user interface, so `Trial_x_FP7_Counter` will be shown as the 3rd and last trial. 


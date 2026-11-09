# RoboDel

RoboDel is a deployable QA testing platform for evaluating goal-directed visual search using AI2-THOR and React.

## Part 1: Running the Application Locally (Windows & Mac)

Follow these steps to run the pre-configured QA evaluation protocol on a standard local machine. No advanced GPU configurations are required.

### Step 1: Environment Setup

Ensure you have [Anaconda/Miniconda](https://docs.anaconda.com/miniconda/) and [Node.js](https://nodejs.org/) installed.

Open your terminal (macOS) or PowerShell/CMD (Windows):

    cd RoboDel
    
    # 1. Setup Python Backend
    conda create -y -n robodel python=3.10
    conda activate robodel
    pip install -r requirements.txt
    
    # 2. Setup React Frontend
    npm install

### Step 2: Launch the Application

You need to run the backend and frontend simultaneously in two separate terminal windows.

**Terminal 1 (Backend Server):**Starts the local server to handle save requests and telemetry logging.

    cd RoboDel
    conda activate robodel
    python local_server.py 

**Terminal 2 (Frontend UI):**Launches the React application in your default web browser.

    cd RoboDel
    npm start

### Step 3: Executing a Trial (Tester Workflow)

Once the app is running in your browser:

1. **Login:** Enter your Tester ID and click "Start".
2. **Review Target:** Note the target object displayed on the screen, then click "Begin Trial".
3. **Search:** Move your mouse to unblur the foveal window and search the room.
  * **Double-Left-Click** directly on the target if you find it.
  * **Press the 'X' key** if the target is missing or cannot be found.
4. **Interactive Verification:** The screen will transition to an unblurred view with green bounding boxes. Click on any outlined objects that were **not** present in the original blurred scene to remove them.
5. **Save:** Click "Save and Continue" to log the trial data and proceed to the next room.

* * *

## Part 2: Generating New Trials

Use these instructions to generate new combinatorial trial images using AI2-THOR's graphics engine.

### Step 1: Graphics Initialization & GPU Mapping

**Option A: Local Windows/macOS (Recommended)**Run the generation scripts locally. AI2-THOR will automatically open a Unity render window. Skip to Step 2.

**Option B: Headless Linux/Ubuntu Lab Server**If generating trials remotely on a headless GPU server, configure the Vulkan libraries and map the GPU.

First, install and link the required `libglvnd` libraries:

    conda install -y -c conda-forge vulkan-tools xorg-libxext
    
    # Create temporary environment to extract libraries
    conda create -y -p /tmp/glvnd -c conda-forge \
        libglvnd-cos7-x86_64 libglvnd-glx-cos7-x86_64 \
        libglvnd-egl-cos7-x86_64 libglvnd-opengl-cos7-x86_64
    
    # Copy them to your local user directory
    mkdir -p ~/.local/vulkanfix/lib
    cp -P /tmp/glvnd/x86_64-conda-linux-gnu/sysroot/usr/lib64/lib{GL,EGL,GLX,GLdispatch,OpenGL}.so* \
          ~/.local/vulkanfix/lib/
    cp -P $CONDA_PREFIX/lib/libXext.so.6* ~/.local/vulkanfix/lib/
    
    # Export the path
    export LD_LIBRARY_PATH=~/.local/vulkanfix/lib

Next, initialize the Unity Build (~1.1 GB) manually to prevent timeouts:

    python -c "
    from ai2thor.controller import Controller
    from ai2thor.platform import CloudRendering
    Controller(platform=CloudRendering, download_only=True)"

Finally, map your CUDA GPU to its Vulkan index. Check indexes using:

    nvidia-smi -L                                             # Lists CUDA indexes
    vulkaninfo --summary | grep -E "^GPU[0-9]|deviceUUID"     # Lists Vulkan indexes

Create a mapping file to force AI2-THOR to route graphics properly (e.g., mapping CUDA `1` to Vulkan `0`):

    mkdir -p ~/.ai2thor
    echo '{"1": 0}' > ~/.ai2thor/cuda-vulkan-mapping.json

### Step 2: Experimental Setup and Scene Selection

To cover a diverse range of environments, select scenes across the 4 domestic categories.

**Core iTHOR Scenes:**| Category | Scene 1 | Scene 2 | Scene 3 | Scene 4 || --- | --- | --- | --- | --- || **Kitchen** | `FloorPlan5` | `FloorPlan6` | `FloorPlan7` | `FloorPlan8` || **Living Room** | `FloorPlan201` | `FloorPlan202` | `FloorPlan203` | `FloorPlan204` || **Bedroom** | `FloorPlan301` | `FloorPlan302` | `FloorPlan303` | `FloorPlan304` || **Bathroom** | `FloorPlan401` | `FloorPlan402` | `FloorPlan403` | `FloorPlan404` |

**Pseudo-Randomized Trial Sequence:**To prevent users from predicting layouts, use this alternating sequence:

| Run # | Trial Directory | Scene ID | Room Category | Target Present |
| --- | --- | --- | --- | --- |
| **01** | `Trial_01_LivingRoom_FP202` | `FloorPlan205` | Living Room | No  |
| **02** | `Trial_02_Bathroom_FP403` | `FloorPlan403` | Bathroom | No  |
| **03** | `Trial_03_Kitchen_FP1` | `FloorPlan5` | Kitchen | No  |
| **04** | `Trial_04_Kitchen_FP2` | `FloorPlan6` | Kitchen | No  |
| **05** | `Trial_05_Bedroom_FP304` | `FloorPlan304` | Bedroom | No  |
| **06** | `Trial_06_Bathroom_FP401` | `FloorPlan401` | Bathroom | Yes |
| **07** | `Trial_07_LivingRoom_FP204` | `FloorPlan204` | Living Room | No  |
| **08** | `Trial_08_Bedroom_FP301` | `FloorPlan301` | Bedroom | No  |
| **09** | `Trial_09_Bathroom_FP404` | `FloorPlan404` | Bathroom | Yes |
| **10** | `Trial_10_Bathroom_FP402` | `FloorPlan402` | Bathroom | No  |
| **11** | `Trial_11_Kitchen_FP3` | `FloorPlan7` | Kitchen | Yes |
| **12** | `Trial_12_LivingRoom_FP201` | `FloorPlan201` | Living Room | No  |
| **13** | `Trial_13_Bedroom_FP303` | `FloorPlan303` | Bedroom | Yes |
| **14** | `Trial_14_LivingRoom_FP203` | `FloorPlan203` | Living Room | Yes |
| **15** | `Trial_15_Kitchen_FP4` | `FloorPlan8` | Kitchen | No  |
| **16** | `Trial_16_Bedroom_FP302` | `FloorPlan302` | Bedroom | Yes |

### Step 3: Step-by-Step Batch Generation Workflow

For each scene, follow this three-step generation sequence:

**1. Interactive Camera Positioning**Launch the web explorer tool to position the camera toward a dense surface and note the HUD coordinates (`X`, `Y`, `Z`, `rotY`, `Horizon`).

    python scripts/web_explorer.py 

**2. Probe Visible Target Candidates**Verify which items the engine recognizes as visible from your viewpoint using the `--list-objects` flag:

    python scripts/batch_pregenerate_2.py \
      --dataset-type ithor \
      --scene FloorPlan1 \
      --x <X> --y <Y> --z <Z> --rotY <ROT> --horizon <HOR> \
      --list-objects

**3. Execute Full Batch Generation**Run the full permutation generation. Include the `--random-obs` flag to automatically designate which objects will be hidden during the initial Observation Phase.

*Example Usage (Trial 1):*

    python scripts/batch_pregenerate_2.py \
      --dataset-type ithor \
      --scene FloorPlan205 \
      --trial Trial_01_LivingRoom_FP205 \
      --x -3.7032 --y 0.9011 --z 0.7929 --rotY 29 --horizon 4.2501 \
      --targets Laptop Statue Television WateringCan GarbageCan Painting Box DeskLamp FloorLamp HousePlant \
      --random-obs

The images and `bounding_boxes.json` will save to the `public/Prerendered_Scenes/` directory.
For more information on arguments , consult the table 
# RoboDel

RoboDel is a deployable QA testing platform for evaluating goal-directed visual search using AI2-THOR and React.

## Part 1: Running the Application Locally (Windows & Mac)

Follow these steps to run the pre-configured QA evaluation protocol on a standard local machine. No advanced GPU configurations are required.

### Step 1: Environment Setup

Ensure you have [Anaconda/Miniconda](https://docs.anaconda.com/miniconda/) and [Node.js](https://nodejs.org/) installed.

Open your terminal (macOS) or PowerShell/CMD (Windows):

    cd RoboDel
    
    # 1. Setup Python Backend
    conda create -y -n robodel python=3.10
    conda activate robodel
    pip install -r requirements.txt
    
    # 2. Setup React Frontend
    npm install

### Step 2: Launch the Application

You need to run the backend and frontend simultaneously in two separate terminal windows.

**Terminal 1 (Backend Server):**Starts the local server to handle save requests and telemetry logging.

    cd RoboDel
    conda activate robodel
    python local_server.py 

**Terminal 2 (Frontend UI):**Launches the React application in your default web browser.

    cd RoboDel
    npm start

### Step 3: Executing a Trial (Tester Workflow)

Once the app is running in your browser:

1. **Login:** Enter your Tester ID and click "Start".
2. **Review Target:** Note the target object displayed on the screen, then click "Begin Trial".
3. **Search:** Move your mouse to unblur the foveal window and search the room.
  * **Double-Left-Click** directly on the target if you find it.
  * **Press the 'X' key** if the target is missing or cannot be found.
4. **Interactive Verification:** The screen will transition to an unblurred view with green bounding boxes. Click on any outlined objects that were **not** present in the original blurred scene to remove them.
5. **Save:** Click "Save and Continue" to log the trial data and proceed to the next room.

* * *

## Part 2: Generating New Trials

Use these instructions to generate new combinatorial trial images using AI2-THOR's graphics engine.

### Step 1: Graphics Initialization & GPU Mapping

**Option A: Local Windows/macOS (Recommended)**Run the generation scripts locally. AI2-THOR will automatically open a Unity render window. Skip to Step 2.

**Option B: Headless Linux/Ubuntu Lab Server**If generating trials remotely on a headless GPU server, configure the Vulkan libraries and map the GPU.

First, install and link the required `libglvnd` libraries:

    conda install -y -c conda-forge vulkan-tools xorg-libxext
    
    # Create temporary environment to extract libraries
    conda create -y -p /tmp/glvnd -c conda-forge \
        libglvnd-cos7-x86_64 libglvnd-glx-cos7-x86_64 \
        libglvnd-egl-cos7-x86_64 libglvnd-opengl-cos7-x86_64
    
    # Copy them to your local user directory
    mkdir -p ~/.local/vulkanfix/lib
    cp -P /tmp/glvnd/x86_64-conda-linux-gnu/sysroot/usr/lib64/lib{GL,EGL,GLX,GLdispatch,OpenGL}.so* \
          ~/.local/vulkanfix/lib/
    cp -P $CONDA_PREFIX/lib/libXext.so.6* ~/.local/vulkanfix/lib/
    
    # Export the path
    export LD_LIBRARY_PATH=~/.local/vulkanfix/lib

Next, initialize the Unity Build (~1.1 GB) manually to prevent timeouts:

    python -c "
    from ai2thor.controller import Controller
    from ai2thor.platform import CloudRendering
    Controller(platform=CloudRendering, download_only=True)"

Finally, map your CUDA GPU to its Vulkan index. Check indexes using:

    nvidia-smi -L                                             # Lists CUDA indexes
    vulkaninfo --summary | grep -E "^GPU[0-9]|deviceUUID"     # Lists Vulkan indexes

Create a mapping file to force AI2-THOR to route graphics properly (e.g., mapping CUDA `1` to Vulkan `0`):

    mkdir -p ~/.ai2thor
    echo '{"1": 0}' > ~/.ai2thor/cuda-vulkan-mapping.json

### Step 2: Experimental Setup and Scene Selection

To cover a diverse range of environments, select scenes across the 4 domestic categories.

**Core iTHOR Scenes:**| Category | Scene 1 | Scene 2 | Scene 3 | Scene 4 || --- | --- | --- | --- | --- || **Kitchen** | `FloorPlan5` | `FloorPlan6` | `FloorPlan7` | `FloorPlan8` || **Living Room** | `FloorPlan201` | `FloorPlan202` | `FloorPlan203` | `FloorPlan204` || **Bedroom** | `FloorPlan301` | `FloorPlan302` | `FloorPlan303` | `FloorPlan304` || **Bathroom** | `FloorPlan401` | `FloorPlan402` | `FloorPlan403` | `FloorPlan404` |

**Pseudo-Randomized Trial Sequence:**To prevent users from predicting layouts, use this alternating sequence:

| Run # | Trial Directory | Scene ID | Room Category | Target Present |
| --- | --- | --- | --- | --- |
| **01** | `Trial_01_LivingRoom_FP202` | `FloorPlan205` | Living Room | No  |
| **02** | `Trial_02_Bathroom_FP403` | `FloorPlan403` | Bathroom | No  |
| **03** | `Trial_03_Kitchen_FP1` | `FloorPlan5` | Kitchen | No  |
| **04** | `Trial_04_Kitchen_FP2` | `FloorPlan6` | Kitchen | No  |
| **05** | `Trial_05_Bedroom_FP304` | `FloorPlan304` | Bedroom | No  |
| **06** | `Trial_06_Bathroom_FP401` | `FloorPlan401` | Bathroom | Yes |
| **07** | `Trial_07_LivingRoom_FP204` | `FloorPlan204` | Living Room | No  |
| **08** | `Trial_08_Bedroom_FP301` | `FloorPlan301` | Bedroom | No  |
| **09** | `Trial_09_Bathroom_FP404` | `FloorPlan404` | Bathroom | Yes |
| **10** | `Trial_10_Bathroom_FP402` | `FloorPlan402` | Bathroom | No  |
| **11** | `Trial_11_Kitchen_FP3` | `FloorPlan7` | Kitchen | Yes |
| **12** | `Trial_12_LivingRoom_FP201` | `FloorPlan201` | Living Room | No  |
| **13** | `Trial_13_Bedroom_FP303` | `FloorPlan303` | Bedroom | Yes |
| **14** | `Trial_14_LivingRoom_FP203` | `FloorPlan203` | Living Room | Yes |
| **15** | `Trial_15_Kitchen_FP4` | `FloorPlan8` | Kitchen | No  |
| **16** | `Trial_16_Bedroom_FP302` | `FloorPlan302` | Bedroom | Yes |

### Step 3: Step-by-Step Batch Generation Workflow

For each scene, follow this three-step generation sequence:

**1. Interactive Camera Positioning**Launch the web explorer tool to position the camera toward a dense surface and note the HUD coordinates (`X`, `Y`, `Z`, `rotY`, `Horizon`).

    python scripts/web_explorer.py 

**2. Probe Visible Target Candidates**Verify which items the engine recognizes as visible from your viewpoint using the `--list-objects` flag:

    python scripts/batch_pregenerate_2.py \
      --dataset-type ithor \
      --scene FloorPlan1 \
      --x <X> --y <Y> --z <Z> --rotY <ROT> --horizon <HOR> \
      --list-objects

**3. Execute Full Batch Generation**Run the full permutation generation. Include the `--random-obs` flag to automatically designate which objects will be hidden during the initial Observation Phase.

*Example Usage (Trial 1):*

    python scripts/batch_pregenerate_2.py \
      --dataset-type ithor \
      --scene FloorPlan205 \
      --trial Trial_01_LivingRoom_FP205 \
      --x -3.7032 --y 0.9011 --z 0.7929 --rotY 29 --horizon 4.2501 \
      --targets Laptop Statue Television WateringCan GarbageCan Painting Box DeskLamp FloorLamp HousePlant \
      --random-obs

The images and `bounding_boxes.json` will save to the `public/Prerendered_Scenes/` directory.

### Step 4: Update React State

To make the new trial load in the UI, add your new folder name and target object to the state arrays in `src/App.js`:

    const TRIAL_SEQUENCE = [
      "Trial_01_LivingRoom_FP205",
      "Trial_02_BathRoom_FP403" // <- Add new folders here in order
    ];
    
    const TARGET_SEQUENCE = [
      "Laptop",
      "SoapBar"               // <- Add corresponding targets here
    ];

* * *

## Part 3: Reproducing Evaluation Results

Follow these steps to locally execute the analytical scripts and reproduce the metrics and figures from the study. Scripts process the raw telemetry data located in `output/Output_JSON/`.

### 1. Generate Baseline Metrics (Table 2 & Figure 2)

Run the feasibility suite to output core performance metrics to the terminal and generate the **Per-Trial Duration Trend (Figure 2)**.

    cd scripts
    conda activate robodel
    python feasibility_metrics.py

### 2. Calculate Memory Recall Accuracy (Section 5.3)

Run the object recall script to calculate the False-Positive Rejection Accuracy (distractor ablation success rate).

    python object_recall.py

### 3. Generate Visualizations (Figure 3 & 4)

Run the visualization suite to process the 300ms telemetry arrays into cohesive graphics (scan paths and heatmaps). Outputs are saved to `output/feasibility_results/`.

    python cohort_visualisation.py 


### 4. Calculate Visual Sampling Density

Run the sampling script to output the average visual sampling points per trial.

    python average_sample_points.py



* * *


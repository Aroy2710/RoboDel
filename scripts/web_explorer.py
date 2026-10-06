import os
import sys
import io
import base64
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from PIL import Image

parser = argparse.ArgumentParser(description="AI2-THOR & ProcTHOR Web Explorer")
parser.add_argument("--dataset-type", choices=["ithor", "procthor"], default="ithor",
                    help="Choose between standard iTHOR scenes or ProcTHOR procedural houses")
parser.add_argument("scene", nargs="?", default="FloorPlan1", 
                    help="The iTHOR floor plan to load (e.g., FloorPlan1, FloorPlan201, FloorPlan401)")
parser.add_argument("--procthor-house-id", type=int, default=0,
                    help="Integer house index from procthor-10k dataset when using --dataset-type procthor")
parser.add_argument("--procthor-split", default="train", choices=["train", "val", "test"],
                    help="Dataset split to sample ProcTHOR houses from")
parser.add_argument("--scene-path", default=None,
                    help="Direct path to custom ProcTHOR JSON layout file")
parser.add_argument("--port", type=int, default=8001, help="Port to run the FastAPI server on")

args = parser.parse_args()
DATASET_TYPE = args.dataset_type
TARGET_SCENE = args.scene
PROCTHOR_HOUSE_ID = args.procthor_house_id
PROCTHOR_SPLIT = args.procthor_split
SCENE_PATH = args.scene_path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from thor3d import ThorRenderer

renderer_instance = None
r = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global renderer_instance, r, TARGET_SCENE
    
    renderer_instance = ThorRenderer(width=800, height=600, gpu_device=1, quality="Medium")
    r = renderer_instance.__enter__()
    
    if DATASET_TYPE == "ithor":
        print(f"Initializing iTHOR scene: {TARGET_SCENE}")
        r.controller.reset(scene=TARGET_SCENE, snapToGrid=False, autoSimulation=False)
    else:
        if SCENE_PATH and os.path.exists(SCENE_PATH):
            import json
            print(f"Loading custom ProcTHOR layout from {SCENE_PATH}...")
            with open(SCENE_PATH, "r") as f:
                house = json.load(f)
        else:
            try:
                import prior
            except ImportError:
                print("\nError: The 'prior' package is required to load ProcTHOR houses. Run: pip install prior\n")
                sys.exit(1)
            print(f"Loading ProcTHOR-10k ({PROCTHOR_SPLIT} split, House ID: {PROCTHOR_HOUSE_ID})...")
            dataset = prior.load_dataset("procthor-10k")
            house = dataset[PROCTHOR_SPLIT][PROCTHOR_HOUSE_ID]
        
        r.controller.reset(scene="Procedural", snapToGrid=False, autoSimulation=False)
        r.controller.step(action="CreateHouse", house=house)
        print("ProcTHOR house created successfully.")
    
    r.controller.step(action="PausePhysicsAutoSim")
    yield
    if renderer_instance:
        renderer_instance.__exit__(None, None, None)

app = FastAPI(lifespan=lifespan)

def get_state_response(scene_title=None):
    global TARGET_SCENE
    event = r.controller.last_event
    agent = event.metadata['agent']
    
    img = Image.fromarray(event.frame)
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=75)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    current_title = (
        f"iTHOR: {TARGET_SCENE}" 
        if DATASET_TYPE == "ithor" 
        else f"ProcTHOR: House #{PROCTHOR_HOUSE_ID} ({PROCTHOR_SPLIT})"
    )
    
    return {
        "image": img_str,
        "x": round(agent['position']['x'], 4),
        "y": round(agent['position']['y'], 4),
        "z": round(agent['position']['z'], 4),
        "rotation": round(agent['rotation']['y'], 4),
        "horizon": round(agent['cameraHorizon'], 4),
        "sceneTitle": scene_title or current_title
    }

@app.get("/switch_scene")
def switch_scene(scene_name: str = Query(...)):
    global r, TARGET_SCENE, DATASET_TYPE
    clean_scene = scene_name.strip()
    if not clean_scene:
        return JSONResponse({"error": "Empty scene name provided"}, status_code=400)
    
    try:
        print(f"Switching scene to: {clean_scene}...")
        r.controller.reset(scene=clean_scene, snapToGrid=False, autoSimulation=False)
        r.controller.step(action="PausePhysicsAutoSim")
        TARGET_SCENE = clean_scene
        DATASET_TYPE = "ithor"
        return get_state_response(scene_title=f"iTHOR: {clean_scene}")
    except Exception as e:
        print(f"Failed to switch to scene {clean_scene}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/step")
def step(action: str = "Pass"):
    global r
    if action == "MoveAhead": r.controller.step(action="MoveAhead", moveMagnitude=0.15)
    elif action == "MoveBack": r.controller.step(action="MoveBack", moveMagnitude=0.15)
    elif action == "MoveRight": r.controller.step(action="MoveRight", moveMagnitude=0.15)
    elif action == "MoveLeft": r.controller.step(action="MoveLeft", moveMagnitude=0.15)
    return get_state_response()

@app.get("/look")
def look(yaw: float = 0.0, pitch: float = 0.0):
    global r
    agent = r.controller.last_event.metadata['agent']
    current_rot = agent['rotation']['y']
    current_horizon = agent['cameraHorizon']

    new_horizon = max(-30.0, min(60.0, current_horizon + pitch))
    new_rot = (current_rot + yaw) % 360.0

    r.controller.step(
        action="TeleportFull",
        x=agent['position']['x'],
        y=agent['position']['y'],
        z=agent['position']['z'],
        rotation=dict(x=0.0, y=new_rot, z=0.0),
        horizon=new_horizon,
        standing=True
    )
    return get_state_response()

@app.get("/", response_class=HTMLResponse)
def index():
    display_title = (
        f"iTHOR: {TARGET_SCENE}" 
        if DATASET_TYPE == "ithor" 
        else f"ProcTHOR: House #{PROCTHOR_HOUSE_ID} ({PROCTHOR_SPLIT})"
    )
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI2-THOR Continuous Web Explorer</title>
        <style>
            body {{
                background: #181818;
                color: #eaeaea;
                text-align: center;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
                user-select: none;
                margin: 15px 0;
            }}
            .scene-bar {{
                background: #252525;
                padding: 10px 16px;
                border-radius: 8px;
                display: inline-flex;
                gap: 8px;
                align-items: center;
                margin-bottom: 12px;
                border: 1px solid #3a3a3a;
            }}
            .scene-input {{
                background: #121212;
                border: 1px solid #4CAF50;
                color: #fff;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 15px;
                font-family: monospace;
                width: 170px;
                text-align: center;
            }}
            .scene-btn {{
                background: #4CAF50;
                color: #fff;
                border: none;
                padding: 7px 15px;
                border-radius: 4px;
                font-size: 14px;
                cursor: pointer;
                font-weight: bold;
                transition: background 0.2s;
            }}
            .scene-btn:hover {{
                background: #43A047;
            }}
            #viewport-container {{
                position: relative;
                display: inline-block;
                cursor: crosshair;
            }}
            #view {{
                width: 800px;
                height: 600px;
                border: 2px solid #444;
                border-radius: 8px;
                display: block;
            }}
            #overlay-msg {{
                position: absolute;
                top: 15px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0,0,0,0.7);
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 13px;
                pointer-events: none;
                transition: opacity 0.2s;
            }}
            .telemetry-bar {{
                margin-top: 15px;
                font-size: 16px;
                background: #252525;
                display: inline-block;
                padding: 12px 24px;
                border-radius: 8px;
                border: 1px solid #333;
            }}
            .val-pos {{ color: #4CAF50; font-weight: bold; }}
            .val-rot {{ color: #2196F3; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2 style="margin: 6px 0 12px 0;">AI2-THOR Live Explorer: <span id="sceneTitle" style="color:#FF9800;">{display_title}</span></h2>
        
        <div class="scene-bar">
            <label for="sceneInput" style="font-size: 14px; color: #bbb;"><b>Switch Floor Plan:</b></label>
            <input id="sceneInput" class="scene-input" type="text" placeholder="e.g. FloorPlan202" value="{TARGET_SCENE}" />
            <button class="scene-btn" onclick="requestSceneSwitch()">Load Scene</button>
        </div>
        
        <br/>
        <div id="viewport-container">
            <img id="view" src="" />
            <div id="overlay-msg">Click render view to lock mouse for smooth looking (ESC to release)</div>
        </div>
        
        <br/>
        <div class="telemetry-bar">
            <b>X:</b> <span id="x" class="val-pos">0</span> | 
            <b>Y:</b> <span id="y" class="val-pos">0</span> | 
            <b>Z:</b> <span id="z" class="val-pos">0</span> &nbsp;&nbsp;|&nbsp;&nbsp;
            <b>Rotation:</b> <span id="rot" class="val-rot">0</span>° | 
            <b>Horizon:</b> <span id="hor" class="val-rot">0</span>°
        </div>
        
        <p style="color:#888; font-size: 14px; margin-top: 12px;">
            Controls: <b>W/A/S/D</b> = Move | <b>Mouse</b> = Smooth Look (Click image first)
        </p>
        
        <script>
            const viewImg = document.getElementById('view');
            const overlayMsg = document.getElementById('overlay-msg');
            const sceneInput = document.getElementById('sceneInput');
            const sceneTitle = document.getElementById('sceneTitle');
            
            let isRequestActive = false;
            let pendingLook = {{ yaw: 0, pitch: 0 }};
            const MOUSE_SENSITIVITY = 0.25;

            function updateHUD(data) {{
                if (data.image) {{
                    viewImg.src = "data:image/jpeg;base64," + data.image;
                }}
                document.getElementById('x').innerText = data.x;
                document.getElementById('y').innerText = data.y;
                document.getElementById('z').innerText = data.z;
                document.getElementById('rot').innerText = data.rotation;
                document.getElementById('hor').innerText = data.horizon;
                if (data.sceneTitle) {{
                    sceneTitle.innerText = data.sceneTitle;
                }}
            }}

            async function requestSceneSwitch() {{
                const targetScene = sceneInput.value.trim();
                if (!targetScene) return;
                
                overlayMsg.innerText = "Loading " + targetScene + "...";
                overlayMsg.style.opacity = "1";
                
                try {{
                    const res = await fetch(`/switch_scene?scene_name=${{encodeURIComponent(targetScene)}}`);
                    const data = await res.json();
                    if (data.error) {{
                        alert("Error loading scene: " + data.error);
                        overlayMsg.innerText = "Error loading scene";
                    }} else {{
                        updateHUD(data);
                        overlayMsg.innerText = "Loaded " + targetScene;
                        setTimeout(() => {{
                            overlayMsg.innerText = "Click render view to lock mouse for smooth looking (ESC to release)";
                        }}, 2000);
                    }}
                }} catch (err) {{
                    console.error(err);
                    alert("Network error switching scene.");
                }}
            }}

            sceneInput.addEventListener('keydown', (e) => {{
                e.stopPropagation();
                if (e.key === 'Enter') {{
                    requestSceneSwitch();
                }}
            }});

            async function flushLook() {{
                if (isRequestActive || (pendingLook.yaw === 0 && pendingLook.pitch === 0)) return;
                
                isRequestActive = true;
                const yaw = pendingLook.yaw;
                const pitch = pendingLook.pitch;
                pendingLook.yaw = 0;
                pendingLook.pitch = 0;
                
                try {{
                    const res = await fetch(`/look?yaw=${{yaw.toFixed(2)}}&pitch=${{pitch.toFixed(2)}}`);
                    const data = await res.json();
                    updateHUD(data);
                }} catch(err) {{
                    console.error(err);
                }} finally {{
                    isRequestActive = false;
                    if (pendingLook.yaw !== 0 || pendingLook.pitch !== 0) {{
                        flushLook();
                    }}
                }}
            }}

            async function sendMoveAction(action) {{
                if (isRequestActive) return;
                isRequestActive = true;
                try {{
                    const res = await fetch('/step?action=' + action);
                    const data = await res.json();
                    updateHUD(data);
                }} catch(err) {{
                    console.error(err);
                }} finally {{
                    isRequestActive = false;
                }}
            }}

            viewImg.addEventListener('click', () => {{
                viewImg.requestPointerLock();
            }});

            document.addEventListener('pointerlockchange', () => {{
                if (document.pointerLockElement === viewImg) {{
                    overlayMsg.innerText = "Pointer Locked (ESC to exit)";
                    overlayMsg.style.opacity = "0.4";
                }} else {{
                    overlayMsg.innerText = "Click render view to lock mouse for smooth looking (ESC to release)";
                    overlayMsg.style.opacity = "1";
                }}
            }});

            document.addEventListener('mousemove', (e) => {{
                if (document.pointerLockElement !== viewImg) return;
                
                pendingLook.yaw += e.movementX * MOUSE_SENSITIVITY;
                pendingLook.pitch += e.movementY * MOUSE_SENSITIVITY;
                flushLook();
            }});

            window.addEventListener('keydown', (e) => {{
                if (document.activeElement === sceneInput) return;
                
                const key = e.key.toLowerCase();
                if (key === 'w') sendMoveAction('MoveAhead');
                if (key === 's') sendMoveAction('MoveBack');
                if (key === 'a') sendMoveAction('MoveLeft');
                if (key === 'd') sendMoveAction('MoveRight');
            }});

            sendMoveAction('Pass');
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=args.port)
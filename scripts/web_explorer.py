import os
import sys
import io
import re
import base64
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from thor3d import ThorRenderer

DEFAULT_PORT = 8001
CURRENT_SCENE = "FloorPlan1"
DATASET_TYPE = "ithor"

renderer_instance = None
r = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global renderer_instance, r, CURRENT_SCENE, DATASET_TYPE
    
    renderer_instance = ThorRenderer(width=800, height=600, gpu_device=1, quality="Medium")
    r = renderer_instance.__enter__()
    
    print(f"Initializing iTHOR scene: {CURRENT_SCENE}")
    r.controller.reset(scene=CURRENT_SCENE, snapToGrid=False, autoSimulation=False)
    r.controller.step(action="PausePhysicsAutoSim")
    
    yield
    
    if renderer_instance:
        renderer_instance.__exit__(None, None, None)

app = FastAPI(lifespan=lifespan)

def get_state_response(scene_title=None):
    global CURRENT_SCENE, DATASET_TYPE
    event = r.controller.last_event
    agent = event.metadata['agent']
    
    img = Image.fromarray(event.frame)
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=75)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    title = scene_title or (
        f"iTHOR: {CURRENT_SCENE}" if DATASET_TYPE == "ithor" else f"ProcTHOR: House {CURRENT_SCENE}"
    )
    
    return {
        "image": img_str,
        "x": round(agent['position']['x'], 4),
        "y": round(agent['position']['y'], 4),
        "z": round(agent['position']['z'], 4),
        "rotation": round(agent['rotation']['y'], 4),
        "horizon": round(agent['cameraHorizon'], 4),
        "sceneTitle": title
    }

@app.get("/switch_scene")
def switch_scene(scene_name: str = Query(...)):
    global r, CURRENT_SCENE, DATASET_TYPE
    query = scene_name.strip()
    if not query:
        return JSONResponse({"error": "Empty scene identifier"}, status_code=400)

    try:
        # Check if user entered an integer ID or "procthor:<id>"
        is_numeric = query.isdigit() or (query.lower().startswith("house") and query.split()[-1].isdigit())
        
        if is_numeric or query.lower().startswith("procthor"):
            import prior
            digits = re.findall(r'\d+', query)
            house_id = int(digits[0]) if digits else 0
            
            print(f"Loading ProcTHOR-10k train split, House ID: {house_id}...")
            dataset = prior.load_dataset("procthor-10k")
            house = dataset["train"][house_id]
            
            r.controller.reset(scene="Procedural", snapToGrid=False, autoSimulation=False)
            r.controller.step(action="CreateHouse", house=house)
            r.controller.step(action="PausePhysicsAutoSim")
            
            CURRENT_SCENE = str(house_id)
            DATASET_TYPE = "procthor"
            return get_state_response(scene_title=f"ProcTHOR: House #{house_id} (train)")

        else:
            # Standard iTHOR scene string (e.g., FloorPlan202)
            print(f"Loading iTHOR Scene: {query}...")
            r.controller.reset(scene=query, snapToGrid=False, autoSimulation=False)
            r.controller.step(action="PausePhysicsAutoSim")
            
            CURRENT_SCENE = query
            DATASET_TYPE = "ithor"
            return get_state_response(scene_title=f"iTHOR: {query}")

    except Exception as e:
        print(f"Failed to load scene {query}: {e}")
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
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI2-THOR Interactive Live Explorer</title>
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
                padding: 10px 18px;
                border-radius: 8px;
                display: inline-flex;
                gap: 10px;
                align-items: center;
                margin-bottom: 12px;
                border: 1px solid #3a3a3a;
            }}
            .scene-input {{
                background: #121212;
                border: 1px solid #4CAF50;
                color: #fff;
                padding: 7px 12px;
                border-radius: 4px;
                font-size: 15px;
                font-family: monospace;
                width: 220px;
                text-align: center;
            }}
            .scene-btn {{
                background: #4CAF50;
                color: #fff;
                border: none;
                padding: 8px 16px;
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
                background: rgba(0,0,0,0.75);
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 13px;
                pointer-events: none;
                transition: opacity 0.2s;
            }}
            .telemetry-bar {{
                margin-top: 14px;
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
        <h2 style="margin: 4px 0 12px 0;">AI2-THOR Live Explorer: <span id="sceneTitle" style="color:#FF9800;">iTHOR: FloorPlan1</span></h2>
        
        <div class="scene-bar">
            <label for="sceneInput" style="font-size: 14px; color: #bbb;"><b>Environment:</b></label>
            <input id="sceneInput" class="scene-input" type="text" placeholder="e.g. FloorPlan202 or 12" value="FloorPlan1" />
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
    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT)
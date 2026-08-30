from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import os
import uuid
import json
import uvicorn
from datetime import datetime
import numpy as np
import cv2
import torch
from PIL import Image as PILImage
from io import BytesIO
from segment_anything import sam_model_registry, SamPredictor
from simple_lama_inpainting import SimpleLama

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClickRequest(BaseModel):
    image_b64: str
    x: int
    y: int
    box: list[int] = None

class SaveSessionRequest(BaseModel):
    image_b64: str
    removed_objects: list
    base_scene_name: str

# Load models globally on startup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

sam = sam_model_registry["vit_b"](checkpoint="sam_vit_b_01ec64.pth").to(device)
predictor = SamPredictor(sam)
simple_lama = SimpleLama(device = "cuda")

@app.post("/process_click")
async def process_click(data: ClickRequest):
    try:
        image_data = base64.b64decode(data.image_b64)
        np_arr = np.frombuffer(image_data, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        predictor.set_image(image_rgb)
        
        # Format box prompt for SAM if provided
        box_prompt = np.array(data.box) if data.box else None

        masks, scores, _ = predictor.predict(
            point_coords=np.array([[data.x, data.y]]),
            point_labels=np.array([1]),
            box=box_prompt,
            multimask_output=False
        )
        
        mask = masks[0].astype(np.uint8) * 255

        input_pil = PILImage.fromarray(image_rgb)
        mask_pil = PILImage.fromarray(mask)
        result_pil = simple_lama(input_pil, mask_pil)
        
        buffered = BytesIO()
        result_pil.save(buffered, format="JPEG")
        inpainted_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return {"inpainted_image_b64": inpainted_b64}

    except Exception as e:
        print(f"Error during inpainting: {str(e)}")
        return {"status": "error", "message": str(e)}
@app.post("/save_session")
async def save_session(data: SaveSessionRequest):
    img_dir = os.path.join("output", "Output_Images")
    json_dir = os.path.join("output", "Output_JSON")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    
    session_hash = str(uuid.uuid4())[:8] 
    rendered_image_name = f"{data.base_scene_name}_rendered_{session_hash}.png"
    img_path = os.path.join(img_dir, rendered_image_name)
    master_json_path = os.path.join(json_dir, "master_dataset.json")
    
    try:
        image_bytes = base64.b64decode(data.image_b64)
        with open(img_path, "wb") as img_file:
            img_file.write(image_bytes)
            
        cleaned_objects = [
            {
                "object_id": obj["object_id"], 
                "click_position": obj["click_position"]
            }
            for obj in data.removed_objects
        ]
        
        new_record = {
            "scene_id": data.base_scene_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "rendered_image_name": rendered_image_name,
            "original_image_path": f"Original_Images/{data.base_scene_name}.jpg",
            "modified_image_path": f"Modified_Images/{data.base_scene_name}_modified.png",
            "user_interactions": {
                "removed_objects": cleaned_objects
            }
        }
        
        if os.path.exists(master_json_path):
            with open(master_json_path, "r") as f:
                dataset = json.load(f)
        else:
            dataset = {"dataset_version": "1.0", "sessions": []}
            
        dataset["sessions"].append(new_record)
        with open(master_json_path, "w") as f:
            json.dump(dataset, f, indent=4)
            
        return {"status": "success", "saved_image": rendered_image_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
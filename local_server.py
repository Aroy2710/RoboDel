from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import os
import uuid
import json
import uvicorn
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SaveSessionRequest(BaseModel):
    image_b64: str
    removed_objects: list
    base_scene_name: str

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
            
        # Cleaned object interactions (stripping out mask_area_pixels)
        cleaned_objects = [
            {
                "object_id": obj["object_id"], 
                "click_position": obj["click_position"]
            }
            for obj in data.removed_objects
        ]
        
        # Session record without eye tracking or mask area references
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
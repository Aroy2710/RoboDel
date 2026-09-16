import os
import json
import time
import shutil
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SessionData(BaseModel):
    removed_objects: list
    removed_labels: list
    base_scene_name: str
    final_image_path: str

OUTPUT_DIR = "output"
JSON_DIR = os.path.join(OUTPUT_DIR, "Output_JSON")
IMG_DIR = os.path.join(OUTPUT_DIR, "Output_Images")
MASTER_JSON_PATH = os.path.join(JSON_DIR, "master_dataset.json")
PUBLIC_DIR = "public"

@app.post("/save_session")
def save_session(data: SessionData):
    try:
        os.makedirs(JSON_DIR, exist_ok=True)
        os.makedirs(IMG_DIR, exist_ok=True)
        
        timestamp = int(time.time())
        session_id = f"session_{timestamp}"
        
        if not os.path.exists(MASTER_JSON_PATH):
            master_data = {
                "dataset_version": "1.0",
                "sessions": []
            }
        else:
            try:
                with open(MASTER_JSON_PATH, "r") as f:
                    master_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                master_data = {"dataset_version": "1.0", "sessions": []}
                
        relative_img_path = data.final_image_path.lstrip("/")
        source_img_path = os.path.join(PUBLIC_DIR, relative_img_path)
        
        dest_img_filename = f"{session_id}_{data.base_scene_name}.png"
        dest_img_path = os.path.join(IMG_DIR, dest_img_filename)
        
        if os.path.exists(source_img_path):
            shutil.copy2(source_img_path, dest_img_path)
        else:
            print(f"Warning: Could not find image to copy at {source_img_path}")
            dest_img_path = "Image not found locally"

        session_record = data.dict()
        session_record["session_id"] = session_id
        session_record["saved_image_path"] = dest_img_path
        
        master_data["sessions"].append(session_record)
        
        with open(MASTER_JSON_PATH, "w") as f:
            json.dump(master_data, f, indent=4)
            
        print(f"Successfully saved {session_id} to {MASTER_JSON_PATH}")
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        print(f"Error saving session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
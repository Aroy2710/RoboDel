import os
import json
import time
import shutil
from typing import Optional, List, Dict, Any
from urllib.parse import unquote
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
    participant_id: str
    target_object: str
    removed_objects: list
    removed_labels: list
    base_scene_name: str
    final_image_path: str
    mouse_telemetry: dict
    trial_index: int
    total_trials: int
    trial_duration_sec: float
    total_experiment_duration_sec: float
    is_early_exit: bool = False

class ExitSessionData(BaseModel):
    participant_id: str
    trials_completed: int
    total_trials: int
    completion_rate: float
    total_experiment_duration_sec: float
    reason: str = "user_requested_exit"

class SurveyResponse(BaseModel):
    participant_id: str
    ease_of_use_score: int
    mouse_control_comfort: Optional[str] = None
    visual_fatigue: Optional[str] = None
    ux_improvement_suggestions: Optional[str] = ""
    experienced_glitches: Optional[str] = ""
    additional_notes: Optional[str] = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
JSON_DIR = os.path.join(OUTPUT_DIR, "Output_JSON")
IMG_DIR = os.path.join(OUTPUT_DIR, "Output_Images")
MASTER_JSON_PATH = os.path.join(JSON_DIR, "master_dataset.json")
SURVEY_JSON_PATH = os.path.join(JSON_DIR, "survey_feedback_master.json")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

def load_or_init_json(filepath: str, default_structure: dict) -> dict:
    if not os.path.exists(filepath):
        return default_structure
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return default_structure
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return default_structure

@app.post("/save_session")
def save_session(data: SessionData):
    try:
        os.makedirs(JSON_DIR, exist_ok=True)
        os.makedirs(IMG_DIR, exist_ok=True)
        
        timestamp = int(time.time())
        session_id = f"session_{timestamp}"
        
        master_data = load_or_init_json(
            MASTER_JSON_PATH, 
            {"dataset_version": "1.0", "participants": {}, "sessions": []}
        )

        if "participants" not in master_data or not isinstance(master_data["participants"], dict):
            master_data["participants"] = {}
        if "sessions" not in master_data or not isinstance(master_data["sessions"], list):
            master_data["sessions"] = []
        
        clean_image_path = unquote(data.final_image_path)
        relative_img_path = clean_image_path.lstrip("/")
        source_img_path = os.path.join(PUBLIC_DIR, relative_img_path)
        ext = os.path.splitext(clean_image_path)[1] or ".jpg"
        dest_img_filename = f"{session_id}_{data.base_scene_name}{ext}"
        dest_img_path = os.path.join(IMG_DIR, dest_img_filename)
        
        if os.path.exists(source_img_path):
            shutil.copy2(source_img_path, dest_img_path)
            saved_record_path = os.path.join("output", "Output_Images", dest_img_filename)
        else:
            saved_record_path = "Image not found locally"

        session_record = data.dict()
        session_record["session_id"] = session_id
        session_record["saved_image_path"] = saved_record_path
        session_record["timestamp"] = timestamp
        master_data["sessions"].append(session_record)

        pid = data.participant_id
        completed_count = data.trial_index + 1
        completion_rate = round(completed_count / data.total_trials, 4)
        current_status = "early_exit" if data.is_early_exit else ("completed" if completed_count >= data.total_trials else "in_progress")

        master_data["participants"][pid] = {
            "participant_id": pid,
            "trials_completed": completed_count,
            "total_trials": data.total_trials,
            "completion_rate": completion_rate,
            "total_experiment_duration_sec": round(data.total_experiment_duration_sec, 2),
            "status": current_status
        }
        
        with open(MASTER_JSON_PATH, "w") as f:
            json.dump(master_data, f, indent=4)
            
        print(f"Successfully saved session {session_id} for participant {pid}")
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        print(f"Error saving session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/record_early_exit")
def record_early_exit(data: ExitSessionData):
    try:
        os.makedirs(JSON_DIR, exist_ok=True)
        master_data = load_or_init_json(
            MASTER_JSON_PATH, 
            {"dataset_version": "1.0", "participants": {}, "sessions": []}
        )

        if "participants" not in master_data or not isinstance(master_data["participants"], dict):
            master_data["participants"] = {}

        pid = data.participant_id
        master_data["participants"][pid] = {
            "participant_id": pid,
            "trials_completed": data.trials_completed,
            "total_trials": data.total_trials,
            "completion_rate": round(data.completion_rate, 4),
            "total_experiment_duration_sec": round(data.total_experiment_duration_sec, 2),
            "status": "early_exit"
        }

        with open(MASTER_JSON_PATH, "w") as f:
            json.dump(master_data, f, indent=4)

        return {"status": "success", "message": f"Exit logged for {pid}"}
    except Exception as e:
        print(f"Error logging early exit: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save_survey")
def save_survey(survey: SurveyResponse):
    try:
        os.makedirs(JSON_DIR, exist_ok=True)
        survey_data = load_or_init_json(
            SURVEY_JSON_PATH, 
            {"survey_version": "1.0", "responses": []}
        )

        if "responses" not in survey_data or not isinstance(survey_data["responses"], list):
            survey_data["responses"] = []

        record = survey.dict()
        record["submission_time_iso"] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        existing_idx = next((i for i, r in enumerate(survey_data["responses"]) if r.get("participant_id") == survey.participant_id), None)
        if existing_idx is not None:
            survey_data["responses"][existing_idx] = record
        else:
            survey_data["responses"].append(record)

        with open(SURVEY_JSON_PATH, "w") as f:
            json.dump(survey_data, f, indent=4)

        print(f"Survey feedback saved for participant: {survey.participant_id}")
        return {"status": "success"}
    except Exception as e:
        print(f"Error saving survey: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
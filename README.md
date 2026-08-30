To add a new scene in the future, you only need to follow these three simple steps:

Drop the new original image into public/Original_Images/ and your modified image into public/Modified_Images/.

Append its respective bounding box rows into public/Bouding_Boxes/bounding_box.csv (exported from Makesense.ai).

Add the new scene identifier string to your sceneList array in App.js (e.g., ["robothor_scene_01", "robothor_scene_02", "robothor_scene_03"]).

run local_server to save your data
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Papa from 'papaparse';

const PHASES = {
  OBSERVATION: 0,
  TRANSITION: 1,
  INTERACTIVE: 2,
  CONFIRMATION: 3,
  COMPLETED: 4
};

const MAX_SEND_WIDTH = 3000;

function App() {
  const sceneList = ["robothor_scene_01", "robothor_scene_02", "robothor_scene_03"];
  const [sceneIndex, setSceneIndex] = useState(0);
  const baseSceneName = sceneList[sceneIndex];

  const originalImage = `/Original_Images/${baseSceneName}.jpg`;
  const modifiedImage = `/Modified_Images/${baseSceneName}_modified.jpg`;

  const [phase, setPhase] = useState(PHASES.OBSERVATION);
  const [timeLeft, setTimeLeft] = useState(10);
  const [isProcessing, setIsProcessing] = useState(false);

  const [displayImage, setDisplayImage] = useState(modifiedImage);
  const workingImageRef = useRef(null);

  const [imageHistory, setImageHistory] = useState([]);
  const [removedObjects, setRemovedObjects] = useState([]);
  const [boundingboxes, setBoundingBoxes] = useState([]);
  const [naturalDims, setNaturalDims] = useState(null);

  // Reset and load images when sceneIndex changes
  useEffect(() => {
    setDisplayImage(modifiedImage);
    setRemovedObjects([]);
    setImageHistory([]);
    setTimeLeft(10);
    setPhase(PHASES.OBSERVATION);

    const ref = new Image();
    ref.crossOrigin = "anonymous";
    ref.onload = () => {
      setNaturalDims({ width: ref.naturalWidth, height: ref.naturalHeight });
      workingImageRef.current = ref;
    };
    ref.src = modifiedImage;
  }, [sceneIndex, modifiedImage]);

  // Load bounding boxes from CSV on mount or scene change
  useEffect(() => {
    fetch('/Bouding_Boxes/bounding_box.csv')
      .then(response => response.text())
      .then(csvText => {
        Papa.parse(csvText, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
          complete: (results) => {
            const sceneBoxes = results.data
              .filter(row => row.image_name === `${baseSceneName}_modified.jpg` || row.image_name.includes(baseSceneName))
              .map((row, index) => ({
                id: index + 1,
                x: row.bbox_x,
                y: row.bbox_y,
                width: row.bbox_width,
                height: row.bbox_height,
                isClicked: false
              }));
            console.log(`Loaded Bounding Boxes for ${baseSceneName}:`, sceneBoxes);
            setBoundingBoxes(sceneBoxes);
          }
        });
      });
  }, [baseSceneName]);

  // Observation Timer
  useEffect(() => {
    if (phase === PHASES.OBSERVATION) {
      if (timeLeft > 0) {
        const timerId = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
        return () => clearTimeout(timerId);
      } else {
        setPhase(PHASES.TRANSITION);
        setTimeout(() => setPhase(PHASES.INTERACTIVE), 500);
      }
    }
  }, [timeLeft, phase]);

  // Perfect Stack (LIFO) Undo with explicit boxIndex pairing
  const handleUndo = () => {
    if (imageHistory.length > 0) {
      const previous = imageHistory[imageHistory.length - 1];
      setDisplayImage(previous.display);
      workingImageRef.current = previous.working;
      setImageHistory(imageHistory.slice(0, -1));
      setRemovedObjects(prev => prev.slice(0, -1));

      setBoundingBoxes(prev => prev.map((box, index) => {
        if (index === previous.boxIndex) {
          return { ...box, isClicked: false };
        }
        return box;
      }));
    }
  };

  const handleImageClick = async (event) => {
    if (isProcessing || !naturalDims || !workingImageRef.current) return;

    const imgElement = document.getElementById('interactive-scene-img');
    if (!imgElement) return;

    const rect = imgElement.getBoundingClientRect();
    const scaleX = naturalDims.width / rect.width;
    const scaleY = naturalDims.height / rect.height;
    const x = Math.round((event.clientX - rect.left) * scaleX);
    const y = Math.round((event.clientY - rect.top) * scaleY);

    const clickedBoxIndex = boundingboxes.findIndex(box =>
      !box.isClicked &&
      x >= box.x && x <= box.x + box.width &&
      y >= box.y && y <= box.y + box.height
    );

    if (clickedBoxIndex === -1) return;

    setIsProcessing(true);
    
    // Save state stack including the exact boxIndex for perfect LIFO undo tracking
    setImageHistory(prev => [
      ...prev,
      { 
        display: displayImage, 
        working: workingImageRef.current, 
        boxIndex: clickedBoxIndex 
      }
    ]);

    try {
      const fullWidth = naturalDims.width;
      const fullHeight = naturalDims.height;

      let targetWidth = fullWidth;
      let targetHeight = fullHeight;
      if (targetWidth > MAX_SEND_WIDTH) {
        const scaleDown = MAX_SEND_WIDTH / targetWidth;
        targetWidth = MAX_SEND_WIDTH;
        targetHeight = Math.round(targetHeight * scaleDown);
      }

      const sendCanvas = document.createElement('canvas');
      sendCanvas.width = targetWidth;
      sendCanvas.height = targetHeight;
      const sendCtx = sendCanvas.getContext('2d');
      sendCtx.drawImage(workingImageRef.current, 0, 0, targetWidth, targetHeight);

      const cleanB64 = sendCanvas.toDataURL('image/jpeg', 0.9).split(',')[1];
      const scaledX = Math.round(x * (targetWidth / fullWidth));
      const scaledY = Math.round(y * (targetHeight / fullHeight));

      const response = await axios.post('https://multitude-resupply-apply.ngrok-free.dev/process_click', {
        image_b64: cleanB64,
        x: scaledX,
        y: scaledY
      }, {
        headers: { 'ngrok-skip-browser-warning': 'true' },
        timeout: 60000
      });

      const returnedB64 = response.data.inpainted_image_b64;
      const displaySafeB64 = returnedB64.startsWith('data:image')
        ? returnedB64
        : `data:image/jpeg;base64,${returnedB64}`;

      setDisplayImage(displaySafeB64);

      const inpaintedImg = await new Promise((resolve, reject) => {
        const im = new Image();
        im.crossOrigin = "anonymous";
        im.onload = () => resolve(im);
        im.onerror = reject;
        im.src = displaySafeB64;
      });

      const fullCanvas = document.createElement('canvas');
      fullCanvas.width = fullWidth;
      fullCanvas.height = fullHeight;
      const fullCtx = fullCanvas.getContext('2d');
      fullCtx.drawImage(inpaintedImg, 0, 0, fullWidth, fullHeight);

      const newWorkingImg = await new Promise((resolve, reject) => {
        const im = new Image();
        im.onload = () => resolve(im);
        im.onerror = reject;
        im.src = fullCanvas.toDataURL('image/png');
      });
      workingImageRef.current = newWorkingImg;

      setBoundingBoxes(prev => prev.map((box, index) =>
        index === clickedBoxIndex ? { ...box, isClicked: true } : box
      ));

      const targetBox = boundingboxes[clickedBoxIndex];
      setRemovedObjects(prev => [...prev, {
        object_id: targetBox.id,
        bounding_box: { x: targetBox.x, y: targetBox.y, width: targetBox.width, height: targetBox.height },
        click_position: { x, y }
      }]);

    } catch (error) {
      console.error("API error:", error);
      setImageHistory(prev => prev.slice(0, -1));
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFinish = async () => {
    setIsProcessing(true);
    try {
      const fullCanvas = document.createElement('canvas');
      fullCanvas.width = naturalDims.width;
      fullCanvas.height = naturalDims.height;
      fullCanvas.getContext('2d').drawImage(workingImageRef.current, 0, 0);
      const finalB64 = fullCanvas.toDataURL('image/png').split(',')[1];

      await axios.post('http://localhost:8000/save_session', {
        image_b64: finalB64,
        removed_objects: removedObjects,
        base_scene_name: baseSceneName
      });

      if (sceneIndex + 1 < sceneList.length) {
        setSceneIndex(sceneIndex + 1);
      } else {
        setPhase(PHASES.COMPLETED);
      }
    } catch (error) {
      console.error("Error saving session:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '20px' }}>
      {phase === PHASES.OBSERVATION && (
        <div style={{ textAlign: 'center' }}>
          <h2>Scene {sceneIndex + 1} of {sceneList.length}: Observe the Scene ({timeLeft}s remaining)</h2>
          <img src={originalImage} alt="Observation" style={{ maxWidth: '800px', border: '2px solid #ccc' }} />
        </div>
      )}

      {phase === PHASES.TRANSITION && <div style={{ textAlign: 'center' }}><h2>Transitioning to Scene {sceneIndex + 1}...</h2></div>}

      {phase === PHASES.INTERACTIVE && (
        <div style={{ display: 'flex', gap: '40px', justifyContent: 'center' }}>
          <div>
            <h3>Scene {sceneIndex + 1}: Target Reference</h3>
            <img src={modifiedImage} alt="Modified Reference" style={{ maxWidth: '500px', border: '2px solid #555' }} />
          </div>

          <div>
            <h3>Interactive Manipulation</h3>
            <div style={{ marginBottom: '15px' }}>
              <button onClick={handleUndo} disabled={imageHistory.length === 0 || isProcessing} style={{ padding: '8px 16px', marginRight: '10px' }}>
                Undo Last Action
              </button>
              <button onClick={() => setPhase(PHASES.CONFIRMATION)} disabled={isProcessing} style={{ padding: '8px 16px', backgroundColor: '#e0e0e0' }}>
                Review and Save
              </button>
            </div>

            <div style={{ position: 'relative', display: 'inline-block', lineHeight: 0 }}>
              <img
                id="interactive-scene-img"
                src={displayImage}
                onClick={handleImageClick}
                alt="Interactive Scene"
                style={{ width: '500px', height: 'auto', border: '2px solid blue', cursor: isProcessing ? 'wait' : 'crosshair', display: 'block' }}
              />

              {naturalDims && boundingboxes.map((box) => {
                const leftPercent = (box.x / naturalDims.width) * 100;
                const topPercent = (box.y / naturalDims.height) * 100;
                const widthPercent = (box.width / naturalDims.width) * 100;
                const heightPercent = (box.height / naturalDims.height) * 100;

                return (
                  <div
                    key={box.id}
                    style={{
                      position: 'absolute',
                      left: `${leftPercent}%`,
                      top: `${topPercent}%`,
                      width: `${widthPercent}%`,
                      height: `${heightPercent}%`,
                      border: `2px solid ${box.isClicked ? 'red' : 'green'}`,
                      backgroundColor: box.isClicked ? 'rgba(255, 0, 0, 0.2)' : 'rgba(0, 255, 0, 0.1)',
                      pointerEvents: 'none'
                    }}
                  />
                );
              })}
            </div>
          </div>
        </div>
      )}

      {phase === PHASES.CONFIRMATION && (
        <div style={{ textAlign: 'center' }}>
          <h2>Confirm Final Image (Scene {sceneIndex + 1})</h2>
          <img src={displayImage} alt="Final Scene" style={{ maxWidth: '600px', border: '3px solid green', marginBottom: '20px' }} />
          <br />
          <button onClick={handleFinish} disabled={isProcessing} style={{ padding: '10px 20px', backgroundColor: '#4CAF50', color: 'white', marginRight: '15px' }}>
            {isProcessing ? 'Saving...' : (sceneIndex + 1 < sceneList.length ? 'Save & Next Scene' : 'Save & Finish Program')}
          </button>
          <button onClick={() => setPhase(PHASES.INTERACTIVE)} disabled={isProcessing} style={{ padding: '10px 20px' }}>
            Back to Editing
          </button>
        </div>
      )}

      {phase === PHASES.COMPLETED && (
        <div style={{ textAlign: 'center', marginTop: '50px' }}>
          <h2>All Sessions Complete!</h2>
          <p>You have successfully completed all {sceneList.length} scenes.</p>
        </div>
      )}
    </div>
  );
}

export default App;
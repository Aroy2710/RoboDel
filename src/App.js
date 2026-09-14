import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Papa from 'papaparse';
import './App.css';

const API_URL = "http://localhost:8000";
const PHASES = {
  FIXATION: -1,
  INSTRUCTIONS: -2,
  OBSERVATION: 0,
  TRANSITION: 1,
  INTERACTIVE: 2,
  COMPLETED: 3
};

const FIXATION_DURATION_SECONDS = 5;
const OBSERVATION_DURATION_SECONDS = 10;
const MAX_SEND_WIDTH = 1000;

function App() {
  const sceneList = ["robothor_scene_01", "robothor_scene_02", "robothor_scene_03"];
  const [sceneIndex, setSceneIndex] = useState(0);
  const baseSceneName = sceneList[sceneIndex];

  const originalImage = `/Original_Images/${baseSceneName}.jpg`;
  const modifiedImage = `/Modified_Images/${baseSceneName}_modified.jpg`;

  const [phase, setPhase] = useState(PHASES.FIXATION);
  const [fixationTimeLeft, setFixationTimeLeft] = useState(FIXATION_DURATION_SECONDS);
  const [timeLeft, setTimeLeft] = useState(OBSERVATION_DURATION_SECONDS);
  const [isProcessing, setIsProcessing] = useState(false);

  const [displayImage, setDisplayImage] = useState(modifiedImage);
  const workingImageRef = useRef(null);

  const [imageHistory, setImageHistory] = useState([]);
  const [removedObjects, setRemovedObjects] = useState([]);
  const [boundingboxes, setBoundingBoxes] = useState([]);
  const [naturalDims, setNaturalDims] = useState(null);

  // Handle scene resets & transitions
  useEffect(() => {
    setDisplayImage(modifiedImage);
    setRemovedObjects([]);
    setImageHistory([]);
    setTimeLeft(OBSERVATION_DURATION_SECONDS);
    setFixationTimeLeft(FIXATION_DURATION_SECONDS);
    setPhase(PHASES.FIXATION);

    const ref = new Image();
    ref.crossOrigin = "anonymous";
    ref.onload = () => {
      setNaturalDims({ width: ref.naturalWidth, height: ref.naturalHeight });
      workingImageRef.current = ref;
    };
    ref.src = modifiedImage;
  }, [sceneIndex, modifiedImage]);

  // Load bounding boxes from CSV
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
              .filter(row => row.image_name === `${baseSceneName}_modified.jpg` || row.image_name?.includes(baseSceneName))
              .map((row, index) => ({
                id: index + 1,
                x: row.bbox_x,
                y: row.bbox_y,
                width: row.bbox_width,
                height: row.bbox_height,
                isClicked: false
              }));
            setBoundingBoxes(sceneBoxes);
          }
        });
      });
  }, [baseSceneName]);

  // Fixation Timer (5 seconds) -> Directs to Instructions if Scene 1, else directly to Observation
  useEffect(() => {
    if (phase === PHASES.FIXATION) {
      if (fixationTimeLeft > 0) {
        const timerId = setTimeout(() => setFixationTimeLeft(fixationTimeLeft - 1), 1000);
        return () => clearTimeout(timerId);
      } else {
        if (sceneIndex === 0) {
          setPhase(PHASES.INSTRUCTIONS);
        } else {
          setPhase(PHASES.OBSERVATION);
        }
      }
    }
  }, [fixationTimeLeft, phase, sceneIndex]);

  // Observation Timer (10 seconds)
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

  // Stack Undo tracking
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

      const targetBox = boundingboxes[clickedBoxIndex];
      const scaleW = targetWidth / fullWidth;
      const scaleH = targetHeight / fullHeight;
      const scaledBox = [
        Math.round(targetBox.x * scaleW),
        Math.round(targetBox.y * scaleH),
        Math.round((targetBox.x + targetBox.width) * scaleW),
        Math.round((targetBox.y + targetBox.height) * scaleH)
      ];

      const response = await axios.post(`${API_URL}/process_click`, {
        image_b64: cleanB64,
        x: scaledX,
        y: scaledY,
        box: scaledBox
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

  // Direct auto-save and transition to next scene
  const handleReviewAndSave = async () => {
    setIsProcessing(true);
    try {
      const fullCanvas = document.createElement('canvas');
      fullCanvas.width = naturalDims.width;
      fullCanvas.height = naturalDims.height;
      fullCanvas.getContext('2d').drawImage(workingImageRef.current, 0, 0);
      const finalB64 = fullCanvas.toDataURL('image/png').split(',')[1];

      await axios.post(`${API_URL}/save_session`, {
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
      console.error("Error auto-saving session:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="app-container">
      {/* 1. Red Fixation Cross Screen (5s duration) */}
      {phase === PHASES.FIXATION && (
        <div className="fixation-screen">
          <div className="fixation-cross" />
        </div>
      )}

      {/* 2. Instructions Screen (Scene 1 only) */}
      {phase === PHASES.INSTRUCTIONS && (
        <div className="instructions-screen">
          <div className="instructions-card">
            <h2>Experiment Instructions</h2>
            <ul>
              <li>
                <span className="step-num">1</span>
                <div><strong>Observe:</strong> You will view the original scene for 10 seconds. Observer the scene however you want.</div>
              </li>
              <li>
                <span className="step-num">2</span>
                <div><strong>Modify:</strong> The image will be shown to you again with newer objects . Click to remove objects that you believe were not in the original image.</div>
              </li>
              <li>
                <span className="step-num">3</span>
                <div><strong>Save:</strong> Click "Save & Next" to immediately save your results to the server and advance.</div>
              </li>
            </ul>
            <button 
              className="start-btn" 
              onClick={() => setPhase(PHASES.OBSERVATION)}
            >
              Start Observation
            </button>
          </div>
        </div>
      )}

      {/* 3. Fullscreen Observation Phase (10s duration, no overlays) */}
      {phase === PHASES.OBSERVATION && (
        <div className="observable-screen">
          <img 
            src={originalImage} 
            alt="Observation View" 
            className="observable-image" 
          />
        </div>
      )}

      {/* 4. Transition Screen */}
      {phase === PHASES.TRANSITION && (
        <div className="centered-view">
          <h2>Transitioning to Interactive Mode...</h2>
        </div>
      )}

      {/* 5. Enlarged Interactive Workspace */}
      {phase === PHASES.INTERACTIVE && (
        <div className="interactive-layout">
          <div className="interactive-toolbar">
            <h2>Scene {sceneIndex + 1}: Interactive Modification</h2>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button 
                onClick={handleUndo} 
                disabled={imageHistory.length === 0 || isProcessing}
                className="btn-secondary"
              >
                Undo Last Action
              </button>
              <button 
                onClick={handleReviewAndSave} 
                disabled={isProcessing}
                className="btn-primary"
              >
                {isProcessing ? 'Saving to Server...' : (sceneIndex + 1 < sceneList.length ? 'Save & Next' : 'Save & Finish')}
              </button>
            </div>
          </div>

          <div className="interactive-windows-grid">
            {/* Left Interactive Target Panel */}
            <div className="interactive-card">
              <div className="interactive-card-title">Interactive Image(Remove objects that were not in the original image) </div>
              <div className="interactive-viewport-wrapper">
                <div style={{ position: 'relative', display: 'inline-block', lineHeight: 0, maxHeight: '100%', maxWidth: '100%' }}>
                  <img
                    id="interactive-scene-img"
                    src={modifiedImage}
                    onClick={handleImageClick}
                    alt="Interactive Target"
                    className="interactive-viewport-img"
                    style={{ cursor: isProcessing ? 'wait' : 'crosshair' }}
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
                          border: `2px solid ${box.isClicked ? '#ef4444' : '#22c55e'}`,
                          backgroundColor: box.isClicked ? 'rgba(239, 68, 68, 0.25)' : 'rgba(34, 197, 94, 0.15)',
                          pointerEvents: 'none'
                        }}
                      />
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Right Inpainted Result View */}
            <div className="interactive-card">
              <div className="interactive-card-title">Current Render</div>
              <div className="interactive-viewport-wrapper">
                <img 
                  src={displayImage} 
                  alt="Inpainted State" 
                  className="interactive-viewport-img"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 6. Completed Phase */}
      {phase === PHASES.COMPLETED && (
        <div className="centered-view">
          <h2>All Sessions Complete</h2>
          <p style={{ marginTop: '12px', color: '#9ca3af' }}>
            All scenes have been modified and saved to the server.
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
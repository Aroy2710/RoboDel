import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = "http://localhost:8000";
const PHASES = {
  FIXATION: -1,
  OBSERVATION: 0,
  TRANSITION: 1,
  INTERACTIVE: 2,
  COMPLETED: 3
};

const FIXATION_DURATION_SECONDS = 5;
const OBSERVATION_DURATION_SECONDS = 1000000; // Reduced to 5 seconds

// Sequence of trial directories
const TRIAL_SEQUENCE = [
  "Trial_1_FP1_Island",
  "Trial_2_FP2_Table"
];

function App() {
  const [currentTrialIndex, setCurrentTrialIndex] = useState(0);
  const activeFolder = TRIAL_SEQUENCE[currentTrialIndex] || TRIAL_SEQUENCE[0];

  // Dynamic paths based on active trial folder
  const modifiedImage = `/Prerendered_Scenes/${activeFolder}/base.jpg`;
  const originalImage = modifiedImage;

  const [phase, setPhase] = useState(PHASES.FIXATION);
  const [fixationTimeLeft, setFixationTimeLeft] = useState(FIXATION_DURATION_SECONDS);
  const [timeLeft, setTimeLeft] = useState(OBSERVATION_DURATION_SECONDS);
  const [isProcessing, setIsProcessing] = useState(false);

  const [displayImage, setDisplayImage] = useState(modifiedImage);
  const workingImageRef = useRef(null);
  
  // Canvas and Telemetry Refs
  const canvasRef = useRef(null);
  const blurredCanvasRef = useRef(document.createElement('canvas'));
  const telemetryRef = useRef([]);
  const renderFrameRef = useRef();
  const currentMouseRef = useRef({ x: 0, y: 0 });

  const [removedObjects, setRemovedObjects] = useState([]);
  const [removedLabels, setRemovedLabels] = useState([]);
  const [boundingboxes, setBoundingBoxes] = useState([]);
  const [naturalDims, setNaturalDims] = useState(null);

  // Initialize display and image natural dimensions when trial advances
  useEffect(() => {
    setDisplayImage(modifiedImage);
    setRemovedObjects([]);
    setRemovedLabels([]);
    setTimeLeft(OBSERVATION_DURATION_SECONDS);
    setFixationTimeLeft(FIXATION_DURATION_SECONDS);
    setPhase(PHASES.FIXATION);
    telemetryRef.current = []; // Reset telemetry for new trial
    currentMouseRef.current = { x: 0, y: 0 }; 

    const ref = new Image();
    ref.crossOrigin = "anonymous";
    ref.onload = () => {
      setNaturalDims({ width: ref.naturalWidth, height: ref.naturalHeight });
      workingImageRef.current = ref;
    };
    ref.src = modifiedImage;
  }, [currentTrialIndex, modifiedImage]);

  // Load bounding boxes for active trial folder
  useEffect(() => {
    if (currentTrialIndex >= TRIAL_SEQUENCE.length) return;

    fetch(`/Prerendered_Scenes/${activeFolder}/bounding_boxes.json`)
      .then(response => response.json())
      .then(data => {
        setBoundingBoxes(data);
      })
      .catch(error => console.error(`Failed to load bounding boxes for ${activeFolder}:`, error));
  }, [activeFolder, currentTrialIndex]);

  // Fixation Timer -> Directs to Observation
  useEffect(() => {
    if (phase === PHASES.FIXATION) {
      if (fixationTimeLeft > 0) {
        const timerId = setTimeout(() => setFixationTimeLeft(fixationTimeLeft - 1), 1000);
        return () => clearTimeout(timerId);
      } else {
        setPhase(PHASES.OBSERVATION);
      }
    }
  }, [fixationTimeLeft, phase]);

  // SALICON Mouse-Contingent Rendering & Telemetry Logic
  useEffect(() => {
    if (phase === PHASES.OBSERVATION && naturalDims && workingImageRef.current) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      
      const ctx = canvas.getContext('2d');
      const img = workingImageRef.current;

      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;

      const bCanvas = blurredCanvasRef.current;
      bCanvas.width = img.naturalWidth;
      bCanvas.height = img.naturalHeight;
      const bCtx = bCanvas.getContext('2d');
      bCtx.filter = 'blur(15px)'; // A6 equivalent extreme Gaussian low-pass
      bCtx.drawImage(img, 0, 0);

      // SALICON Mathematical Constants
      const P_PX_PER_DEG = 29.719; // Target viewing distance parameter
      const ALPHA_DEG = 2.5;       // 50% sharpness visual angle
      const CURSOR_DEG = 2.0;      // Visible cursor ring radius

      // Convert visual angles to physical pixel radii
      const alpha_px = P_PX_PER_DEG * ALPHA_DEG;          
      const cursor_radius_px = P_PX_PER_DEG * CURSOR_DEG; 

      // Max radius large enough to cover the screen corners
      const MAX_BLEND_RADIUS = Math.max(canvas.width, canvas.height); 

      const handleMouseMove = (e) => {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const x = (e.clientX - rect.left) * scaleX;
        const y = (e.clientY - rect.top) * scaleY;

        currentMouseRef.current = { x, y };

        if (renderFrameRef.current) cancelAnimationFrame(renderFrameRef.current);
        renderFrameRef.current = requestAnimationFrame(() => {
          ctx.clearRect(0, 0, canvas.width, canvas.height);

          // 1. Draw the fully blurred low-res image (A_i)
          ctx.globalCompositeOperation = 'source-over';
          ctx.drawImage(bCanvas, 0, 0);

          // 2. Erase the blur using Formula: R(x,y) = alpha / (alpha + theta)
          ctx.globalCompositeOperation = 'destination-out';
          const gradient = ctx.createRadialGradient(x, y, 0, x, y, MAX_BLEND_RADIUS);
          
          const numStops = 40; 
          for (let i = 0; i <= numStops; i++) {
              const fraction = Math.pow(i / numStops, 2); 
              const r = fraction * MAX_BLEND_RADIUS;
              
              const R_val = alpha_px / (alpha_px + r); 
              gradient.addColorStop(fraction, `rgba(0, 0, 0, ${R_val})`);
          }

          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.rect(0, 0, canvas.width, canvas.height);
          ctx.fill();

          // 3. Draw the high-res crisp image BEHIND the erased mask (I_high)
          ctx.globalCompositeOperation = 'destination-over';
          ctx.drawImage(img, 0, 0);

          // 4. Draw the visible red cursor ring
          ctx.globalCompositeOperation = 'source-over';
          ctx.strokeStyle = 'rgba(255, 0, 0, 0.65)';
          ctx.lineWidth = 2 * scaleX; 
          ctx.beginPath();
          ctx.arc(x, y, cursor_radius_px, 0, 2 * Math.PI);
          ctx.stroke();
        });
      };

      canvas.addEventListener('mousemove', handleMouseMove);
      
      // Telemetry recorded strictly at 300ms intervals
      const telemetryIntervalId = setInterval(() => {
        const { x, y } = currentMouseRef.current;
        if (x !== 0 || y !== 0) {
          telemetryRef.current.push({ t: performance.now(), x: Math.round(x), y: Math.round(y) });
        }
      }, 300);

      const timerId = setTimeout(() => {
        setPhase(PHASES.TRANSITION);
        setTimeout(() => setPhase(PHASES.INTERACTIVE), 500);
      }, OBSERVATION_DURATION_SECONDS * 1000);

      return () => {
        canvas.removeEventListener('mousemove', handleMouseMove);
        clearInterval(telemetryIntervalId);
        clearTimeout(timerId);
        if (renderFrameRef.current) cancelAnimationFrame(renderFrameRef.current);
      };
    }
  }, [phase, naturalDims]);

  const handleImageClick = (event) => {
    if (isProcessing || !naturalDims || !workingImageRef.current) return;

    const imgElement = document.getElementById('interactive-scene-img');
    if (!imgElement) return;

    const rect = imgElement.getBoundingClientRect();
    const scaleX = naturalDims.width / rect.width;
    const scaleY = naturalDims.height / rect.height;
    const x = Math.round((event.clientX - rect.left) * scaleX);
    const y = Math.round((event.clientY - rect.top) * scaleY);

    const clickedBoxIndex = boundingboxes.findIndex(box =>
      x >= box.x && x <= box.x + box.width &&
      y >= box.y && y <= box.y + box.height
    );

    if (clickedBoxIndex === -1) return;

    const targetBox = boundingboxes[clickedBoxIndex];
    const clickedLabel = targetBox.label.toLowerCase();
    const isCurrentlyClicked = targetBox.isClicked;

    let newRemovedLabels;
    let newRemovedObjects;

    if (isCurrentlyClicked) {
      newRemovedLabels = removedLabels.filter(label => label !== clickedLabel);
      newRemovedObjects = removedObjects.filter(obj => obj.object_id !== targetBox.id);
    } else {
      newRemovedLabels = [...removedLabels, clickedLabel];
      newRemovedObjects = [...removedObjects, {
        object_id: targetBox.id,
        label: targetBox.label,
        bounding_box: { x: targetBox.x, y: targetBox.y, width: targetBox.width, height: targetBox.height },
        click_position: { x, y }
      }];
    }

    setRemovedLabels(newRemovedLabels);
    setRemovedObjects(newRemovedObjects);

    const sortedLabels = [...newRemovedLabels].sort();
    const filename = sortedLabels.length === 0 
      ? "base.jpg" 
      : `removed_${sortedLabels.join('_')}.jpg`;

    const newImageSrc = `/Prerendered_Scenes/${activeFolder}/${filename}`;
    setDisplayImage(newImageSrc);

    setBoundingBoxes(prev => prev.map((box, index) =>
      index === clickedBoxIndex ? { ...box, isClicked: !isCurrentlyClicked } : box
    ));
  };

  const handleReviewAndSave = async () => {
    setIsProcessing(true);
    try {
      const rawTelemetry = telemetryRef.current;
      
      const formattedTelemetry = {
        X: rawTelemetry.map(p => Number(p.x.toFixed(1))),
        Y: rawTelemetry.map(p => Number(p.y.toFixed(1))),
        T: rawTelemetry.map(p => Math.round(p.t - (rawTelemetry.length > 0 ? rawTelemetry[0].t : 0))),
        length: rawTelemetry.length
      };

      await axios.post(`${API_URL}/save_session`, {
        removed_objects: removedObjects,
        removed_labels: removedLabels,
        base_scene_name: activeFolder,
        final_image_path: displayImage,
        mouse_telemetry: formattedTelemetry 
      });

      if (currentTrialIndex + 1 < TRIAL_SEQUENCE.length) {
        setCurrentTrialIndex(prev => prev + 1);
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
    <div className="app-container">
      {/* 1. Fixation Screen */}
      {phase === PHASES.FIXATION && (
        <div className="fixation-screen">
          <div className="fixation-cross" />
        </div>
      )}

      {/* 2. Observation Phase */}
      {phase === PHASES.OBSERVATION && (
        <div className="observable-screen">
          <canvas
            ref={canvasRef}
            className="observable-image"
            style={{ pointerEvents: 'auto', cursor: 'none' }}
          />
        </div>
      )}

      {/* 3. Transition Screen */}
      {phase === PHASES.TRANSITION && (
        <div className="centered-view">
          <h2>Transitioning to Interactive Mode...</h2>
        </div>
      )}

      {/* 4. Interactive Workspace */}
      {phase === PHASES.INTERACTIVE && (
        <div className="interactive-layout">
          <div className="interactive-toolbar">
            <h2></h2>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={handleReviewAndSave}
                disabled={isProcessing}
                className="btn-primary"
              >
                {isProcessing ? 'Saving to Server...' : (currentTrialIndex + 1 < TRIAL_SEQUENCE.length ? 'Save & Next Trial' : 'Save & Finish')}
              </button>
            </div>
          </div>

          <div className="interactive-windows-grid">
            {/* Target Interaction View (Left Card) */}
            <div className="interactive-card">
              <div className="interactive-card-title">Interactive Image (Remove objects that were not in original image)</div>
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
                          pointerEvents: 'none' /* Prevents the box from blocking the image click */
                        }}
                      />
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Inpainted Result View (Right Card) */}
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

      {/* 5. Completed Phase */}
      {phase === PHASES.COMPLETED && (
        <div className="centered-view">
          <h2>Experiment Complete</h2>
          <p style={{ marginTop: '12px', color: '#9ca3af' }}>
            All session data has been successfully saved to the server.
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
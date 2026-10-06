import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = "http://localhost:8000";
const PHASES = {
  ID_ENTRY: -4,
  TARGET_PROMPT: -3,
  BLANK_SCREEN: -2,
  FIXATION: -1,
  OBSERVATION: 0,
  TRANSITION: 1,
  INTERACTIVE: 2,
  COMPLETED: 3
};

const TRIAL_SEQUENCE = [
  "Trial_1_Living_Room",
];

const TARGET_SEQUENCE = [
  "Pan",
];

function App() {
  const [currentTrialIndex, setCurrentTrialIndex] = useState(0);
  const activeFolder = TRIAL_SEQUENCE[currentTrialIndex] || TRIAL_SEQUENCE[0];
  const activeTarget = TARGET_SEQUENCE[currentTrialIndex] || TARGET_SEQUENCE[0];

  // EXPERIMENTAL DESIGN: Strict unified naming convention
  const observationImage = `/Prerendered_Scenes/${activeFolder}/obs.jpg`;
  const interactiveBaseImage = `/Prerendered_Scenes/${activeFolder}/int.jpg`;

  const [participantId, setParticipantId] = useState("");
  const [phase, setPhase] = useState(PHASES.ID_ENTRY);
  const [isProcessing, setIsProcessing] = useState(false);

  const [displayImage, setDisplayImage] = useState(observationImage);
  const workingImageRef = useRef(null);
  
  const canvasRef = useRef(null);
  const telemetryRef = useRef([]);
  const renderFrameRef = useRef();
  const currentMouseRef = useRef({ x: 0, y: 0 });

  const pyramidRefs = useRef([]); 
  const saliconLUTRef = useRef(null);

  const [removedObjects, setRemovedObjects] = useState([]);
  const [removedLabels, setRemovedLabels] = useState([]);
  const [boundingboxes, setBoundingBoxes] = useState([]);
  const [naturalDims, setNaturalDims] = useState(null);

  useEffect(() => {
    setDisplayImage(observationImage);
    setRemovedObjects([]);
    setRemovedLabels([]);
    setPhase(currentTrialIndex === 0 ? PHASES.ID_ENTRY : PHASES.TARGET_PROMPT); 
    telemetryRef.current = []; 
    currentMouseRef.current = { x: 0, y: 0 }; 

    const ref = new Image();
    ref.crossOrigin = "anonymous";
    ref.onload = () => {
      setNaturalDims({ width: ref.naturalWidth, height: ref.naturalHeight });
      workingImageRef.current = ref;
      
      const TARGET_W = ref.naturalWidth;
      const TARGET_H = ref.naturalHeight;

      const c0 = document.createElement('canvas');
      c0.width = TARGET_W;
      c0.height = TARGET_H;
      const ctx0 = c0.getContext('2d');
      ctx0.drawImage(ref, 0, 0, TARGET_W, TARGET_H);
      
      const levels = [c0];
      for (let i = 1; i < 6; i++) {
        const prev = levels[i - 1];
        const c = document.createElement('canvas');
        c.width = Math.max(1, Math.floor(prev.width / 2));
        c.height = Math.max(1, Math.floor(prev.height / 2));
        const cCtx = c.getContext('2d');
        cCtx.imageSmoothingEnabled = true;
        cCtx.imageSmoothingQuality = 'high';
        cCtx.drawImage(prev, 0, 0, c.width, c.height);
        levels.push(c);
      }

      const tempPyramid = [];
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = TARGET_W;
      tempCanvas.height = TARGET_H;
      const tempCtx = tempCanvas.getContext('2d', { willReadFrequently: true });
      
      for (let i = 0; i < 6; i++) {
        tempCtx.clearRect(0, 0, TARGET_W, TARGET_H);
        tempCtx.imageSmoothingEnabled = true;
        tempCtx.imageSmoothingQuality = 'high';
        
        if (i > 0) {
          tempCtx.filter = `blur(${Math.pow(2, i - 1)}px)`;
        } else {
          tempCtx.filter = 'none';
        }
        
        tempCtx.drawImage(levels[i], 0, 0, levels[i].width, levels[i].height, 0, 0, TARGET_W, TARGET_H);
        
        const imgData = tempCtx.getImageData(0, 0, TARGET_W, TARGET_H);
        tempPyramid.push(new Uint32Array(imgData.data.buffer));
      }
      
      const totalPixels = TARGET_W * TARGET_H;
      const interleaved = new Uint32Array(totalPixels * 6);
      for (let i = 0; i < totalPixels; i++) {
        interleaved[i * 6 + 0] = tempPyramid[0][i];
        interleaved[i * 6 + 1] = tempPyramid[1][i];
        interleaved[i * 6 + 2] = tempPyramid[2][i];
        interleaved[i * 6 + 3] = tempPyramid[3][i];
        interleaved[i * 6 + 4] = tempPyramid[4][i];
        interleaved[i * 6 + 5] = tempPyramid[5][i];
      }
      pyramidRefs.current = interleaved;

      const p = 29.719 * (TARGET_W / 1920); 
      const alpha = 2.5; 
      const maxDistSq = (TARGET_W * TARGET_W) + (TARGET_H * TARGET_H);
      const lut = new Float32Array(maxDistSq * 2);
      
      const fovealRadius = p * 2.0; 

      for (let dSq = 0; dSq < maxDistSq; dSq++) {
        const d = Math.sqrt(dSq); 
        
        let theta = 0;
        if (d > fovealRadius) {
          theta = (d - fovealRadius) / p;
        }
        
        const R = alpha / (alpha + theta); 

        let L = (1.0 - R) * 5.0;
        L = Math.max(0, Math.min(5, L));

        const layerA = Math.floor(L);
        lut[dSq * 2] = layerA;            
        lut[dSq * 2 + 1] = L - layerA;    
      }
      
      saliconLUTRef.current = lut;
    };
    ref.src = observationImage; 
  }, [currentTrialIndex, observationImage]);

  useEffect(() => {
    if (currentTrialIndex >= TRIAL_SEQUENCE.length) return;
    fetch(`/Prerendered_Scenes/${activeFolder}/bounding_boxes.json`)
      .then(response => response.json())
      .then(data => setBoundingBoxes(data))
      .catch(error => console.error(`Failed to load bounding boxes for ${activeFolder}:`, error));
  }, [activeFolder, currentTrialIndex]);

  useEffect(() => {
    let timerId;
    if (phase === PHASES.BLANK_SCREEN) {
      timerId = setTimeout(() => setPhase(PHASES.FIXATION), 500);
    } else if (phase === PHASES.FIXATION) {
      timerId = setTimeout(() => setPhase(PHASES.OBSERVATION), 500);
    }
    return () => clearTimeout(timerId);
  }, [phase]);

  useEffect(() => {
    if (phase === PHASES.OBSERVATION && naturalDims && workingImageRef.current && pyramidRefs.current.length > 0) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      
      canvas.width = naturalDims.width;
      canvas.height = naturalDims.height;
      const ctx = canvas.getContext('2d', { alpha: false }); 

      const p = 29.719 * (canvas.width / 1920); 
      const w = canvas.width;
      const h = canvas.height;
      const maxDistSq = (w * w) + (h * h);

      const outData = new Uint8ClampedArray(w * h * 4);
      const out32 = new Uint32Array(outData.buffer);
      const dxSqArray = new Uint32Array(w); 

      const handleMouseMove = (e) => {
        const rect = canvas.getBoundingClientRect();
        
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const mx = Math.round((e.clientX - rect.left) * scaleX);
        const my = Math.round((e.clientY - rect.top) * scaleY);

        currentMouseRef.current = { x: mx, y: my };

        if (renderFrameRef.current) cancelAnimationFrame(renderFrameRef.current);
        
        renderFrameRef.current = requestAnimationFrame(() => {
          const lut = saliconLUTRef.current;
          const pyra = pyramidRefs.current;

          for (let px = 0; px < w; px++) {
            const dx = px - mx;
            dxSqArray[px] = dx * dx;
          }

          let i = 0;
          for (let py = 0; py < h; py++) {
            const dy = py - my;
            const dySq = dy * dy; 
            
            for (let px = 0; px < w; px++) {
              let distSq = dxSqArray[px] + dySq;
              if (distSq >= maxDistSq) distSq = maxDistSq - 1;

              const lutIdx = distSq << 1; 
              const layerA = lut[lutIdx];
              const weightB = lut[lutIdx + 1];
              const weightA = 1.0 - weightB;

              const layerB = layerA < 5 ? layerA + 1 : 5;

              const offset = i * 6;
              const colorA = pyra[offset + layerA];
              const colorB = pyra[offset + layerB];

              const r = (colorA & 0xff) * weightA + (colorB & 0xff) * weightB;
              const g = ((colorA >> 8) & 0xff) * weightA + ((colorB >> 8) & 0xff) * weightB;
              const b = ((colorA >> 16) & 0xff) * weightA + ((colorB >> 16) & 0xff) * weightB;

              out32[i] = (0xff000000) | (b << 16) | (g << 8) | r;
              i++;
            }
          }

          ctx.putImageData(new ImageData(outData, w, h), 0, 0);

          ctx.strokeStyle = 'rgba(255, 0, 0, 0.65)';
          ctx.lineWidth = 2 * scaleX; 
          ctx.beginPath();
          ctx.arc(mx, my, p * 2.0, 0, 2 * Math.PI); 
          ctx.stroke();
        });
      };

      const handleMouseDown = (e) => {
        if (e.button === 0) { 
          setPhase(PHASES.TRANSITION);
          setTimeout(() => setPhase(PHASES.INTERACTIVE), 500);
        }
      };

      canvas.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mousedown', handleMouseDown);
      
      const telemetryIntervalId = setInterval(() => {
        const { x, y } = currentMouseRef.current;
        if (x !== 0 || y !== 0) {
          telemetryRef.current.push({ t: performance.now(), x: Math.round(x), y: Math.round(y) });
        }
      }, 300);

      handleMouseMove({ clientX: -999, clientY: -999 });

      return () => {
        canvas.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mousedown', handleMouseDown); 
        clearInterval(telemetryIntervalId);
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
    
    // Updated default fall-back image to int.jpg
    const filename = sortedLabels.length === 0 
      ? "int.jpg" 
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
        participant_id: participantId,
        target_object: activeTarget,
        removed_objects: removedObjects,
        removed_labels: removedLabels,
        base_scene_name: activeFolder,
        final_image_path: displayImage,
        mouse_telemetry: formattedTelemetry 
      }, {
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
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
      {phase === PHASES.ID_ENTRY && (
        <div className="centered-view" style={{ textAlign: 'center', fontFamily: 'sans-serif', color: 'white' }}>
          <h2 style={{ fontSize: '36px', marginBottom: '40px' }}>Trial Setup</h2>
          <div style={{ marginBottom: '30px' }}>
            <label style={{ fontSize: '20px', fontWeight: 'bold', marginRight: '15px' }}>
              Participant ID:
            </label>
            <input 
              type="text" 
              value={participantId} 
              onChange={(e) => setParticipantId(e.target.value)} 
              placeholder="Enter ID..."
              style={{ padding: '12px 18px', fontSize: '20px', borderRadius: '6px', border: 'none', outline: 'none', color: 'black' }}
            />
          </div>
          <button 
            onClick={() => {
              if (!participantId.trim()) { alert("Please enter a Participant ID to continue."); return; }
              setPhase(PHASES.TARGET_PROMPT);
            }}
            style={{ padding: '12px 30px', fontSize: '20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', marginTop: '20px' }}
          >
            Next
          </button>
        </div>
      )}

      {phase === PHASES.TARGET_PROMPT && (
        <div className="centered-view" style={{ textAlign: 'center', fontFamily: 'sans-serif' }}>
          <div style={{ margin: '0 auto 40px auto', fontSize: '28px', backgroundColor: '#f3f4f6', padding: '40px 60px', borderRadius: '12px', color: '#374151', display: 'inline-block' }}>
            Your target to find is: <br />
            <strong style={{ fontSize: '64px', color: '#3b82f6', display: 'block', marginTop: '20px' }}>{activeTarget}</strong>
          </div>
          <br/>
          <button 
            onClick={() => setPhase(PHASES.BLANK_SCREEN)}
            style={{ padding: '15px 40px', fontSize: '22px', backgroundColor: '#22c55e', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}
          >
            Start Trial
          </button>
        </div>
      )}

      {phase === PHASES.BLANK_SCREEN && <div className="fixation-screen" />}
      {phase === PHASES.FIXATION && <div className="fixation-screen"><div className="fixation-cross" /></div>}

      {phase === PHASES.OBSERVATION && (
        <div className="observable-screen" style={{ overflow: 'hidden', width: '100vw', height: '100vh', backgroundColor: 'black' }}>
          <canvas
            ref={canvasRef}
            className="observable-image"
            style={{ 
              width: '100%', 
              height: '100%', 
              pointerEvents: 'auto', 
              cursor: 'none',
              objectFit: 'cover'
            }}
          />
        </div>
      )}

      {phase === PHASES.TRANSITION && <div className="centered-view"><h2>Transitioning to Interactive Mode...</h2></div>}

      {phase === PHASES.INTERACTIVE && (
        <div className="interactive-layout">
          <div className="interactive-toolbar">
            <h2>Target: {activeTarget}</h2>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button onClick={handleReviewAndSave} disabled={isProcessing} className="btn-primary">
                {isProcessing ? 'Saving to Server...' : (currentTrialIndex + 1 < TRIAL_SEQUENCE.length ? 'Save & Next Trial' : 'Save & Finish')}
              </button>
            </div>
          </div>

          <div className="interactive-windows-grid">
            <div className="interactive-card">
              <div className="interactive-card-title">Interactive Image (Identify the newly added object)</div>
              <div className="interactive-viewport-wrapper">
                <div style={{ position: 'relative', display: 'inline-block', lineHeight: 0, maxHeight: '100%', maxWidth: '100%' }}>
                  <img
                    id="interactive-scene-img"
                    src={interactiveBaseImage}
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
                          position: 'absolute', left: `${leftPercent}%`, top: `${topPercent}%`, width: `${widthPercent}%`, height: `${heightPercent}%`,
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

            <div className="interactive-card">
              <div className="interactive-card-title">Current Render</div>
              <div className="interactive-viewport-wrapper">
                <img src={displayImage} alt="Inpainted State" className="interactive-viewport-img" />
              </div>
            </div>
          </div>
        </div>
      )}

      {phase === PHASES.COMPLETED && (
        <div className="centered-view">
          <h2>Experiment Complete</h2>
          <p style={{ marginTop: '12px', color: '#9ca3af' }}>All session data has been successfully saved to the server.</p>
        </div>
      )}
    </div>
  );
}

export default App;
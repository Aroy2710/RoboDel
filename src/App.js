import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = "https://multitude-resupply-apply.ngrok-free.dev ";
const GOOGLE_FORM_URL = "https://forms.google.com";

const PHASES = {
  ID_ENTRY: -4,
  TARGET_PROMPT: -3,
  BLANK_SCREEN: -2,
  FIXATION: -1,
  OBSERVATION: 0,
  TRANSITION: 1,
  INTERACTIVE: 2,
  SURVEY: 3,
  COMPLETED: 4
};

const TRIAL_SEQUENCE = [
  "Trial_01_LivingRoom_FP205",
  "Trial_02_BathRoom_FP403",
  "Trial_03_Kitchen_FP5",
  "Trial_04_Kitchen_FP6",
  "Trial_05_Bedroom_FP304",
  "Trial_06_Bathroom_FP401",
  "Trial_07_LivingRoom_FP204",
  "Trial_08_Bedroom_FP301",
  "Trial_09_Bathroom_FP404",
  "Trial_10_Bathroom_FP402",
  "Trial_11_Kitchen_FP7",
  "Trial_12_LivingRoom_FP201",
  "Trial_13_Bedroom_FP303",
  "Trial_14_LivingRoom_FP203",
  "Trial_15_Kitchen_FP8",
  "Trial_16_Bedroom_FP302"
];

const TARGET_SEQUENCE = [
  "Laptop",
  "SoapBar",
  "Kettle",
  "Apple",
  "Chair",
  "DishSponge",
  "Painting",
  "Book",
  "ToiletPaper",
  "GarbageCan",
  "Bread",
  "Newspaper",
  "Dumbbell",
  "Box",
  "HousePlant",
  "AlarmClock"
];

function App() {
  const [currentTrialIndex, setCurrentTrialIndex] = useState(0);
  const activeFolder = TRIAL_SEQUENCE[currentTrialIndex] || TRIAL_SEQUENCE[0];
  const activeTarget = TARGET_SEQUENCE[currentTrialIndex] || TARGET_SEQUENCE[0];

  const observationImage = `/Prerendered_Scenes/${activeFolder}/obs.jpg`;
  const interactiveBaseImage = `/Prerendered_Scenes/${activeFolder}/int.jpg`;

  const [participantId, setParticipantId] = useState("");
  const [phase, setPhase] = useState(PHASES.ID_ENTRY);
  const [isProcessing, setIsProcessing] = useState(false);

  // Both viewports initialize to int.jpg
  const [displayImage, setDisplayImage] = useState(interactiveBaseImage);
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

  const experimentStartTimeRef = useRef(null);
  const trialStartTimeRef = useRef(null);

  // Survey state matching the 5 questions
  const [surveyData, setSurveyData] = useState({
    ease_of_use_score: 8,
    mouse_control_comfort: "Smooth and instant",
    visual_fatigue: "None / Felt completely fine",
    ux_improvement_suggestions: "",
    experienced_glitches: "No"
  });
  const [surveySubmitted, setSurveySubmitted] = useState(false);

  const handleStartExperiment = () => {
    if (!participantId.trim()) {
      alert("Please enter a Participant ID to continue.");
      return;
    }
    experimentStartTimeRef.current = performance.now();
    trialStartTimeRef.current = performance.now();
    setPhase(PHASES.TARGET_PROMPT);
  };

  useEffect(() => {
    setDisplayImage(interactiveBaseImage);
    setRemovedObjects([]);
    setRemovedLabels([]);
    telemetryRef.current = []; 
    currentMouseRef.current = { x: 0, y: 0 }; 

    if (phase !== PHASES.ID_ENTRY && phase !== PHASES.SURVEY && phase !== PHASES.COMPLETED) {
      trialStartTimeRef.current = performance.now();
    }

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
  }, [currentTrialIndex, observationImage, interactiveBaseImage]);

  useEffect(() => {
    if (currentTrialIndex >= TRIAL_SEQUENCE.length) return;
    fetch(`/Prerendered_Scenes/${activeFolder}/bounding_boxes.json`)
      .then(response => response.json())
      .then(data => {
        const resetData = data.map(box => ({ ...box, isClicked: false }));
        setBoundingBoxes(resetData);
      })
      .catch(error => console.error(`Failed to load bounding boxes:`, error));
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
    const filename = sortedLabels.length === 0 
      ? "int.jpg" 
      : `removed_${sortedLabels.join('_')}.jpg`;

    setDisplayImage(`/Prerendered_Scenes/${activeFolder}/${filename}`);

    setBoundingBoxes(prev => prev.map((box, index) =>
      index === clickedBoxIndex ? { ...box, isClicked: !isCurrentlyClicked } : box
    ));
  };

  const saveCurrentSession = async (isEarlyExit = false) => {
    const rawTelemetry = telemetryRef.current;
    const trialDurationSec = (performance.now() - (trialStartTimeRef.current || performance.now())) / 1000;
    const totalDurationSec = (performance.now() - (experimentStartTimeRef.current || performance.now())) / 1000;

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
      mouse_telemetry: formattedTelemetry,
      trial_index: currentTrialIndex,
      total_trials: TRIAL_SEQUENCE.length,
      trial_duration_sec: trialDurationSec,
      total_experiment_duration_sec: totalDurationSec,
      is_early_exit: isEarlyExit
    });
  };

  const handleSaveAndContinue = async () => {
    setIsProcessing(true);
    try {
      await saveCurrentSession(false);
      if (currentTrialIndex + 1 < TRIAL_SEQUENCE.length) {
        setCurrentTrialIndex(prev => prev + 1);
        setPhase(PHASES.TARGET_PROMPT);
      } else {
        setPhase(PHASES.SURVEY);
      }
    } catch (error) {
      console.error("Error saving session:", error);
      alert("Failed to save trial to server. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSaveAndExit = async () => {
    const confirmExit = window.confirm("Save your progress on this trial and exit to the survey?");
    if (!confirmExit) return;

    setIsProcessing(true);
    try {
      await saveCurrentSession(true);
      const totalDurationSec = (performance.now() - (experimentStartTimeRef.current || performance.now())) / 1000;
      const completedCount = currentTrialIndex + 1;
      const completionRate = completedCount / TRIAL_SEQUENCE.length;

      await axios.post(`${API_URL}/record_early_exit`, {
        participant_id: participantId,
        trials_completed: completedCount,
        total_trials: TRIAL_SEQUENCE.length,
        completion_rate: completionRate,
        total_experiment_duration_sec: totalDurationSec,
        reason: "user_requested_exit"
      });
      setPhase(PHASES.SURVEY);
    } catch (e) {
      console.error("Failed to complete save and exit:", e);
      alert("Failed to record exit. Moving to survey anyway.");
      setPhase(PHASES.SURVEY);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSurveySubmit = async (e) => {
    e.preventDefault();
    setIsProcessing(true);
    try {
      await axios.post(`${API_URL}/save_survey`, {
        participant_id: participantId,
        ...surveyData
      });
      setSurveySubmitted(true);
      setTimeout(() => setPhase(PHASES.COMPLETED), 1200);
    } catch (err) {
      console.error("Error submitting survey feedback:", err);
      alert("Error saving response to server. You can still complete via the direct link.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="app-container" style={{ position: 'relative' }}>
      {/* 1. PARTICIPANT ID ENTRY */}
      {phase === PHASES.ID_ENTRY && (
        <div className="centered-view" style={{ textAlign: 'center', fontFamily: 'sans-serif', color: 'white' }}>
          <h2 style={{ fontSize: '36px', marginBottom: '35px' }}>Enter your ID</h2>
          <div style={{ marginBottom: '30px' }}>
            <label style={{ fontSize: '20px', fontWeight: 'bold', marginRight: '15px' }}>
              Participant ID:
            </label>
            <input 
              type="text" 
              value={participantId} 
              onChange={(e) => setParticipantId(e.target.value)} 
              placeholder="e.g. 1"
              style={{ padding: '12px 18px', fontSize: '20px', borderRadius: '6px', border: 'none', outline: 'none', color: 'black' }}
            />
          </div>
          <button 
            onClick={handleStartExperiment}
            style={{ padding: '12px 32px', fontSize: '18px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Start Experiment
          </button>
        </div>
      )}

      {/* 2. TARGET PROMPT */}
      {phase === PHASES.TARGET_PROMPT && (
        <div className="centered-view" style={{ textAlign: 'center', fontFamily: 'sans-serif' }}>
          <div style={{ margin: '0 auto 40px auto', fontSize: '26px', backgroundColor: '#f3f4f6', padding: '40px 60px', borderRadius: '12px', color: '#374151', display: 'inline-block' }}>
            Your target object is: <br />
            <strong style={{ fontSize: '60px', color: '#3b82f6', display: 'block', marginTop: '16px' }}>{activeTarget}</strong>
          </div>
          <br/>
          <button 
            onClick={() => setPhase(PHASES.BLANK_SCREEN)}
            style={{ padding: '14px 40px', fontSize: '20px', backgroundColor: '#22c55e', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Begin Trial
          </button>
        </div>
      )}

      {phase === PHASES.BLANK_SCREEN && <div className="fixation-screen" />}
      {phase === PHASES.FIXATION && <div className="fixation-screen"><div className="fixation-cross" /></div>}

      {/* 3. OBSERVATION (FOVEATED BLUR) - Clean screen with zero overlays */}
      {phase === PHASES.OBSERVATION && (
        <div className="observable-screen" style={{ overflow: 'hidden', width: '100vw', height: '100vh', backgroundColor: 'black' }}>
          <canvas
            ref={canvasRef}
            className="observable-image"
            style={{ width: '100%', height: '100%', pointerEvents: 'auto', cursor: 'none', objectFit: 'cover' }}
          />
        </div>
      )}

      {phase === PHASES.TRANSITION && <div className="centered-view"><h2>Transitioning to Interactive Mode...</h2></div>}

      {/* 4. INTERACTIVE VERIFICATION */}
      {phase === PHASES.INTERACTIVE && (
        <div className="interactive-layout" style={{ paddingTop: '20px' }}>
          <div className="interactive-toolbar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <span style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: '1px solid #3b82f6',
                padding: '6px 14px',
                borderRadius: '20px',
                color: '#fff',
                fontWeight: 'bold',
                fontSize: '14px'
              }}>
                Trial {currentTrialIndex + 1} of {TRIAL_SEQUENCE.length}
              </span>
              <h2 style={{ margin: 0 }}>Target: <span style={{ color: '#60a5fa' }}>{activeTarget}</span></h2>
            </div>

            <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
              <button 
                onClick={handleSaveAndContinue} 
                disabled={isProcessing} 
                className="btn-primary"
                style={{ padding: '10px 20px', fontSize: '15px' }}
              >
                {isProcessing ? 'Saving...' : (currentTrialIndex + 1 < TRIAL_SEQUENCE.length ? 'Save and Continue' : 'Save & Finish')}
              </button>
              
              <button 
                onClick={handleSaveAndExit} 
                disabled={isProcessing}
                style={{
                  background: '#dc2626',
                  color: '#fff',
                  border: 'none',
                  padding: '10px 18px',
                  borderRadius: '6px',
                  fontWeight: 'bold',
                  fontSize: '15px',
                  cursor: isProcessing ? 'wait' : 'pointer'
                }}
              >
                Save and Exit
              </button>
            </div>
          </div>

          <div className="interactive-windows-grid">
            <div className="interactive-card">
              <div className="interactive-card-title">Click to delete objects you do not recall seeing in the previous image</div>
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

            <div className="interactive-card">
              <div className="interactive-card-title">Current Render</div>
              <div className="interactive-viewport-wrapper">
                <img src={displayImage} alt="Inpainted State" className="interactive-viewport-img" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. FEEDBACK QUESTIONNAIRE */}
      {phase === PHASES.SURVEY && (
        <div style={{
          maxWidth: '750px',
          margin: '30px auto',
          background: '#1f2937',
          padding: '30px 40px',
          borderRadius: '12px',
          color: '#f3f4f6',
          fontFamily: 'sans-serif',
          textAlign: 'left',
          maxHeight: '90vh',
          overflowY: 'auto'
        }}>
          <h2 style={{ fontSize: '26px', borderBottom: '1px solid #374151', paddingBottom: '12px', marginTop: 0 }}>
            Post-Experiment Feedback Questionnaire
          </h2>
          <p style={{ color: '#9ca3af', fontSize: '14px', lineHeight: '1.5' }}>
            Participant: <b>{participantId}</b> | Completed: <b>{Math.min(currentTrialIndex + 1, TRIAL_SEQUENCE.length)} of {TRIAL_SEQUENCE.length}</b> trials.
            <br />
            Please complete this short pilot survey below
          </p>

          <form onSubmit={handleSurveySubmit} style={{ display: 'flex', flexDirection: 'column', gap: '22px', marginTop: '20px' }}>
            {/* Question 1 */}
            <div>
              <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>
                1. How easy was the application to use?
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <span style={{ fontSize: '13px', color: '#9ca3af' }}>Very Confusing (1)</span>
                <input 
                  type="range" min="1" max="10" step="1"
                  value={surveyData.ease_of_use_score}
                  onChange={(e) => setSurveyData({ ...surveyData, ease_of_use_score: parseInt(e.target.value) })}
                  style={{ flex: 1 }}
                />
                <span style={{ fontSize: '13px', color: '#9ca3af' }}>Very Easy (10)</span>
                <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#38bdf8', minWidth: '24px', textAlign: 'center' }}>
                  {surveyData.ease_of_use_score}
                </span>
              </div>
            </div>

            {/* Question 2 */}
            <div>
              <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>
                2. How well did the clear focus circle keep up with your mouse?
              </label>
              <select 
                value={surveyData.mouse_control_comfort}
                onChange={(e) => setSurveyData({ ...surveyData, mouse_control_comfort: e.target.value })}
                style={{ width: '100%', padding: '10px', borderRadius: '6px', background: '#111827', color: '#fff', border: '1px solid #4b5563' }}
              >
                <option value="Smooth and instant">Smooth and instant</option>
                <option value="Good / comfortable">Good / comfortable</option>
                <option value="A little delayed or sluggish">A little delayed or sluggish</option>
                <option value="Noticeably laggy or stuttery">Noticeably laggy or stuttery</option>
              </select>
            </div>

            {/* Question 3 */}
            <div>
              <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>
                3. Did searching with the blur effect cause any eye tiredness or discomfort?
              </label>
              <select 
                value={surveyData.visual_fatigue}
                onChange={(e) => setSurveyData({ ...surveyData, visual_fatigue: e.target.value })}
                style={{ width: '100%', padding: '10px', borderRadius: '6px', background: '#111827', color: '#fff', border: '1px solid #4b5563' }}
              >
                <option value="None / Felt completely fine">None / Felt completely fine</option>
                <option value="Mild tiredness">Mild tiredness</option>
                <option value="Moderate eye strain">Moderate eye strain</option>
                <option value="Uncomfortable / wanted to stop">Uncomfortable / wanted to stop</option>
              </select>
            </div>

            {/* Question 4 */}
            <div>
              <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>
                4. What could we improve to make this easier or more comfortable to use?
              </label>
              <textarea 
                rows="3"
                value={surveyData.ux_improvement_suggestions}
                onChange={(e) => setSurveyData({ ...surveyData, ux_improvement_suggestions: e.target.value })}
                placeholder="Any suggestions on instructions, buttons, or screen layout?"
                style={{ width: '100%', padding: '10px', borderRadius: '6px', background: '#111827', color: '#fff', border: '1px solid #4b5563' }}
              />
            </div>

            {/* Question 5 */}
            <div>
              <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                5. Did anything seem broken or glitched during your session?
              </label>
              <span style={{ fontSize: '13px', color: '#9ca3af', display: 'block', marginBottom: '8px' }}>
                (For example: green selection boxes appearing in the wrong spot, clicks not registering, or the image failing to update.)
              </span>
              <input 
                type="text"
                value={surveyData.experienced_glitches}
                onChange={(e) => setSurveyData({ ...surveyData, experienced_glitches: e.target.value })}
                placeholder="Describe any issues, or leave as 'No'"
                style={{ width: '100%', padding: '10px', borderRadius: '6px', background: '#111827', color: '#fff', border: '1px solid #4b5563' }}
              />
            </div>

            <button
              type="submit"
              disabled={isProcessing || surveySubmitted}
              style={{
                marginTop: '10px',
                padding: '12px 24px',
                backgroundColor: '#22c55e',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 'bold',
                fontSize: '16px',
                cursor: 'pointer'
              }}
            >
              {surveySubmitted ? 'Submitted!' : (isProcessing ? 'Submitting...' : 'Submit Feedback & Finish')}
            </button>
          </form>
        </div>
      )}

      {/* 6. COMPLETED SCREEN */}
      {phase === PHASES.COMPLETED && (
        <div className="centered-view" style={{ textAlign: 'center', color: '#fff' }}>
          <h2>Session Complete</h2>
          <p style={{ marginTop: '12px', color: '#9ca3af' }}>
            Thank you for participating! All trial telemetry and feedback have been safely recorded.
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
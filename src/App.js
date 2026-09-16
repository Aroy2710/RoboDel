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
const OBSERVATION_DURATION_SECONDS = 10;

// Sequence of trial directories
const TRIAL_SEQUENCE = [
  "Trial_1_FP1_Island",
  "Trial_2_FP2_Table"
];

const BASE_SCENE_NAME = "robothor_scene_01";

function App() {
  const [currentTrialIndex, setCurrentTrialIndex] = useState(0);
  const activeFolder = TRIAL_SEQUENCE[currentTrialIndex] || TRIAL_SEQUENCE[0];

  // Dynamic paths based on active trial folder
  const modifiedImage = `/Prerendered_Scenes/${activeFolder}/base.png`;
  const originalImage = modifiedImage;

  const [phase, setPhase] = useState(PHASES.FIXATION);
  const [fixationTimeLeft, setFixationTimeLeft] = useState(FIXATION_DURATION_SECONDS);
  const [timeLeft, setTimeLeft] = useState(OBSERVATION_DURATION_SECONDS);
  const [isProcessing, setIsProcessing] = useState(false);

  const [displayImage, setDisplayImage] = useState(modifiedImage);
  const workingImageRef = useRef(null);

  const [imageHistory, setImageHistory] = useState([]);
  const [removedObjects, setRemovedObjects] = useState([]);
  const [removedLabels, setRemovedLabels] = useState([]);
  const [boundingboxes, setBoundingBoxes] = useState([]);
  const [naturalDims, setNaturalDims] = useState(null);

  // Initialize display and image natural dimensions when trial advances
  useEffect(() => {
    setDisplayImage(modifiedImage);
    setRemovedObjects([]);
    setImageHistory([]);
    setRemovedLabels([]);
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

  // Undo functionality
  const handleUndo = () => {
    if (imageHistory.length > 0) {
      const previous = imageHistory[imageHistory.length - 1];

      setDisplayImage(previous.display);
      setRemovedLabels(previous.labelsState);

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
      !box.isClicked &&
      x >= box.x && x <= box.x + box.width &&
      y >= box.y && y <= box.y + box.height
    );

    if (clickedBoxIndex === -1) return;

    const targetBox = boundingboxes[clickedBoxIndex];
    const clickedLabel = targetBox.label.toLowerCase();

    const newRemovedLabels = [...removedLabels, clickedLabel];
    setRemovedLabels(newRemovedLabels);

    const sortedLabels = [...newRemovedLabels].sort();
    const filename = `removed_${sortedLabels.join('_')}.png`;

    const newImageSrc = `/Prerendered_Scenes/${activeFolder}/${filename}`;

    setImageHistory(prev => [
      ...prev,
      {
        display: displayImage,
        labelsState: [...removedLabels],
        boxIndex: clickedBoxIndex
      }
    ]);

    setDisplayImage(newImageSrc);

    setBoundingBoxes(prev => prev.map((box, index) =>
      index === clickedBoxIndex ? { ...box, isClicked: true } : box
    ));

    setRemovedObjects(prev => [...prev, {
      object_id: targetBox.id,
      label: targetBox.label,
      bounding_box: { x: targetBox.x, y: targetBox.y, width: targetBox.width, height: targetBox.height },
      click_position: { x, y }
    }]);
  };

  // Save session & advance sequence
  const handleReviewAndSave = async () => {
    setIsProcessing(true);
    try {
      await axios.post(`${API_URL}/save_session`, {
        removed_objects: removedObjects,
        removed_labels: removedLabels,
        base_scene_name: activeFolder,
        final_image_path: displayImage
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
          <img
            src={originalImage}
            alt="Observation View"
            className="observable-image"
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
                          pointerEvents: 'none'
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
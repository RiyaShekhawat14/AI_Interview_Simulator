import { useEffect, useEffectEvent, useRef, useState } from "react";

import { detectEmotion } from "../services/api.js";

function WebcamCapture({ setImageBlob, onEmotionDetected }) {
  const videoRef = useRef();
  const canvasRef = useRef();
  const intervalRef = useRef();
  const [isActive, setIsActive] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState("Unknown");

  const captureAndAnalyze = useEffectEvent(async () => {
    if (!videoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const context = canvas.getContext("2d");
    context.drawImage(videoRef.current, 0, 0, 224, 224);

    canvas.toBlob(async (blob) => {
      if (!blob) return;

      setImageBlob(blob);
      try {
        const emotionData = await detectEmotion(blob);
        const emotion = emotionData.emotion;
        setCurrentEmotion(emotion);
        if (onEmotionDetected) {
          onEmotionDetected(emotion);
        }
      } catch (err) {
        console.warn("Emotion detection failed:", err);
      }
    });
  });

  useEffect(() => {
    let stream;

    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setIsActive(true);
        }
      } catch (err) {
        console.error("Camera access failed:", err);
      }
    };

    startCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (isActive && onEmotionDetected) {
      intervalRef.current = setInterval(() => {
        captureAndAnalyze();
      }, 2000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isActive, onEmotionDetected]);

  return (
    <div className="video-card">
      <video ref={videoRef} autoPlay muted playsInline />
      <canvas ref={canvasRef} width="224" height="224" style={{ display: "none" }} />
      <div className="emotion-display">
        <span className="emotion-label">Current Emotion: {currentEmotion}</span>
      </div>
      <p className="footer-note">
        Camera is active. Emotion detection is running automatically.
      </p>
    </div>
  );
}

export default WebcamCapture;

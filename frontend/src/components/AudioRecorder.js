import React, { useState, useRef } from "react";

function AudioRecorder({ setAudioBlob }) {
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  // 🎤 Start Recording
  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;

    mediaRecorder.ondataavailable = (event) => {
      chunksRef.current.push(event.data);
    };

    mediaRecorder.start();
    setRecording(true);
  };

  // 🛑 Stop Recording
  const stopRecording = () => {
    mediaRecorderRef.current.stop();
    setRecording(false);

    mediaRecorderRef.current.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/wav" });
      setAudioBlob(blob);
      chunksRef.current = [];
    };
  };

  return (
    <div style={{ marginTop: "20px" }}>
      <h3>🎤 Voice Answer</h3>

      {!recording ? (
        <button onClick={startRecording}>Start Recording</button>
      ) : (
        <button onClick={stopRecording}>Stop Recording</button>
      )}
    </div>
  );
}

export default AudioRecorder;
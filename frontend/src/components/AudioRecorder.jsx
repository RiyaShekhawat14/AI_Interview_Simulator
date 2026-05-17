import { useEffect, useRef, useState } from "react";

function AudioRecorder({ setAudioBlob, onRecordingComplete }) {
  const [status, setStatus] = useState("idle");
  const [audioUrl, setAudioUrl] = useState("");
  const [isListening, setIsListening] = useState(false);

  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const microphoneRef = useRef(null);
  const processorRef = useRef(null);
  const pcmChunksRef = useRef([]);
  const sampleRateRef = useRef(16000);
  const streamRef = useRef(null);
  const silenceTimeoutRef = useRef(null);
  const statusRef = useRef("idle");

  function setRecorderStatus(nextStatus) {
    statusRef.current = nextStatus;
    setStatus(nextStatus);
  }

  function encodeWav(chunks, sampleRate) {
    const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const pcmData = new Int16Array(totalLength);
    let offset = 0;

    chunks.forEach((chunk) => {
      for (let index = 0; index < chunk.length; index += 1) {
        const sample = Math.max(-1, Math.min(1, chunk[index]));
        pcmData[offset] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
        offset += 1;
      }
    });

    const buffer = new ArrayBuffer(44 + pcmData.length * 2);
    const view = new DataView(buffer);
    const writeString = (position, value) => {
      for (let index = 0; index < value.length; index += 1) {
        view.setUint8(position + index, value.charCodeAt(index));
      }
    };

    writeString(0, "RIFF");
    view.setUint32(4, 36 + pcmData.length * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, pcmData.length * 2, true);

    for (let index = 0; index < pcmData.length; index += 1) {
      view.setInt16(44 + index * 2, pcmData[index], true);
    }

    return new Blob([buffer], { type: "audio/wav" });
  }

  function stopListening() {
    setIsListening(false);

    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }

    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current.onaudioprocess = null;
      processorRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close();
    }

    if (microphoneRef.current) {
      microphoneRef.current.disconnect();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }

  useEffect(() => {
    return () => {
      stopListening();
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  function stopRecording() {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current.onaudioprocess = null;
      processorRef.current = null;
    }

    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }

    setRecorderStatus("processing");

    const blob = encodeWav(pcmChunksRef.current, sampleRateRef.current);
    if (typeof setAudioBlob === "function") {
      setAudioBlob(blob);
    }

    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    const url = URL.createObjectURL(blob);
    setAudioUrl(url);
    setRecorderStatus("saved");

    if (onRecordingComplete) {
      onRecordingComplete(blob);
    }

    window.setTimeout(() => {
      setRecorderStatus("idle");
    }, 300);
  }

  function monitorAudio() {
    if (!analyserRef.current) return;

    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const checkAudio = () => {
      if (!analyserRef.current) return;

      analyserRef.current.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < bufferLength; i += 1) {
        sum += dataArray[i];
      }
      const average = sum / bufferLength;
      const threshold = 15;

      if (average > threshold) {
        if (statusRef.current === "idle") {
          startRecording();
        }
        if (silenceTimeoutRef.current) {
          clearTimeout(silenceTimeoutRef.current);
          silenceTimeoutRef.current = null;
        }
      } else if (statusRef.current === "recording" && !silenceTimeoutRef.current) {
        silenceTimeoutRef.current = setTimeout(() => {
          stopRecording();
        }, 2000);
      }

      if (isListening) {
        requestAnimationFrame(checkAudio);
      }
    };

    checkAudio();
  }

  async function startListening() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      microphoneRef.current = audioContextRef.current.createMediaStreamSource(stream);
      sampleRateRef.current = audioContextRef.current.sampleRate || 16000;
      analyserRef.current.fftSize = 256;
      analyserRef.current.smoothingTimeConstant = 0.3;
      microphoneRef.current.connect(analyserRef.current);
      setIsListening(true);
      monitorAudio();
    } catch (err) {
      console.error("Microphone access failed:", err);
      setRecorderStatus("error");
    }
  }

  async function startRecording() {
    try {
      if (!streamRef.current || !audioContextRef.current || !microphoneRef.current) {
        setRecorderStatus("error");
        return;
      }

      pcmChunksRef.current = [];
      const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        const input = event.inputBuffer.getChannelData(0);
        pcmChunksRef.current.push(new Float32Array(input));
      };

      microphoneRef.current.connect(processor);
      processor.connect(audioContextRef.current.destination);
      processorRef.current = processor;
      setRecorderStatus("recording");
    } catch (err) {
      console.error("Recording failed:", err);
      setRecorderStatus("error");
    }
  }

  function clearRecording() {
    if (typeof setAudioBlob === "function") {
      setAudioBlob(null);
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl("");
    }
    setRecorderStatus("idle");
  }

  return (
    <div className="audio-recorder">
      <div className="recorder-status">
        Status: {status} {isListening && "(Listening for speech)"}
      </div>
      <div className="button-group">
        {!isListening ? (
          <button className="button-primary" type="button" onClick={startListening}>
            Start Voice Detection
          </button>
        ) : (
          <button className="button-secondary" type="button" onClick={stopListening}>
            Stop Listening
          </button>
        )}
        <button
          className="button-secondary"
          type="button"
          onClick={clearRecording}
          disabled={status === "idle" && !audioUrl}
        >
          Clear
        </button>
      </div>
      {status === "recording" ? (
        <div className="recording-indicator">Recording... Speak now</div>
      ) : null}
      {audioUrl ? <audio controls src={audioUrl} className="audio-preview" /> : null}
      <p className="footer-note">
        Voice detection is active. Recording starts automatically when you speak and stops when you pause.
      </p>
    </div>
  );
}

export default AudioRecorder;

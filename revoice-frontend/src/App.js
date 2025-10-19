import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./App.css";

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [mediaStream, setMediaStream] = useState(null);
  const [showRecordingOptions, setShowRecordingOptions] = useState(false);
  const [recordingType, setRecordingType] = useState(null); // 'audio' or 'video'

  const mediaRecorderRef = useRef(null);
  const timerRef = useRef(null);
  const videoRef = useRef(null);
  const navigate = useNavigate();

  // 🎬 START RECORDING
  const startRecording = async (withVideo = false) => {
    try {
      console.log("Starting recording with video:", withVideo);

      const stream = await navigator.mediaDevices.getUserMedia({
        video: withVideo ? { width: 1280, height: 720 } : false,
        audio: true,
      });

      setMediaStream(stream);
      setShowRecordingOptions(false);
      setRecordingType(withVideo ? "video" : "audio");
      setIsRecording(true);
      setRecordingTime(0);

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      const chunks = [];
      mediaRecorder.ondataavailable = (event) => chunks.push(event.data);

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, {
          type: withVideo ? "video/webm" : "audio/webm",
        });
        setAudioBlob(blob);
        stream.getTracks().forEach((t) => t.stop());
        setMediaStream(null);
      };

      mediaRecorder.start();
    } catch (error) {
      console.error("Error accessing media devices:", error);
      alert(`Could not access camera/microphone: ${error.message}`);
    }
  };

  // 🛑 STOP RECORDING
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setTimeout(() => setRecordingType(null), 200);
    }
  };

  // 📤 HANDLE FILE UPLOAD
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAudioBlob(file);
      console.log("File uploaded:", file.name);
    }
  };

  // 🕓 FORMAT TIMER
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, "0");
    const secs = (seconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  // ☁️ SEND TO BACKEND
  const sendToBackend = async () => {
    if (!audioBlob) return alert("Please record or upload audio first!");
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");

    try {
      console.log("Sending to backend...");
      alert("Ready to send to voice cloning backend!");
    } catch (err) {
      console.error("Error sending audio:", err);
    }
  };

  // ▶️ START/STOP BUTTON LOGIC
  const handleRecordClick = () => {
    if (isRecording) stopRecording();
    else setShowRecordingOptions(true);
  };

  // 🎥 SETUP VIDEO PREVIEW
  useEffect(() => {
    if (recordingType === "video" && mediaStream && videoRef.current) {
      videoRef.current.srcObject = mediaStream;
      videoRef.current.onloadedmetadata = () => {
        videoRef.current.play().catch((e) => console.error("Video play error:", e));
      };
    }
  }, [recordingType, mediaStream]);

  // ⏱ TIMER
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording]);

  // 🧹 CLEANUP
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
    };
  }, [mediaStream]);

  return (
    <div className="App">
      <header className="header">
        <div className="logo-container">
          <div className="waveform">
            <div className="wave"></div>
            <div className="wave"></div>
            <div className="wave"></div>
            <div className="wave"></div>
            <div className="wave"></div>
          </div>
          <h1 className="logo">ReVoice</h1>
        </div>
        <p className="tagline">REAL-TIME FLUENCY, POWERED BY YOUR OWN VOICE.</p>
      </header>

      <main className="main-content">
        <div className="recording-container">
          <div className="status-bar">
            <div className="timer">{formatTime(recordingTime)}</div>
          </div>

          <div className={`recording-area ${isRecording ? "recording-active" : ""}`}>
            {isRecording && recordingType === "video" ? (
              <video ref={videoRef} autoPlay playsInline muted className="video-preview" />
            ) : (
              <div className={`rec-indicator ${isRecording ? "active" : ""}`}>
                <span className="rec-dot"></span>
                REC
              </div>
            )}
          </div>

          <div className="button-container">
            {!showRecordingOptions ? (
              <>
                {!isRecording ? (
                  <button className="primary-button" onClick={handleRecordClick}>
                    Start Recording
                  </button>
                ) : (
                  <button className="primary-button stop" onClick={stopRecording}>
                    Stop Recording
                  </button>
                )}

                <label className="upload-button">
                  Upload Audio/Video File ☁️
                  <input
                    type="file"
                    accept="audio/*,video/*"
                    onChange={handleFileUpload}
                    style={{ display: "none" }}
                  />
                </label>
              </>
            ) : (
              <div className="recording-options">
                <button
                  className="option-button audio-option"
                  onClick={() => startRecording(false)}
                >
                  🎤 Audio Only
                </button>
                <button
                  className="option-button video-option"
                  onClick={() => startRecording(true)}
                >
                  📹 Video + Audio
                </button>
                <button
                  className="cancel-button"
                  onClick={() => setShowRecordingOptions(false)}
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          {audioBlob && (
            <button className="submit-button" onClick={sendToBackend}>
              Clone My Voice 🎤
            </button>
          )}
          
          <button 
            className="practice-button" 
            onClick={() => navigate('/practice')}
          >
            📚 Assistance / Practice
          </button>
          
        </div>

        <p className="instructions">
          We need about 10 seconds of your voice to create your unique clone.
        </p>
      </main>
    </div>
  );
}

export default App;
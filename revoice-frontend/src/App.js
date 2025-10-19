// src/App.js
import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./App.css";

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [mediaBlob, setMediaBlob] = useState(null); // audio or video
  const [mediaStream, setMediaStream] = useState(null);
  const [showRecordingOptions, setShowRecordingOptions] = useState(false);
  const [recordingType, setRecordingType] = useState(null); // 'audio' | 'video'
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [cleanedText, setCleanedText] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [pipeline, setPipeline] = useState(null); // optional: shown if backend returns it

  const mediaRecorderRef = useRef(null);
  const timerRef = useRef(null);
  const videoRef = useRef(null);
  const navigate = useNavigate();

  // -------- Backend URL helpers (fixes blank tab issue) --------
  const API_BASE =
    process.env.REACT_APP_API ||
    (window.location.origin.includes(":3000")
      ? window.location.origin.replace(":3000", ":5001")
      : "http://localhost:5001");

  const toAbs = (path) => (path?.startsWith("http") ? path : `${API_BASE}${path}`);

  // -------- Recording --------
  const startRecording = async (withVideo = false) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: withVideo ? { width: 1280, height: 720 } : false,
        audio: true,
      });

      if (withVideo && stream.getVideoTracks().length === 0) {
        alert("No camera track detected. Check camera permissions and try again.");
      }

      setMediaStream(stream);
      setShowRecordingOptions(false);
      setRecordingType(withVideo ? "video" : "audio");
      setIsRecording(true);
      setRecordingTime(0);
      setMediaBlob(null);
      setCleanedText(null);
      setAudioUrl(null);
      setVideoUrl(null);
      setPipeline(null);

      // Use explicit codecs for better browser support (Chrome)
      const mimeType = withVideo ? "video/webm;codecs=vp8,opus" : "audio/webm;codecs=opus";
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      const chunks = [];
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) chunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });
        setMediaBlob(blob);
        stream.getTracks().forEach((t) => t.stop());
        setMediaStream(null);
      };

      mediaRecorder.start();
    } catch (error) {
      console.error("Error accessing media devices:", error);
      alert(`Could not access camera/microphone: ${error.message}`);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      // IMPORTANT: do NOT clear recordingType here — we need it to decide lipsync
      // setTimeout(() => setRecordingType(null), 200); // ❌ REMOVE THIS
    }
  };

  // Upload from disk
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setMediaBlob(file);
    setRecordingType(file.type.startsWith("video") ? "video" : "audio");
    setCleanedText(null);
    setAudioUrl(null);
    setVideoUrl(null);
    setPipeline(null);
    console.log("File uploaded:", file.name, file.type);
  };

  // Timer + live preview for video
  useEffect(() => {
    if (recordingType === "video" && mediaStream && videoRef.current) {
      videoRef.current.srcObject = mediaStream;
      videoRef.current.onloadedmetadata = () => {
        videoRef.current.play().catch((e) => console.error("Video play error:", e));
      };
    }
  }, [recordingType, mediaStream]);

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => setRecordingTime((t) => t + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
    };
  }, [mediaStream]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, "0");
    const secs = (seconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  // -------- Fetch helper (robust JSON parsing) --------
  async function fetchJSON(url, options) {
    const res = await fetch(url, options);
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      return data;
    } else {
      const text = await res.text();
      try {
        const data = JSON.parse(text);
        if (!res.ok) throw new Error(data.error || "Request failed");
        return data;
      } catch {
        throw new Error(text.slice(0, 300) || "Unexpected non-JSON response");
      }
    }
  }

  // -------- Send to backend --------
  const sendToBackend = async () => {
    if (!mediaBlob) return alert("Please record or upload media first!");

    setIsSubmitting(true);
    setCleanedText(null);
    setAudioUrl(null);
    setVideoUrl(null);
    setPipeline(null);

    const formData = new FormData();
    formData.append("media", mediaBlob, "recording.webm");

    // Derive lipsync from real blob mime (more robust than UI state)
    const looksLikeVideo = mediaBlob.type?.startsWith("video");
    formData.append("use_lipsync", looksLikeVideo ? "true" : "false");

    try {
      const data = await fetchJSON("/api/revoice", { method: "POST", body: formData });

      setCleanedText(data.cleaned_text || null);
      setAudioUrl(data.audio_url ? toAbs(data.audio_url) : null);
      setVideoUrl(data.video_url ? toAbs(data.video_url) : null);
      if (data.pipeline) setPipeline(data.pipeline);

      // Also open in a new tab if you want that behavior:
      if (data.video_url) {
        window.open(toAbs(data.video_url), "_blank", "noopener,noreferrer");
      } else if (data.audio_url) {
        window.open(toAbs(data.audio_url), "_blank", "noopener,noreferrer");
      }
    } catch (err) {
      console.error(err);
      alert(`Backend error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // -------- UI --------
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
            {pipeline && (
              <div className="badge" style={{ marginLeft: 12 }}>
                pipeline: {pipeline}
              </div>
            )}
          </div>

          <div className={`recording-area ${isRecording ? "recording-active" : ""}`}>
            {isRecording && recordingType === "video" ? (
              <video ref={videoRef} autoPlay playsInline muted className="video-preview" />
            ) : (
              <div className={`rec-indicator ${isRecording ? "active" : ""}`}>
                <span className="rec-dot"></span>
                {isRecording ? "REC" : "READY"}
              </div>
            )}
          </div>

          <div className="button-container">
            {!showRecordingOptions ? (
              <>
                {!isRecording ? (
                  <button className="primary-button" onClick={() => setShowRecordingOptions(true)}>
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
                <button className="option-button audio-option" onClick={() => startRecording(false)}>
                  🎤 Audio Only
                </button>
                <button className="option-button video-option" onClick={() => startRecording(true)}>
                  📹 Video + Audio
                </button>
                <button className="cancel-button" onClick={() => setShowRecordingOptions(false)}>
                  Cancel
                </button>
              </div>
            )}
          </div>

          {mediaBlob && (
            <button className="submit-button" onClick={sendToBackend} disabled={isSubmitting}>
              {isSubmitting ? "Processing…" : "Clone / ReVoice 🎤"}
            </button>
          )}

          <button className="practice-button" onClick={() => navigate("/practice")} disabled={isSubmitting}>
            📚 Assistance / Practice
          </button>

          {/* Results */}
          {(cleanedText || audioUrl || videoUrl) && (
            <div style={{ marginTop: 16, width: "100%" }}>
              {cleanedText && (
                <div className="analysis-card">
                  <h3>🧼 Cleaned Transcript</h3>
                  <p style={{ whiteSpace: "pre-wrap" }}>{cleanedText}</p>
                </div>
              )}
              {videoUrl && (
                <div className="analysis-card">
                  <h3>✅ Lip-Synced Video</h3>
                  <video src={videoUrl} controls style={{ width: "100%", maxWidth: 720 }} />
                  <div style={{ marginTop: 8 }}>
                    <a href={videoUrl} target="_blank" rel="noreferrer">
                      Open raw file
                    </a>{" "}
                    |{" "}
                    <a href={videoUrl} download>
                      Download
                    </a>
                  </div>
                </div>
              )}
              {!videoUrl && audioUrl && (
                <div className="analysis-card">
                  <h3>✅ Corrected Audio</h3>
                  <audio src={audioUrl} controls />
                  <div style={{ marginTop: 8 }}>
                    <a href={audioUrl} target="_blank" rel="noreferrer">
                      Open raw file
                    </a>{" "}
                    |{" "}
                    <a href={audioUrl} download>
                      Download
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <p className="instructions">
          We need about 10 seconds of your voice to create your unique clone. For lip-sync, record a short video.
        </p>
      </main>
    </div>
  );
}

export default App;

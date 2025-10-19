import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Practice.css';

function Practice() {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const timerRef = useRef(null);
  const navigate = useNavigate();

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      const chunks = [];
      mediaRecorder.ondataavailable = (event) => chunks.push(event.data);

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        setAudioBlob(blob);
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      setAnalysis(null);

      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (error) {
      alert(`Could not access microphone: ${error.message}`);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  const analyzeAudio = async () => {
    if (!audioBlob) return;

    setIsAnalyzing(true);
    
    // TODO: Replace with actual AI analysis API call
    // Simulating API call with setTimeout
    setTimeout(() => {
      const mockAnalysis = {
        pace: "Your speaking pace is moderate at approximately 140 words per minute.",
        clarity: "Speech clarity is good with clear pronunciation of most words.",
        pauses: "Natural pauses detected. Consider taking slightly longer pauses between thoughts.",
        volume: "Volume is consistent throughout the recording.",
        suggestions: [
          "Practice breathing exercises before speaking to reduce tension",
          "Try speaking in shorter sentences to maintain clarity",
          "Record yourself regularly to track improvement over time",
          "Focus on relaxing your jaw and facial muscles while speaking"
        ]
      };
      setAnalysis(mockAnalysis);
      setIsAnalyzing(false);
    }, 2000);

    // ACTUAL IMPLEMENTATION (uncomment when ready):
    // const formData = new FormData();
    // formData.append('audio', audioBlob);
    // 
    // try {
    //   const response = await fetch('YOUR_API_ENDPOINT', {
    //     method: 'POST',
    //     body: formData
    //   });
    //   const data = await response.json();
    //   setAnalysis(data);
    //   setIsAnalyzing(false);
    // } catch (error) {
    //   console.error('Analysis error:', error);
    //   setIsAnalyzing(false);
    // }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
    const secs = (seconds % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <div className="Practice">
      <header className="header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Back to Home
        </button>
        <div className="logo-container">
          <div className="waveform">
            <div className="wave"></div>
            <div className="wave"></div>
            <div className="wave"></div>
            <div className="wave"></div>
            <div className="wave"></div>
          </div>
          <h1 className="logo">ReVoice Practice</h1>
        </div>
        <p className="tagline">PERSONALIZED SPEECH ASSISTANCE & PRACTICE</p>
      </header>

      <main className="main-content">
        <div className="warning-banner">
          <span className="warning-icon">⚠️</span>
          <p>
            <strong>Disclaimer:</strong> This tool provides general suggestions and is not 
            intended as medical advice. For professional speech therapy, please consult a 
            licensed speech-language pathologist.
          </p>
        </div>

        <div className="practice-container">
          <div className="recording-section">
            <h2>Record Your Speech</h2>
            <div className="status-bar">
              <div className="timer">{formatTime(recordingTime)}</div>
            </div>

            <div className={`recording-area ${isRecording ? 'recording-active' : ''}`}>
              <div className={`rec-indicator ${isRecording ? 'active' : ''}`}>
                <span className="rec-dot"></span>
                {isRecording ? 'RECORDING' : 'READY'}
              </div>
            </div>

            <div className="button-group">
              {!isRecording ? (
                <button className="primary-button" onClick={startRecording}>
                  🎤 Start Recording
                </button>
              ) : (
                <button className="primary-button stop" onClick={stopRecording}>
                  ⏹ Stop Recording
                </button>
              )}

              {audioBlob && !isRecording && (
                <button 
                  className="analyze-button" 
                  onClick={analyzeAudio}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? '🔄 Analyzing...' : '🤖 Analyze My Speech'}
                </button>
              )}
            </div>
          </div>

          {analysis && (
            <div className="analysis-section">
              <h2>📊 Speech Analysis</h2>
              
              <div className="analysis-card">
                <h3>Pace</h3>
                <p>{analysis.pace}</p>
              </div>

              <div className="analysis-card">
                <h3>Clarity</h3>
                <p>{analysis.clarity}</p>
              </div>

              <div className="analysis-card">
                <h3>Pauses</h3>
                <p>{analysis.pauses}</p>
              </div>

              <div className="analysis-card">
                <h3>Volume</h3>
                <p>{analysis.volume}</p>
              </div>

              <div className="suggestions-card">
                <h3>💡 Personalized Suggestions</h3>
                <ul>
                  {analysis.suggestions.map((suggestion, index) => (
                    <li key={index}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default Practice;
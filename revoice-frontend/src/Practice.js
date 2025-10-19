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
  const canvasRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animationRef = useRef(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

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
        
        // Stop audio visualization
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      setAnalysis(null);
      setAudioBlob(null); // Clear previous audio blob

      // Start audio visualization
      startAudioVisualization(stream);

      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (error) {
      alert(`Could not access microphone: ${error.message}`);
    }
  };

  const startAudioVisualization = (stream) => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = audioContext.createAnalyser();
    const microphone = audioContext.createMediaStreamSource(stream);
    
    analyser.fftSize = 256;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    microphone.connect(analyser);
    
    audioContextRef.current = audioContext;
    analyserRef.current = analyser;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const canvasContext = canvas.getContext('2d');
    const WIDTH = canvas.width;
    const HEIGHT = canvas.height;
    
    const draw = () => {
      animationRef.current = requestAnimationFrame(draw);
      
      analyser.getByteFrequencyData(dataArray);
      
      // Clear canvas with gradient background
      const gradient = canvasContext.createLinearGradient(0, 0, 0, HEIGHT);
      gradient.addColorStop(0, '#667eea');
      gradient.addColorStop(1, '#764ba2');
      canvasContext.fillStyle = gradient;
      canvasContext.fillRect(0, 0, WIDTH, HEIGHT);
      
      // Draw waveform bars
      const barWidth = (WIDTH / bufferLength) * 2.5;
      let barHeight;
      let x = 0;
      
      for (let i = 0; i < bufferLength; i++) {
        barHeight = (dataArray[i] / 255) * HEIGHT * 0.8;
        
        // Create bar gradient
        const barGradient = canvasContext.createLinearGradient(0, HEIGHT - barHeight, 0, HEIGHT);
        barGradient.addColorStop(0, '#ffffff');
        barGradient.addColorStop(1, 'rgba(255, 255, 255, 0.5)');
        
        canvasContext.fillStyle = barGradient;
        canvasContext.fillRect(x, HEIGHT - barHeight, barWidth, barHeight);
        
        x += barWidth + 1;
      }
    };
    
    draw();
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
    
    const formData = new FormData();
    // Add timestamp to ensure uniqueness
    const timestamp = Date.now();
    formData.append('audio', audioBlob, `recording_${timestamp}.webm`);
    
    try {
      const response = await fetch('http://localhost:5001/api/analyze', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Analysis failed');
      }
      
      const data = await response.json();
      setAnalysis(data);
      setIsAnalyzing(false);
      
      // IMPORTANT: Clear the audio blob after analysis to force new recording
      setAudioBlob(null);
    } catch (error) {
      console.error('Analysis error:', error);
      alert(`Analysis error: ${error.message}. Make sure the backend is running!`);
      setIsAnalyzing(false);
    }
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
          <span className="warning-icon">!</span>
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
              {isRecording ? (
                <canvas 
                  ref={canvasRef} 
                  width="700" 
                  height="120"
                  className="audio-visualizer"
                />
              ) : (
                <div className="rec-indicator ready">
                  <div className="ready-waveform">
                    <div className="bar"></div>
                    <div className="bar"></div>
                    <div className="bar"></div>
                    <div className="bar"></div>
                    <div className="bar"></div>
                  </div>
                  <span className="ready-text">READY TO RECORD</span>
                </div>
              )}
            </div>

            <div className="button-group">
              {!isRecording ? (
                <button className="primary-button" onClick={startRecording}>
                  Start Recording
                </button>
              ) : (
                <button className="primary-button stop" onClick={stopRecording}>
                  Stop Recording
                </button>
              )}

              {audioBlob && !isRecording && (
                <button 
                  className="analyze-button" 
                  onClick={analyzeAudio}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? 'Analyzing...' : 'Analyze My Speech'}
                </button>
              )}
            </div>
          </div>

          {analysis && (
            <div className="analysis-section">
              <h2>Your Results</h2>
              
              {/* Combined Analysis Card - Box 1 */}
              <div className="analysis-card">
                <h3>What We Found</h3>
                {analysis.has_stutters ? (
                  <>
                    <p style={{marginBottom: '12px'}}>
                      <strong>{analysis.stutter_count} stutter moment(s)</strong> detected in your speech.
                    </p>
                    
                    {analysis.detection_summary?.stutter_types && (
                      <div style={{marginBottom: '12px'}}>
                        <strong>Types:</strong> {Object.entries(analysis.detection_summary.stutter_types)
                          .map(([type, count]) => `${type} (${count})`)
                          .join(', ')}
                      </div>
                    )}
                    
                    {analysis.detection_summary?.events_detail && analysis.detection_summary.events_detail.length > 0 && (
                      <div style={{fontSize: '14px', color: '#666'}}>
                        {analysis.detection_summary.events_detail.map((event, idx) => (
                          <div key={idx} style={{marginTop: '6px'}}>
                            • <strong>{event.time}</strong> - "{event.word}" ({event.type})
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <p>Great fluent speech! No stutters detected.</p>
                )}
              </div>

              {/* Personalized Tips Card - Box 2 */}
              {analysis.has_stutters && analysis.practice && (
                <div className="tips-card">
                  <h3>Detailed Guidance for You</h3>
                  <p style={{marginBottom: '20px', fontSize: '16px', lineHeight: '1.6', fontWeight: '600', color: '#d63031'}}>
                    You stuttered on the word "{analysis.practice.word}" (the {analysis.practice.sound.toLowerCase()} sound)
                  </p>
                  
                  {analysis.practice.detailed_tips ? (
                    <div style={{
                      fontSize: '14px', 
                      lineHeight: '1.8', 
                      color: '#2d3436', 
                      whiteSpace: 'pre-line',
                      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }}>
                      {analysis.practice.detailed_tips}
                    </div>
                  ) : (
                    <p style={{fontSize: '14px', lineHeight: '1.5', color: '#555'}}>
                      {analysis.practice.stutter_type === 'repetition' && 
                        "Try stretching the sound slowly and smoothly. Take your time and use gentle contact."}
                      {analysis.practice.stutter_type === 'acoustic_repetition' && 
                        "Practice saying the sound slowly and continuously, without breaking into separate bursts."}
                      {analysis.practice.stutter_type === 'prolongation' && 
                        "Start softly and transition quickly through the sound. Reduce air pressure and keep it brief."}
                      {analysis.practice.stutter_type === 'block' && 
                        "Begin with a gentle breath out (like 'hhh') before the sound. Stay relaxed and allow airflow."}
                    </p>
                  )}
                </div>
              )}

              {/* Practice Audio - Box 3 */}
              {analysis.practice && analysis.practice.audio_file && (
                <div className="suggestions-card">
                  <h3>Your Practice Exercise</h3>
                  <p style={{marginBottom: '15px', fontSize: '14px'}}>
                    Listen and repeat to build muscle memory for fluent speech.
                  </p>
                  <audio 
                    controls 
                    style={{width: '100%', marginTop: '10px'}}
                    src={`http://localhost:5001/api/audio/${analysis.practice.audio_file}`}
                  >
                    Your browser does not support audio playback.
                  </audio>
                  
                  {analysis.practice.script && (
                    <details style={{marginTop: '15px'}}>
                      <summary style={{cursor: 'pointer', fontWeight: 'bold', marginBottom: '10px'}}>
                        View Practice Script
                      </summary>
                      <pre style={{
                        background: 'rgba(255,255,255,0.1)', 
                        padding: '15px', 
                        borderRadius: '8px',
                        whiteSpace: 'pre-wrap',
                        fontSize: '13px',
                        lineHeight: '1.6'
                      }}>
                        {analysis.practice.script}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default Practice;
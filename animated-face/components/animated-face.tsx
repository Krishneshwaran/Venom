"use client"

import { useEffect, useState, useRef } from "react"

export default function VenomAIFace() {
  const [isBlinking, setIsBlinking] = useState(false)
  const [smileIntensity, setSmileIntensity] = useState(1)
  const [isListening, setIsListening] = useState(false)
  const [eyesOpen, setEyesOpen] = useState(false)
  const [statusMessage, setStatusMessage] = useState("Initializing...")
  const [isConnected, setIsConnected] = useState(false)
  const [transcript, setTranscript] = useState("")
  const [aiResponse, setAiResponse] = useState("")
  const [debugLog, setDebugLog] = useState([])
  const [audioPermission, setAudioPermission] = useState(false)
  
  const recognitionRef = useRef(null)
  const isListeningRef = useRef(false) // Track listening state
  const API_BASE_URL = "http://localhost:8000"

  const addDebugLog = (message) => {
    const timestamp = new Date().toLocaleTimeString()
    setDebugLog(prev => [`[${timestamp}] ${message}`, ...prev].slice(0, 15))
    console.log(`[Venom] ${message}`)
  }

  // Request microphone permission
  useEffect(() => {
    const requestMicPermission = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach(track => track.stop())
        setAudioPermission(true)
        addDebugLog("✅ Microphone permission granted")
        setStatusMessage("Ready! Click 'Start Listening' or say 'Hey Venom'")
      } catch (error) {
        addDebugLog(`❌ Microphone permission denied: ${error.message}`)
        setStatusMessage("⚠️ Microphone access denied - Please allow in browser settings")
        setAudioPermission(false)
      }
    }

    requestMicPermission()
  }, [])

  // Initialize speech recognition
  useEffect(() => {
    if (!audioPermission) return

    if (typeof window !== 'undefined') {
      const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition
      
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition()
        recognitionRef.current.continuous = true
        recognitionRef.current.interimResults = true
        recognitionRef.current.lang = 'en-US'
        recognitionRef.current.maxAlternatives = 1

        recognitionRef.current.onstart = () => {
          addDebugLog("🎤 Microphone activated - Listening...")
          isListeningRef.current = true
        }

        recognitionRef.current.onresult = (event) => {
          let interimTranscript = ''
          let finalTranscript = ''

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript
            if (event.results[i].isFinal) {
              finalTranscript += transcript + ' '
            } else {
              interimTranscript += transcript
            }
          }

          if (finalTranscript) {
            const text = finalTranscript.trim().toLowerCase()
            addDebugLog(`✅ Heard: "${text}"`)
            setTranscript(text)
            handleSpeechResult(text)
          } else if (interimTranscript) {
            // Show interim results in real-time
            setTranscript(`(hearing...) ${interimTranscript}`)
          }
        }

        recognitionRef.current.onerror = (event) => {
          addDebugLog(`❌ Speech error: ${event.error}`)
          
          if (event.error === 'no-speech') {
            addDebugLog("⏸️ No speech detected, still listening...")
            // Don't stop on no-speech, just continue
          } else if (event.error === 'aborted') {
            addDebugLog("⚠️ Recognition aborted, restarting...")
            if (isListeningRef.current) {
              setTimeout(() => restartRecognition(), 100)
            }
          } else if (event.error === 'network') {
            addDebugLog("🌐 Network error, retrying...")
            if (isListeningRef.current) {
              setTimeout(() => restartRecognition(), 1000)
            }
          } else if (event.error === 'not-allowed') {
            addDebugLog("🚫 Microphone access denied!")
            setAudioPermission(false)
            setIsListening(false)
            isListeningRef.current = false
          } else {
            addDebugLog(`⚠️ Error: ${event.error}`)
          }
        }

        recognitionRef.current.onend = () => {
          addDebugLog("🔄 Recognition ended, checking if should restart...")
          // Auto-restart if still supposed to be listening
          if (isListeningRef.current) {
            addDebugLog("♻️ Auto-restarting recognition...")
            setTimeout(() => restartRecognition(), 100)
          } else {
            addDebugLog("⏹️ Listening stopped")
          }
        }

        addDebugLog("✅ Speech recognition initialized")
        setStatusMessage("Ready! Click 'Start Listening'")
      } else {
        addDebugLog("❌ Speech recognition not supported")
        setStatusMessage("⚠️ Speech recognition not supported - Use Chrome browser")
      }
    }

    return () => {
      if (recognitionRef.current) {
        isListeningRef.current = false
        try {
          recognitionRef.current.stop()
        } catch (e) {
          // Ignore errors on cleanup
        }
      }
    }
  }, [audioPermission])

  // Blinking animation
  useEffect(() => {
    if (!isConnected || !eyesOpen) return

    const blinkInterval = setInterval(() => {
      setIsBlinking(true)
      setTimeout(() => setIsBlinking(false), 150)
    }, 3000)

    return () => clearInterval(blinkInterval)
  }, [isConnected, eyesOpen])

  // Smile animation
  useEffect(() => {
    let direction = 1
    const smileInterval = setInterval(() => {
      setSmileIntensity((prev) => {
        const newIntensity = prev + direction * 0.1
        if (newIntensity >= 1.2) direction = -1
        if (newIntensity <= 0.8) direction = 1
        return Math.max(0.8, Math.min(1.2, newIntensity))
      })
    }, 100)

    return () => clearInterval(smileInterval)
  }, [])

  const restartRecognition = () => {
    if (recognitionRef.current && isListeningRef.current) {
      try {
        recognitionRef.current.start()
        addDebugLog("✅ Recognition restarted")
      } catch (error) {
        if (error.message.includes('already started')) {
          addDebugLog("ℹ️ Recognition already running")
        } else {
          addDebugLog(`❌ Restart failed: ${error.message}`)
        }
      }
    }
  }

  const startListening = () => {
    if (!audioPermission) {
      addDebugLog("❌ No microphone permission")
      alert("Please allow microphone access in your browser settings!")
      return
    }

    if (recognitionRef.current && !isListeningRef.current) {
      try {
        isListeningRef.current = true
        recognitionRef.current.start()
        setIsListening(true)
        setStatusMessage("🎤 Listening... Say 'Hey Venom' to activate")
        addDebugLog("🎤 Started listening - Speak now!")
      } catch (error) {
        if (error.message.includes('already started')) {
          addDebugLog("ℹ️ Already listening")
          setIsListening(true)
        } else {
          addDebugLog(`❌ Failed to start: ${error.message}`)
          isListeningRef.current = false
        }
      }
    }
  }

  const stopListening = () => {
    if (recognitionRef.current) {
      isListeningRef.current = false
      setIsListening(false)
      try {
        recognitionRef.current.stop()
        addDebugLog("🛑 Stopped listening")
        setStatusMessage("Stopped. Click 'Start Listening' to resume")
      } catch (error) {
        addDebugLog(`⚠️ Stop error: ${error.message}`)
      }
    }
  }

  const handleSpeechResult = async (text) => {
    addDebugLog(`🔍 Processing: "${text}"`)

    const activationPhrases = ['hey venom', 'hi venom', 'venom', 'heyenom', 'a venom', 'heyenom']
    const isActivation = activationPhrases.some(phrase => text.includes(phrase))

    if (isActivation && !isConnected) {
      addDebugLog("🚀 Activation phrase detected!")
      await activateVenom()
    } else if (isConnected && text.length > 2) {
      addDebugLog(`📤 Sending command to API: "${text}"`)
      await processCommand(text)
    } else {
      addDebugLog(`⏭️ Ignored: "${text}" (too short or not activated)`)
    }
  }

  const activateVenom = async () => {
    setStatusMessage("🔄 Connecting to Venom...")
    setEyesOpen(false)
    addDebugLog("🔌 Connecting to API...")
    
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (response.ok) {
        const data = await response.json()
        addDebugLog(`✅ API connected: ${data.status}`)
        addDebugLog(`📹 Camera: ${data.camera_available ? 'Available' : 'Not available'}`)
        
        await new Promise(resolve => setTimeout(resolve, 800))
        
        setIsConnected(true)
        setEyesOpen(true)
        setStatusMessage("🟢 Connected! I'm listening...")
        addDebugLog("🟢 Venom activated!")
        
        // Speak confirmation
        await fetch(`${API_BASE_URL}/tts/speak`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: "Yes, I'm listening!", save_audio: false })
        })
        addDebugLog("🔊 Spoke: Yes, I'm listening!")
      } else {
        throw new Error(`API responded with status ${response.status}`)
      }
    } catch (error) {
      addDebugLog(`❌ Connection failed: ${error.message}`)
      setStatusMessage(`❌ Connection failed: ${error.message}`)
      setEyesOpen(false)
      setIsConnected(false)
    }
  }

  const processCommand = async (command) => {
    setStatusMessage(`⚙️ Processing: "${command}"...`)
    addDebugLog(`⚙️ Processing command...`)
    
    try {
      const response = await fetch(`${API_BASE_URL}/ai/process-command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: command, language: 'en' })
      })

      if (response.ok) {
        const data = await response.json()
        const responseText = data.response || "Command processed"
        setAiResponse(responseText)
        setStatusMessage(`💬 ${responseText}`)
        addDebugLog(`✅ Response: ${responseText}`)
        
        // Speak the response
        if (data.response) {
          await fetch(`${API_BASE_URL}/tts/speak`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: data.response, save_audio: false })
          })
          addDebugLog(`🔊 Spoke response`)
        }
      } else {
        addDebugLog(`❌ API error: ${response.status}`)
      }
    } catch (error) {
      addDebugLog(`❌ Command failed: ${error.message}`)
      setStatusMessage("❌ Failed to process command")
    }
  }

  const testAudioCapture = () => {
    addDebugLog("🧪 Testing audio capture...")
    if (!audioPermission) {
      addDebugLog("❌ No audio permission. Please allow microphone access.")
      alert("Please allow microphone access first!")
      return
    }

    if (recognitionRef.current) {
      addDebugLog("✅ Speech recognition is available")
      addDebugLog("🎤 Starting test... Say something!")
      startListening()
      
      // Show a helpful message
      setTimeout(() => {
        if (isListeningRef.current) {
          addDebugLog("💡 TIP: Speak clearly and say 'Hey Venom'")
        }
      }, 2000)
    } else {
      addDebugLog("❌ Speech recognition not initialized")
    }
  }

  const handleManualActivation = async () => {
    if (!isConnected) {
      await activateVenom()
    } else {
      setIsConnected(false)
      setEyesOpen(false)
      setStatusMessage("💤 Deactivated. Say 'Hey Venom' to reactivate")
      setAiResponse("")
      addDebugLog("🔴 Venom deactivated")
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-purple-100 to-blue-100 p-4">
      {/* Face container */}
      <div className="relative w-96 h-80 mb-8">
        {/* Left Eye */}
        <div className="absolute left-8 top-16 w-32 h-32 bg-black rounded-full flex items-center justify-center shadow-lg">
          <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center relative">
            <div
              className={`w-12 h-12 bg-black rounded-full transition-all duration-150 ${
                isBlinking || !eyesOpen ? "scale-y-0" : "scale-y-100"
              }`}
              style={{ transformOrigin: "center" }}
            >
              <div className="absolute top-2 left-2 w-4 h-4 bg-white rounded-full opacity-80" />
            </div>
          </div>
          <div className="absolute bottom-4 left-4 w-6 h-6 bg-white rounded-full opacity-60" />
        </div>

        {/* Right Eye */}
        <div className="absolute right-8 top-16 w-32 h-32 bg-black rounded-full flex items-center justify-center shadow-lg">
          <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center relative">
            <div
              className={`w-12 h-12 bg-black rounded-full transition-all duration-150 ${
                isBlinking || !eyesOpen ? "scale-y-0" : "scale-y-100"
              }`}
              style={{ transformOrigin: "center" }}
            >
              <div className="absolute top-2 left-2 w-4 h-4 bg-white rounded-full opacity-80" />
            </div>
          </div>
          <div className="absolute bottom-4 left-4 w-6 h-6 bg-white rounded-full opacity-60" />
        </div>

        {/* Smile */}
        <svg
          className="absolute bottom-12 left-1/2 transform -translate-x-1/2"
          width="200"
          height="100"
          viewBox="0 0 200 100"
          style={{ scaleY: smileIntensity, transformOrigin: "center" }}
        >
          <path d="M 30 50 Q 100 90 170 50" stroke="black" strokeWidth="16" fill="none" strokeLinecap="round" />
        </svg>

        {/* Cheeks */}
        <div className="absolute bottom-32 left-8 w-20 h-20 bg-pink-300 rounded-full opacity-70 blur-xl" />
        <div className="absolute bottom-32 right-8 w-20 h-20 bg-pink-300 rounded-full opacity-70 blur-xl" />
      </div>

      {/* Status and Controls */}
      <div className="text-center bg-white rounded-2xl shadow-xl p-6 max-w-3xl w-full">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          {isConnected ? "🟢 Venom AI - Active" : "⚫ Venom AI - Sleeping"}
        </h1>
        
        <div className="mb-4">
          <p className={`text-lg font-medium ${isConnected ? 'text-green-600' : 'text-gray-600'}`}>
            {statusMessage}
          </p>
          
          {/* Audio Status Indicators */}
          <div className="mt-3 flex items-center justify-center gap-4 flex-wrap">
            <span className={`text-sm px-3 py-1 rounded-full ${audioPermission ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              {audioPermission ? '🎤 Mic Allowed' : '🔇 Mic Denied'}
            </span>
            <span className={`text-sm px-3 py-1 rounded-full ${isListening ? 'bg-blue-100 text-blue-700 animate-pulse' : 'bg-gray-100 text-gray-500'}`}>
              {isListening ? '🔴 Listening' : '⚪ Not Listening'}
            </span>
            <span className={`text-sm px-3 py-1 rounded-full ${isConnected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
              {isConnected ? '✓ Connected' : '✗ Not Connected'}
            </span>
          </div>

          {transcript && (
            <p className="text-sm text-gray-600 mt-3 italic">
              "{transcript}"
            </p>
          )}
          {aiResponse && (
            <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
              <p className="text-sm font-semibold text-blue-800 mb-1">🤖 Venom says:</p>
              <p className="text-blue-700">{aiResponse}</p>
            </div>
          )}
        </div>

        {/* Control Buttons */}
        <div className="flex flex-wrap gap-3 justify-center mb-4">
          {!isListening ? (
            <button
              onClick={startListening}
              disabled={!audioPermission}
              className="px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl"
            >
              🎤 Start Listening
            </button>
          ) : (
            <button
              onClick={stopListening}
              className="px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition-all shadow-lg hover:shadow-xl animate-pulse"
            >
              🛑 Stop Listening
            </button>
          )}

          <button
            onClick={handleManualActivation}
            className={`px-6 py-3 rounded-lg font-semibold transition-all shadow-lg hover:shadow-xl ${
              isConnected
                ? 'bg-orange-600 text-white hover:bg-orange-700'
                : 'bg-purple-600 text-white hover:bg-purple-700'
            }`}
          >
            {isConnected ? "💤 Sleep" : "⚡ Activate"}
          </button>

          <button
            onClick={testAudioCapture}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-lg hover:shadow-xl"
          >
            🧪 Test Audio
          </button>
        </div>

        {/* API Status */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
            <span className="font-mono">{API_BASE_URL}</span>
          </div>
        </div>
      </div>

      {/* Debug Log */}
      <div className="mt-6 bg-gray-900 rounded-xl shadow-xl p-4 max-w-3xl w-full">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-bold text-green-400 flex items-center gap-2">
            🐛 Debug Log
            {isListening && <span className="animate-pulse text-red-400">● LIVE</span>}
          </h2>
          <button
            onClick={() => setDebugLog([])}
            className="text-xs text-gray-400 hover:text-white transition-colors"
          >
            Clear
          </button>
        </div>
        <div className="bg-black rounded p-3 h-56 overflow-y-auto font-mono text-xs">
          {debugLog.length === 0 ? (
            <p className="text-gray-500">Waiting for activity...</p>
          ) : (
            debugLog.map((log, index) => (
              <p key={index} className="text-green-400 mb-1 hover:text-green-300">
                {log}
              </p>
            ))
          )}
        </div>
      </div>

      {/* Instructions */}
      <div className="mt-6 text-center max-w-3xl bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-700 mb-3">📋 Quick Start:</h2>
        <ol className="text-left text-gray-600 space-y-2 text-sm">
          <li>1. ✅ Ensure API is running: <code className="bg-gray-200 px-2 py-1 rounded text-xs">python api_with_debug.py</code></li>
          <li>2. 🎤 Click <strong>"Start Listening"</strong> (you should see "🔴 Listening")</li>
          <li>3. 🗣️ Say <strong>"Hey Venom"</strong> clearly</li>
          <li>4. 👀 Watch eyes close → connect → open & blink</li>
          <li>5. 💬 Start talking! Venom will respond</li>
        </ol>
        
        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-sm text-blue-800">
            <strong>💡 Tip:</strong> Keep the "Start Listening" button active (showing 🔴) for Venom to hear you. 
            Check the debug log to see what's being captured!
          </p>
        </div>
      </div>
    </div>
  )
}
"use client"

import { useEffect, useState } from "react"

interface VenomState {
  is_active: boolean
  is_listening: boolean
  is_speaking: boolean
  last_command: string
  timestamp: number
}

export default function AnimatedFace() {
  const [isBlinking, setIsBlinking] = useState(false)
  const [smileIntensity, setSmileIntensity] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [eyesOpen, setEyesOpen] = useState(false) // Start with eyes closed
  const [venomState, setVenomState] = useState<VenomState>({
    is_active: false,
    is_listening: false,
    is_speaking: false,
    last_command: "",
    timestamp: 0
  })

  // Poll API for Venom state
  useEffect(() => {
    // Use environment variable or fallback to localhost
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${apiUrl}/api/state`)
        if (response.ok) {
          const state: VenomState = await response.json()
          setVenomState(state)
          setEyesOpen(state.is_active) // Eyes open when Venom is active
        }
      } catch (error) {
        console.error('Error fetching Venom state:', error)
      }
    }, 500) // Poll every 500ms

    return () => clearInterval(pollInterval)
  }, [])

  // Blinking animation - only when eyes are open and not loading
  useEffect(() => {
    if (isLoading || !eyesOpen) return

    const blinkInterval = setInterval(() => {
      setIsBlinking(true)
      setTimeout(() => setIsBlinking(false), 150)
    }, 3000)

    return () => clearInterval(blinkInterval)
  }, [isLoading, eyesOpen])

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

  const handleFetchData = async () => {
    setIsLoading(true)
    setEyesOpen(false) // Close eyes while loading

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 2000))
      setEyesOpen(true) // Open eyes on success
    } catch (error) {
      console.error("Error fetching data:", error)
      setEyesOpen(true)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center gap-8">
      {/* Face container */}
      <div className="relative w-96 h-80">
        {/* Left Eye */}
        <div className="absolute left-8 top-16 w-32 h-32 bg-black rounded-full flex items-center justify-center shadow-lg">
          {/* Eye white */}
          <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center relative">
            {/* Pupil */}
            <div
              className={`w-12 h-12 bg-black rounded-full transition-all duration-150 ${
                isBlinking || !eyesOpen ? "scale-y-0" : "scale-y-100"
              }`}
              style={{
                transformOrigin: "center",
              }}
            >
              {/* Shine */}
              <div className="absolute top-2 left-2 w-4 h-4 bg-white rounded-full opacity-80" />
            </div>
          </div>
          {/* Small highlight */}
          <div className="absolute bottom-4 left-4 w-6 h-6 bg-white rounded-full opacity-60" />
        </div>

        {/* Right Eye */}
        <div className="absolute right-8 top-16 w-32 h-32 bg-black rounded-full flex items-center justify-center shadow-lg">
          {/* Eye white */}
          <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center relative">
            {/* Pupil */}
            <div
              className={`w-12 h-12 bg-black rounded-full transition-all duration-150 ${
                isBlinking || !eyesOpen ? "scale-y-0" : "scale-y-100"
              }`}
              style={{
                transformOrigin: "center",
              }}
            >
              {/* Shine */}
              <div className="absolute top-2 left-2 w-4 h-4 bg-white rounded-full opacity-80" />
            </div>
          </div>
          {/* Small highlight */}
          <div className="absolute bottom-4 left-4 w-6 h-6 bg-white rounded-full opacity-60" />
        </div>

        {/* Smile */}
        <svg
          className="absolute bottom-12 left-1/2 transform -translate-x-1/2"
          width="200"
          height="100"
          viewBox="0 0 200 100"
          style={{
            scaleY: smileIntensity,
            transformOrigin: "center",
          }}
        >
          <path d="M 30 50 Q 100 90 170 50" stroke="black" strokeWidth="16" fill="none" strokeLinecap="round" />
        </svg>
      </div>

      {/* Cheeks */}
      <div className="absolute bottom-32 left-8 w-20 h-20 bg-pink-300 rounded-full opacity-70 blur-xl" />
      <div className="absolute bottom-32 right-8 w-20 h-20 bg-pink-300 rounded-full opacity-70 blur-xl" />

      {/* Decorative text and status */}
      <div className="text-center mt-12">
        <h1 className="text-4xl font-bold text-gray-800 mb-2">Venom AI Assistant</h1>
        <p className="text-gray-600 mb-2">
          {venomState.is_active ? (
            <span className="text-green-600 font-semibold">🟢 Active & Listening</span>
          ) : (
            <span className="text-gray-400">💤 Waiting for activation...</span>
          )}
        </p>
        {venomState.last_command && (
          <p className="text-sm text-gray-500 italic">Last: "{venomState.last_command}"</p>
        )}
        <div className="mt-4 text-xs text-gray-400">
          Say "hey venom" to activate
        </div>
      </div>
    </div>
  )
}
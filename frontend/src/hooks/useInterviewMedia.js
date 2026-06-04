import { useState, useRef, useCallback, useEffect } from 'react'

function isMobileDevice() {
  return /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(
    typeof navigator !== 'undefined' ? navigator.userAgent : ''
  )
}

export default function useInterviewMedia() {
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [cameraStatus, setCameraStatus] = useState('idle')
  const [screenShareEnabled, setScreenShareEnabled] = useState(false)
  const [screenShareStatus, setScreenShareStatus] = useState('idle')
  const [isMobile] = useState(isMobileDevice)

  const cameraVideoRef = useRef(null)
  const screenVideoRef = useRef(null)
  const cameraStreamRef = useRef(null)
  const screenStreamRef = useRef(null)

  useEffect(() => {
    return () => {
      stopCamera()
      stopScreenShare()
    }
  }, [])

  const startCamera = useCallback(async () => {
    if (cameraEnabled) return true
    setCameraStatus('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      cameraStreamRef.current = stream
      setCameraEnabled(true)
      setCameraStatus('active')
      if (cameraVideoRef.current) {
        cameraVideoRef.current.srcObject = stream
      }
      return true
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setCameraStatus('denied')
      } else if (err.name === 'NotFoundError') {
        setCameraStatus('unavailable')
      } else {
        setCameraStatus('error')
      }
      setCameraEnabled(false)
      return false
    }
  }, [cameraEnabled])

  const stopCamera = useCallback(() => {
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach(t => t.stop())
      cameraStreamRef.current = null
    }
    setCameraEnabled(false)
    setCameraStatus('idle')
    if (cameraVideoRef.current) {
      cameraVideoRef.current.srcObject = null
    }
  }, [])

  const startScreenShare = useCallback(async () => {
    if (screenShareEnabled) return true
    if (isMobile) {
      setScreenShareStatus('unavailable')
      return false
    }
    setScreenShareStatus('requesting')
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true })
      screenStreamRef.current = stream
      stream.getVideoTracks()[0].onended = () => {
        stopScreenShare()
      }
      setScreenShareEnabled(true)
      setScreenShareStatus('active')
      if (screenVideoRef.current) {
        screenVideoRef.current.srcObject = stream
      }
      return true
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'AbortError') {
        setScreenShareStatus('denied')
      } else {
        setScreenShareStatus('error')
      }
      setScreenShareEnabled(false)
      return false
    }
  }, [screenShareEnabled, isMobile])

  const stopScreenShare = useCallback(() => {
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(t => t.stop())
      screenStreamRef.current = null
    }
    setScreenShareEnabled(false)
    setScreenShareStatus('idle')
    if (screenVideoRef.current) {
      screenVideoRef.current.srcObject = null
    }
  }, [])

  return {
    cameraEnabled,
    cameraStatus,
    screenShareEnabled,
    screenShareStatus,
    isMobile,
    cameraVideoRef,
    screenVideoRef,
    startCamera,
    stopCamera,
    startScreenShare,
    stopScreenShare,
  }
}

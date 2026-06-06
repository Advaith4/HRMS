import { useState, useRef, useCallback, useEffect } from 'react'

export default function useRecorder() {
  const [isRecording, setIsRecording] = useState(false)
  const [duration, setDuration] = useState(0)
  const [audioBlob, setAudioBlob] = useState(null)
  const [audioMeta, setAudioMeta] = useState(null)
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const audioLevelTimerRef = useRef(null)
  const audioContextRef = useRef(null)
  const startedAtRef = useRef(null)
  const isStartingRef = useRef(false)
  const recordingIdRef = useRef(0)
  const audioLevelStatsRef = useRef({ samples: 0, maxRms: 0, avgRms: 0 })

  const cleanupActiveRecording = useCallback((stream = null) => {
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = null
    if (audioLevelTimerRef.current) clearInterval(audioLevelTimerRef.current)
    audioLevelTimerRef.current = null
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {})
      audioContextRef.current = null
    }
    const activeStream = stream || mediaRecorderRef.current?.stream
    if (activeStream) {
      activeStream.getTracks().forEach(t => t.stop())
    }
    isStartingRef.current = false
  }, [])

  useEffect(() => {
    return () => {
      cleanupActiveRecording()
    }
  }, [cleanupActiveRecording])

  const startRecording = useCallback(async () => {
    if (isStartingRef.current || (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive')) {
      console.warn('audio_recording_start_ignored', {
        recordingId: recordingIdRef.current,
        isStarting: isStartingRef.current,
        recorderState: mediaRecorderRef.current?.state,
      })
      return false
    }
    isStartingRef.current = true
    setError(null)
    setAudioBlob(null)
    setAudioMeta(null)
    setDuration(0)
    chunksRef.current = []
    audioLevelStatsRef.current = { samples: 0, maxRms: 0, avgRms: 0 }
    recordingIdRef.current += 1
    const recordingId = recordingIdRef.current
    console.info('audio_recording_reset', { recordingId, chunks: chunksRef.current.length })
    console.info('audio_recorder_support_matrix', {
      recordingId,
      support: {
        'audio/webm': MediaRecorder.isTypeSupported('audio/webm'),
        'audio/webm;codecs=opus': MediaRecorder.isTypeSupported('audio/webm;codecs=opus'),
        'audio/mp4': MediaRecorder.isTypeSupported('audio/mp4'),
        'audio/ogg': MediaRecorder.isTypeSupported('audio/ogg'),
      },
    })

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 48000,
        }
      })
      const firstTrack = stream.getAudioTracks()[0]
      console.info('audio_recording_microphone_ready', {
        recordingId,
        firstTrack: firstTrack ? {
          label: firstTrack.label,
          settings: firstTrack.getSettings?.() || {},
          enabled: firstTrack.enabled,
          muted: firstTrack.muted,
          readyState: firstTrack.readyState,
        } : null,
        tracks: stream.getAudioTracks().map(track => ({
          label: track.label,
          settings: track.getSettings?.() || {},
          enabled: track.enabled,
          muted: track.muted,
          readyState: track.readyState,
        })),
      })
    } catch (err) {
      const msg = err.name === 'NotAllowedError'
        ? 'Microphone access denied. Please allow microphone access or use text answers.'
        : err.name === 'NotFoundError'
        ? 'No microphone found. Please connect a microphone or use text answers.'
        : `Microphone error: ${err.message}`
      setError(msg)
      isStartingRef.current = false
      return false
    }

    try {
      const track = stream.getAudioTracks()[0]
      if (track) {
        track.onmute = () => console.warn('audio_track_muted', { recordingId, readyState: track.readyState })
        track.onunmute = () => console.info('audio_track_unmuted', { recordingId, readyState: track.readyState })
        track.onended = () => console.warn('audio_track_ended', { recordingId, readyState: track.readyState })
      }

      const AudioContextCtor = window.AudioContext || window.webkitAudioContext
      if (AudioContextCtor && track) {
        const audioContext = new AudioContextCtor()
        audioContextRef.current = audioContext
        const analyser = audioContext.createAnalyser()
        analyser.fftSize = 2048
        const source = audioContext.createMediaStreamSource(stream)
        source.connect(analyser)
        const buffer = new Uint8Array(analyser.fftSize)
        audioLevelTimerRef.current = setInterval(() => {
          analyser.getByteTimeDomainData(buffer)
          let sumSquares = 0
          for (let i = 0; i < buffer.length; i += 1) {
            const centered = (buffer[i] - 128) / 128
            sumSquares += centered * centered
          }
          const rms = Math.sqrt(sumSquares / buffer.length)
          const prev = audioLevelStatsRef.current
          const samples = prev.samples + 1
          audioLevelStatsRef.current = {
            samples,
            maxRms: Math.max(prev.maxRms, rms),
            avgRms: ((prev.avgRms * prev.samples) + rms) / samples,
          }
          if (samples <= 3 || samples % 5 === 0) {
            console.info('audio_signal_sample', {
              recordingId,
              rms: Number(rms.toFixed(5)),
              maxRms: Number(audioLevelStatsRef.current.maxRms.toFixed(5)),
              avgRms: Number(audioLevelStatsRef.current.avgRms.toFixed(5)),
            })
          }
        }, 500)
      } else {
        console.warn('audio_signal_sampler_unavailable', { recordingId, hasAudioContext: Boolean(AudioContextCtor), hasTrack: Boolean(track) })
      }

      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      console.info('audio_recorder_config_selected', {
        recordingId,
        mode: 'browser-default',
        forcedConfigDisabled: true,
        previousForcedConfig: {
          mimeType: 'audio/webm;codecs=opus',
          audioBitsPerSecond: 128000,
        },
        actualMimeType: recorder.mimeType,
        actualAudioBitsPerSecond: recorder.audioBitsPerSecond,
      })

      recorder.ondataavailable = (e) => {
        console.info('audio_recording_chunk', {
          recordingId,
          chunkSizeBytes: e.data.size,
          chunkIndex: chunksRef.current.length,
          chunkType: e.data.type,
        })
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        const finalMimeType = recorder.mimeType || chunksRef.current[0]?.type || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type: finalMimeType })
        const durationMs = startedAtRef.current ? Date.now() - startedAtRef.current : 0
        const blobId = `${recordingId}-${blob.size}-${durationMs}`
        const finalTrackState = track ? {
          enabled: track.enabled,
          muted: track.muted,
          readyState: track.readyState,
          settings: track.getSettings?.() || {},
        } : null
        console.info('audio_recording_stop', {
          recordingId,
          blobId,
          durationMs,
          fileSizeBytes: blob.size,
          mimeType: finalMimeType,
          chunkCount: chunksRef.current.length,
          recorderMimeType: recorder.mimeType,
          recorderState: recorder.state,
          trackState: finalTrackState,
          signal: {
            samples: audioLevelStatsRef.current.samples,
            maxRms: Number(audioLevelStatsRef.current.maxRms.toFixed(5)),
            avgRms: Number(audioLevelStatsRef.current.avgRms.toFixed(5)),
          },
          sizeLooksRealistic: blob.size >= 20_000,
        })
        if (durationMs >= 3000 && blob.size < 20_000) {
          console.warn('audio_recording_suspiciously_small_blob', {
            recordingId,
            durationMs,
            fileSizeBytes: blob.size,
            expectedMinimumBytes: 20_000,
            signal: audioLevelStatsRef.current,
          })
        }
        setAudioMeta({ recordingId, blobId, durationMs, fileSizeBytes: blob.size, mimeType: finalMimeType, chunkCount: chunksRef.current.length, signal: audioLevelStatsRef.current })
        setAudioBlob(blob)
        cleanupActiveRecording(stream)
      }

      recorder.onerror = () => {
        setError('Recording failed. Please try again or use text answers.')
        setIsRecording(false)
        cleanupActiveRecording(stream)
      }

      recorder.start(250)
      startedAtRef.current = Date.now()
      console.info('audio_recording_start', {
        recordingId,
        mode: 'browser-default',
        mimeType: recorder.mimeType,
        audioBitsPerSecond: recorder.audioBitsPerSecond,
        trackState: track ? {
          enabled: track.enabled,
          muted: track.muted,
          readyState: track.readyState,
          settings: track.getSettings?.() || {},
        } : null,
      })
      setIsRecording(true)

      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1)
      }, 1000)

      return true
    } catch (err) {
      setError(`Failed to start recording: ${err.message}`)
      setIsRecording(false)
      cleanupActiveRecording(stream)
      return false
    }
  }, [cleanupActiveRecording])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      const track = mediaRecorderRef.current.stream.getAudioTracks()[0]
      console.info('audio_recording_stop_requested', {
        recordingId: recordingIdRef.current,
        recorderState: mediaRecorderRef.current.state,
        trackState: track ? {
          enabled: track.enabled,
          muted: track.muted,
          readyState: track.readyState,
          settings: track.getSettings?.() || {},
        } : null,
      })
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }, [])

  const clearRecording = useCallback(() => {
    setAudioBlob(null)
    setAudioMeta(null)
    setDuration(0)
    setError(null)
    chunksRef.current = []
    audioLevelStatsRef.current = { samples: 0, maxRms: 0, avgRms: 0 }
    console.info('audio_recording_clear', { recordingId: recordingIdRef.current })
  }, [])

  return {
    isRecording,
    duration,
    audioBlob,
    audioMeta,
    error,
    startRecording,
    stopRecording,
    clearRecording,
  }
}

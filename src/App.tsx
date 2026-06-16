import { useState, useRef, useEffect, useCallback } from 'react'
import './App.css'

const WS_URL = (import.meta as ImportMeta & { env: Record<string, string> }).env?.VITE_WS_URL
  ?? 'ws://localhost:8000/call'

const MAX_RETRIES = 5

function getMimeType(): string {
  const candidatos = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/ogg',
  ]
  return candidatos.find((m) => MediaRecorder.isTypeSupported(m)) ?? ''
}

type Status = 'idle' | 'connecting' | 'recording' | 'reconnecting' | 'error'

export default function App() {
  const [status, setStatus]         = useState<Status>('idle')
  const [transcript, setTranscript] = useState('')
  const [errorMsg, setErrorMsg]     = useState('')
  const [volumen, setVolumen]        = useState(0) // 0-100

  const wsRef          = useRef<WebSocket | null>(null)
  const recorderRef    = useRef<MediaRecorder | null>(null)
  const streamRef      = useRef<MediaStream | null>(null)
  const retriesRef     = useRef(0)
  const activoRef      = useRef(false)
  const conectarWSRef  = useRef<((stream: MediaStream) => void) | null>(null)
  // Web Audio API para el medidor de volumen
  const audioCtxRef    = useRef<AudioContext | null>(null)
  const analyserRef    = useRef<AnalyserNode | null>(null)
  const rafRef         = useRef<number | null>(null)

  // Arranca el loop de lectura de volumen usando AnalyserNode
  const iniciarMedidor = useCallback((stream: MediaStream) => {
    const ctx      = new AudioContext()
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 256
    const source = ctx.createMediaStreamSource(stream)
    source.connect(analyser)
    audioCtxRef.current  = ctx
    analyserRef.current  = analyser

    const buffer = new Uint8Array(analyser.frequencyBinCount)

    const tick = () => {
      analyser.getByteTimeDomainData(buffer)
      // RMS del buffer → valor 0-100
      let sum = 0
      for (let i = 0; i < buffer.length; i++) {
        const s = (buffer[i] - 128) / 128
        sum += s * s
      }
      const rms = Math.sqrt(sum / buffer.length)
      setVolumen(Math.min(100, Math.round(rms * 400)))
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
  }, [])

  const detenerMedidor = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    audioCtxRef.current?.close()
    audioCtxRef.current = null
    analyserRef.current = null
    setVolumen(0)
  }, [])

  const pararRecorder = useCallback(() => {
    recorderRef.current?.stop()
    recorderRef.current = null
  }, [])

  const detener = useCallback(() => {
    activoRef.current = false
    retriesRef.current = 0
    pararRecorder()
    detenerMedidor()
    wsRef.current?.close()
    wsRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    setStatus('idle')
  }, [pararRecorder, detenerMedidor])

  const conectarWS = useCallback((stream: MediaStream) => {
    if (!activoRef.current) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      if (!activoRef.current) { ws.close(); return }
      retriesRef.current = 0
      setStatus('recording')
      setErrorMsg('')

      const mimeType = getMimeType()
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {})
      recorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          ws.send(e.data)
        }
      }
      recorder.start(1000)
    }

    ws.onmessage = (e) => {
      const fragment = (e.data as string).trim()
      if (fragment) {
        setTranscript((prev) => (prev ? prev + ' ' + fragment : fragment))
      }
    }

    ws.onerror = () => {
      // siempre precede a onclose; el reintento se gestiona ahí
    }

    ws.onclose = () => {
      pararRecorder()
      if (!activoRef.current) return

      if (retriesRef.current < MAX_RETRIES) {
        const delay = Math.min(500 * 2 ** retriesRef.current, 8000)
        retriesRef.current++
        setStatus('reconnecting')
        setErrorMsg(`Reconectando… (intento ${retriesRef.current}/${MAX_RETRIES})`)
        setTimeout(() => conectarWSRef.current?.(stream), delay)
      } else {
        setErrorMsg('No se pudo mantener la conexión con el servidor.')
        setStatus('error')
        activoRef.current = false
        detenerMedidor()
        streamRef.current?.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }
    }
  }, [pararRecorder, detenerMedidor])

  useEffect(() => {
    conectarWSRef.current = conectarWS
  }, [conectarWS])

  const iniciar = useCallback(async () => {
    setTranscript('')
    setErrorMsg('')
    setStatus('connecting')
    retriesRef.current = 0
    activoRef.current = true

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
    } catch {
      setErrorMsg('No se pudo acceder al micrófono.')
      setStatus('error')
      activoRef.current = false
      return
    }

    iniciarMedidor(stream)
    conectarWS(stream)
  }, [conectarWS, iniciarMedidor])

  useEffect(() => {
    return () => { detener() }
  }, [detener])

  const grabando     = status === 'recording'
  const reconectando = status === 'reconnecting'

  return (
    <main className="app">

      <button
        className={`mic-btn ${grabando || reconectando ? 'active' : ''}`}
        onClick={grabando || reconectando ? detener : iniciar}
        disabled={status === 'connecting'}
        aria-label={grabando || reconectando ? 'Detener' : 'Hablar'}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="36" height="36">
          <path d="M12 1a4 4 0 0 1 4 4v6a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm6 9a1 1 0 0 1 2 0 8 8 0 0 1-7 7.93V20h2a1 1 0 0 1 0 2H9a1 1 0 0 1 0-2h2v-2.07A8 8 0 0 1 4 10a1 1 0 0 1 2 0 6 6 0 0 0 12 0z"/>
        </svg>
      </button>

      {/* Medidor de volumen — visible solo mientras graba o reconecta */}
      {(grabando || reconectando) && (
        <div className="volumen-wrap" aria-label={`Nivel de entrada: ${volumen}%`}>
          <div
            className="volumen-bar"
            style={{ width: `${volumen}%` }}
          />
        </div>
      )}

      <p className="status-label">
        {status === 'idle'         && 'Toca para hablar'}
        {status === 'connecting'   && 'Conectando…'}
        {status === 'recording'    && 'Escuchando — toca para detener'}
        {status === 'reconnecting' && 'Reconectando…'}
      </p>

      {errorMsg && <p className="error-msg">{errorMsg}</p>}

      {transcript && (
        <div className="transcript">
          <p>{transcript.trim()}</p>
          <button onClick={() => navigator.clipboard.writeText(transcript.trim())}>
            Copiar
          </button>
        </div>
      )}

    </main>
  )
}
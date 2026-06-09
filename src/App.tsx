import { useState, useRef } from 'react'
import './App.css'

const WS_URL = 'ws://localhost:8000/call'

type Status = 'idle' | 'connecting' | 'recording' | 'error'

function App() {
  const [status, setStatus]         = useState<Status>('idle')
  const [transcript, setTranscript] = useState('')
  const [errorMsg, setErrorMsg]     = useState('')

  const wsRef       = useRef<WebSocket | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef   = useRef<MediaStream | null>(null)

  async function iniciar() {
    setTranscript('')
    setErrorMsg('')
    setStatus('connecting')

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
    } catch {
      setErrorMsg('No se pudo acceder al micrófono.')
      setStatus('error')
      return
    }

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('recording')
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      recorderRef.current = recorder
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) ws.send(e.data)
      }
      recorder.start(1000)
    }

    ws.onmessage = (e) => setTranscript((prev) => prev + ' ' + e.data)

    ws.onerror = () => {
      setErrorMsg('No se pudo conectar al servidor. ¿Está corriendo FastAPI?')
      setStatus('error')
      detener()
    }

    ws.onclose = () => setStatus((prev) => prev === 'error' ? 'error' : 'idle')
  }

  function detener() {
    recorderRef.current?.stop()
    wsRef.current?.close()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    setStatus('idle')
  }

  const grabando = status === 'recording'

  return (
    <main className="app">

      <button
        className={`mic-btn ${grabando ? 'active' : ''}`}
        onClick={grabando ? detener : iniciar}
        disabled={status === 'connecting'}
        aria-label={grabando ? 'Detener' : 'Hablar'}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="36" height="36">
          <path d="M12 1a4 4 0 0 1 4 4v6a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm6 9a1 1 0 0 1 2 0 8 8 0 0 1-7 7.93V20h2a1 1 0 0 1 0 2H9a1 1 0 0 1 0-2h2v-2.07A8 8 0 0 1 4 10a1 1 0 0 1 2 0 6 6 0 0 0 12 0z"/>
        </svg>
      </button>

      <p className="status-label">
        {status === 'idle'       && 'Toca para hablar'}
        {status === 'connecting' && 'Conectando…'}
        {status === 'recording'  && 'Escuchando — toca para detener'}
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

export default App
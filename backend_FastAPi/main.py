from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
import tempfile, os, asyncio

app = FastAPI(title="Wispher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Cargando modelo Whisper...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Modelo listo ✓")


@app.get("/")
def root():
    return {"status": "Wispher API activa"}


@app.websocket("/call")
async def websocket_transcripcion(websocket: WebSocket):
    await websocket.accept()

    chunks: list[bytes] = []

    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_bytes(), timeout=30.0)
            chunks.append(data)

            # Cuando acumula ~2s de audio, transcribe y manda el texto
            total = sum(len(c) for c in chunks)
            if total >= 64_000:
                texto = await transcribir_chunks(chunks)
                if texto.strip():
                    await websocket.send_text(texto.strip())
                chunks = []

    except asyncio.TimeoutError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        # Transcribe lo que quedó en el buffer al cerrar
        if chunks:
            texto = await transcribir_chunks(chunks)
            if texto.strip():
                try:
                    await websocket.send_text(texto.strip())
                except Exception:
                    pass


async def transcribir_chunks(chunks: list[bytes]) -> str:
    audio_bytes = b"".join(chunks)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(audio_bytes)
        ruta = tmp.name

    try:
        loop = asyncio.get_event_loop()
        texto = await loop.run_in_executor(None, _transcribir, ruta)
        return texto
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)  ## Consoderación: verificar si se crean archivos temporales o eliminar esta parte del codigo 


def _transcribir(ruta: str) -> str:
    segmentos, _ = model.transcribe(
        ruta,
        language="es",
        vad_filter=True,
    )
    return " ".join(seg.text.strip() for seg in segmentos)
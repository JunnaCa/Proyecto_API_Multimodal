from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from starlette.websockets import WebSocketState
import tempfile, os, asyncio, logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wispher")

CHUNKS_POR_TRANSCRIPCION = 5   # lotes de ~5s
MAX_BUFFER_BYTES = 5_000_000   # 5 MB

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")

model: WhisperModel | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    logger.info("Cargando modelo Whisper (small)...")
    try:
        model = WhisperModel("small", device="cpu", compute_type="int8")
        logger.info("Modelo Whisper listo ✓")
    except Exception as e:
        logger.error(f"Error al cargar el modelo Whisper: {e}")
        raise
    yield
    _executor.shutdown(wait=False)
    model = None
    logger.info("Modelo Whisper descargado")


app = FastAPI(title="Wispher API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        # "https://<canister-id>.icp0.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "Wispher API activa",
        "modelo_cargado": model is not None,
    }


@app.websocket("/call")
async def websocket_transcripcion(websocket: WebSocket):
    await websocket.accept()
    logger.info("Cliente conectado")

    queue: asyncio.Queue[list[bytes] | None] = asyncio.Queue()

    # El primer chunk de un stream WebM contiene el header del contenedor
    # (EBML + Tracks). Sin él, ffmpeg no puede decodificar ningún lote posterior.
    # Lo guardamos en cuanto llega y lo anteponemos a cada lote.
    webm_header: bytes | None = None

    async def worker():
        while True:
            lote = await queue.get()
            if lote is None:
                break
            try:
                texto = await _transcribir_async(lote)
                if texto.strip() and websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(texto.strip())
            except Exception as e:
                logger.error(f"Error en worker de transcripción: {e}")

    worker_task = asyncio.create_task(worker())
    chunks: list[bytes] = []

    try:
        while True:
            data = await websocket.receive_bytes()

            # El primer chunk siempre contiene el header WebM (EBML).
            # Lo identificamos por la firma de 4 bytes 0x1A45DFA3.
            if webm_header is None:
                if data[:4] == b'\x1a\x45\xdf\xa3':
                    webm_header = data
                    logger.info("Header WebM capturado ✓")
                else:
                    # Todavía no tenemos header, acumular y esperar
                    chunks.append(data)
                    continue

            # Protección OOM
            total_bytes = sum(len(c) for c in chunks) + len(data)
            if total_bytes > MAX_BUFFER_BYTES:
                logger.warning("Buffer superó el límite, reiniciando acumulador")
                chunks = []

            chunks.append(data)

            if len(chunks) >= CHUNKS_POR_TRANSCRIPCION:
                # Anteponer el header a cada lote para que ffmpeg pueda decodificarlo
                lote_completo = [webm_header] + chunks
                await queue.put(lote_completo)
                chunks = []

    except WebSocketDisconnect:
        logger.info("Cliente desconectado normalmente")
    except Exception as e:
        logger.error(f"Error inesperado en WebSocket: {e}")
    finally:
        if chunks and webm_header is not None:
            await queue.put([webm_header] + chunks)
        await queue.put(None)
        await worker_task


async def _transcribir_async(chunks: list[bytes]) -> str:
    audio_bytes = b"".join(chunks)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(audio_bytes)
        ruta = tmp.name

    try:
        loop = asyncio.get_running_loop()
        texto = await loop.run_in_executor(_executor, _transcribir, ruta)
        return texto
    finally:
        try:
            os.remove(ruta)
        except OSError as e:
            logger.warning(f"No se pudo eliminar archivo temporal {ruta}: {e}")


def _transcribir(ruta: str) -> str:
    if model is None:
        raise RuntimeError("El modelo Whisper no está cargado")
    segmentos, _ = model.transcribe(
        ruta,
        language="es",
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
        condition_on_previous_text=False,
    )
    return " ".join(seg.text.strip() for seg in segmentos)   
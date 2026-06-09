# =============================================================================
# MULTIMODAL API - FastAPI Template
# =============================================================================
# This API handles 4 types of input:
#   1. AUDIO  → Speech-to-text transcription
#   2. IMAGE  → Image captioning / visual question answering
#   3. VIDEO  → Video analysis / description
#   4. CALL   → Real-time audio streaming (WebSocket)
#
# Each section is clearly marked with where to plug in your model.
# =============================================================================

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import tempfile

# =============================================================================
# APP SETUP
# Initialize the FastAPI app and allow requests from any frontend (CORS).
# =============================================================================

app = FastAPI(
    title="Multimodal API",
    description="API that processes audio, image, video and live calls",
    version="1.0.0"
)

# Allow all origins so your HTML page can call this API freely.
# In production, replace "*" with your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ██████████████████████████████████████████████████████████████████████████
# SECTION 1 — AUDIO MODEL
# ██████████████████████████████████████████████████████████████████████████
#
# PURPOSE: Load your speech-to-text model once when the server starts.
#          Reusing the same instance avoids reloading it on every request.
#
# RECOMMENDED LIBRARIES:
#   pip install faster-whisper
#   pip install openai-whisper
#   pip install speechbrain
#
# HOW TO PLUG IN YOUR MODEL:
#   Replace the comment below with your model initialization.
#   Example with faster-whisper:
#
#     from faster_whisper import WhisperModel
#     audio_model = WhisperModel("small", device="cpu", compute_type="int8")
#
# ██████████████████████████████████████████████████████████████████████████

# ↓↓↓ LOAD YOUR AUDIO MODEL HERE ↓↓↓
audio_model = None
# ↑↑↑ END AUDIO MODEL SETUP ↑↑↑


# =============================================================================
# ██████████████████████████████████████████████████████████████████████████
# SECTION 2 — IMAGE MODEL
# ██████████████████████████████████████████████████████████████████████████
#
# PURPOSE: Load your image analysis model once at startup.
#          Used for captioning, classification, or visual Q&A.
#
# RECOMMENDED LIBRARIES:
#   pip install transformers torch pillow       ← BLIP, ViT, etc.
#   pip install ultralytics                     ← YOLO object detection
#   pip install timm                            ← image classification
#
# HOW TO PLUG IN YOUR MODEL:
#   Example with BLIP (image captioning):
#
#     from transformers import BlipProcessor, BlipForConditionalGeneration
#     from PIL import Image
#
#     image_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
#     image_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
#
# ██████████████████████████████████████████████████████████████████████████

# ↓↓↓ LOAD YOUR IMAGE MODEL HERE ↓↓↓
image_model = None
image_processor = None
# ↑↑↑ END IMAGE MODEL SETUP ↑↑↑


# =============================================================================
# ██████████████████████████████████████████████████████████████████████████
# SECTION 3 — VIDEO MODEL
# ██████████████████████████████████████████████████████████████████████████
#
# PURPOSE: Load your video analysis model once at startup.
#          Used for action recognition, frame description, or summarization.
#
# RECOMMENDED LIBRARIES:
#   pip install opencv-python                   ← frame extraction
#   pip install transformers torch              ← VideoMAE, CLIP per frame
#   pip install moviepy                         ← video processing utilities
#   pip install decord                          ← fast video reading
#
# HOW TO PLUG IN YOUR MODEL:
#   A common approach is to extract key frames and analyze each with an image model.
#   Example:
#
#     import cv2
#     # video_model can be the same as image_model if you analyze frame by frame,
#     # or a dedicated video model like VideoMAE:
#
#     from transformers import VideoMAEForVideoClassification, AutoProcessor
#     video_processor = AutoProcessor.from_pretrained("MCG-NJU/videomae-base")
#     video_model = VideoMAEForVideoClassification.from_pretrained("MCG-NJU/videomae-base")
#
# ██████████████████████████████████████████████████████████████████████████

# ↓↓↓ LOAD YOUR VIDEO MODEL HERE ↓↓↓
video_model = None
video_processor = None
# ↑↑↑ END VIDEO MODEL SETUP ↑↑↑


# =============================================================================
# HELPER: save upload to a temp file and return the path
# This is used by audio, image, and video endpoints to handle uploaded files.
# =============================================================================

def save_upload(upload: UploadFile, suffix: str) -> str:
    """
    Saves an uploaded file to a temporary location on disk.
    Returns the file path so your model can read it.
    The caller is responsible for deleting the file after use.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    shutil.copyfileobj(upload.file, tmp)
    tmp.close()
    return tmp.name


# =============================================================================
# ██████████████████████████████████████████████████████████████████████████
# ENDPOINT 1 — /audio
# ██████████████████████████████████████████████████████████████████████████
#
# METHOD : POST
# INPUT  : audio file (mp3, wav, ogg, m4a, flac, webm)
# OUTPUT : { "transcription": "..." }
#
# HOW IT WORKS:
#   1. Receives the audio file from the frontend
#   2. Saves it temporarily to disk
#   3. Passes the path to your audio model
#   4. Returns the transcribed text
#   5. Deletes the temp file
#
# ██████████████████████████████████████████████████████████████████████████

@app.post("/audio", summary="Transcribe an audio file to text")
async def transcribe_audio(archivo: UploadFile = File(...)):
    """
    Accepts an audio file and returns its transcription as text.
    Supported formats: mp3, wav, ogg, m4a, flac, webm
    """

    # Save the uploaded file to a temporary path
    ruta = save_upload(archivo, suffix=os.path.splitext(archivo.filename)[-1])

    try:
        # ↓↓↓ CALL YOUR AUDIO MODEL HERE ↓↓↓
        #
        # Example with faster-whisper:
        #   segments, _ = audio_model.transcribe(ruta, language="es")
        #   texto = " ".join([s.text for s in segments])
        #
        # Example with openai-whisper:
        #   result = audio_model.transcribe(ruta)
        #   texto = result["text"]
        #
        texto = "[ Audio model not loaded yet — plug in your model above ]"
        # ↑↑↑ END AUDIO MODEL CALL ↑↑↑

    finally:
        # Always delete the temp file even if the model throws an error
        os.remove(ruta)

    return {"transcription": texto}


# =============================================================================
# ██████████████████████████████████████████████████████████████████████████
# ENDPOINT 2 — /image
# ██████████████████████████████████████████████████████████████████████████
#
# METHOD : POST
# INPUT  : image file (jpg, png, webp, gif)
# OUTPUT : { "description": "..." }
#
# HOW IT WORKS:
#   1. Receives the image file from the frontend
#   2. Saves it temporarily to disk
#   3. Passes it to your image model
#   4. Returns the description or detected labels
#   5. Deletes the temp file
#
# ██████████████████████████████████████████████████████████████████████████

@app.post("/image", summary="Analyze or caption an image")
async def analyze_image(archivo: UploadFile = File(...)):
    """
    Accepts an image file and returns a description or analysis.
    Supported formats: jpg, jpeg, png, webp, gif
    """

    ruta = save_upload(archivo, suffix=os.path.splitext(archivo.filename)[-1])

    try:
        # ↓↓↓ CALL YOUR IMAGE MODEL HERE ↓↓↓
        #
        # Example with BLIP captioning:
        #   from PIL import Image as PILImage
        #   img = PILImage.open(ruta).convert("RGB")
        #   inputs = image_processor(img, return_tensors="pt")
        #   out = image_model.generate(**inputs)
        #   descripcion = image_processor.decode(out[0], skip_special_tokens=True)
        #
        # Example with YOLO object detection:
        #   results = image_model(ruta)
        #   descripcion = str(results[0].boxes)
        #
        descripcion = "[ Image model not loaded yet — plug in your model above ]"
        # ↑↑↑ END IMAGE MODEL CALL ↑↑↑

    finally:
        os.remove(ruta)

    return {"description": descripcion}


# =============================================================================
# ██████████████████████████████████████████████████████████████████████████
# ENDPOINT 3 — /video
# ██████████████████████████████████████████████████████████████████████████
#
# METHOD : POST
# INPUT  : video file (mp4, avi, mov, webm)
# OUTPUT : { "analysis": "..." }
#
# HOW IT WORKS:
#   1. Receives the video file from the frontend
#   2. Saves it temporarily to disk
#   3. Extracts frames or passes the full video to your model
#   4. Returns a description, summary, or classification
#   5. Deletes the temp file
#
# ██████████████████████████████████████████████████████████████████████████

@app.post("/video", summary="Analyze or describe a video file")
async def analyze_video(archivo: UploadFile = File(...)):
    """
    Accepts a video file and returns an analysis or description.
    Supported formats: mp4, avi, mov, webm
    """

    ruta = save_upload(archivo, suffix=os.path.splitext(archivo.filename)[-1])

    try:
        # ↓↓↓ CALL YOUR VIDEO MODEL HERE ↓↓↓
        #
        # Option A — Frame by frame with OpenCV + image model:
        #   import cv2
        #   cap = cv2.VideoCapture(ruta)
        #   results = []
        #   frame_interval = 30  # analyze every 30th frame
        #   frame_count = 0
        #   while cap.isOpened():
        #       ret, frame = cap.read()
        #       if not ret: break
        #       if frame_count % frame_interval == 0:
        #           # pass frame to image_model here
        #           results.append("frame description")
        #       frame_count += 1
        #   cap.release()
        #   analisis = " | ".join(results)
        #
        # Option B — Dedicated video model (VideoMAE):
        #   inputs = video_processor(videos=[frames], return_tensors="pt")
        #   outputs = video_model(**inputs)
        #   analisis = str(outputs.logits.argmax(-1).item())
        #
        analisis = "[ Video model not loaded yet — plug in your model above ]"
        # ↑↑↑ END VIDEO MODEL CALL ↑↑↑

    finally:
        os.remove(ruta)

    return {"analysis": analisis}


# =============================================================================
# ██████████████████████████████████████████████████████████████████████████
# ENDPOINT 4 — /call  (WebSocket)
# ██████████████████████████████████████████████████████████████████████████
#
# METHOD : WebSocket (ws://localhost:8000/call)
# INPUT  : raw audio bytes streamed in real time from the frontend
# OUTPUT : text chunks sent back in real time as the model processes them
#
# HOW IT WORKS:
#   1. Frontend opens a WebSocket connection
#   2. Sends audio data as binary chunks (e.g. from MediaRecorder API)
#   3. Server accumulates chunks and processes them with your real-time model
#   4. Server sends back transcription or response text as it's generated
#   5. Connection stays open until the user hangs up
#
# RECOMMENDED LIBRARIES FOR REAL-TIME:
#   pip install faster-whisper                  ← stream transcription
#   pip install pyaudio                         ← audio I/O (if needed server side)
#   pip install websockets                      ← already included in fastapi
#
# ██████████████████████████████████████████████████████████████████████████

@app.websocket("/call")
async def live_call(websocket: WebSocket):
    """
    Real-time audio streaming endpoint via WebSocket.
    The frontend sends audio chunks; the server transcribes and responds in real time.
    """

    await websocket.accept()
    print("[ CALL ] Client connected")

    # Buffer to accumulate audio chunks before processing
    audio_buffer = bytearray()

    try:
        while True:
            # Receive the next audio chunk from the frontend
            chunk = await websocket.receive_bytes()
            audio_buffer.extend(chunk)

            # ↓↓↓ DEFINE YOUR CHUNK PROCESSING LOGIC HERE ↓↓↓
            #
            # Option A — Process every N bytes (sliding window):
            #   chunk_threshold = 32000  # ~1 second at 16kHz 16-bit mono
            #   if len(audio_buffer) >= chunk_threshold:
            #       # Save buffer to a temp file and transcribe
            #       with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            #           f.write(audio_buffer)
            #           tmp_path = f.name
            #       segments, _ = audio_model.transcribe(tmp_path, language="es")
            #       texto = " ".join([s.text for s in segments])
            #       os.remove(tmp_path)
            #       await websocket.send_text(texto)
            #       audio_buffer.clear()
            #
            # Option B — Send every chunk immediately for very fast models:
            #   resultado = your_realtime_model(chunk)
            #   await websocket.send_text(resultado)
            #
            # For now, we echo back a placeholder:
            await websocket.send_text(f"[ Received {len(chunk)} bytes — plug in your real-time model ]")
            # ↑↑↑ END CALL MODEL LOGIC ↑↑↑

    except WebSocketDisconnect:
        print("[ CALL ] Client disconnected")


# =============================================================================
# HEALTH CHECK
# A simple GET endpoint to verify the server is running.
# Visit http://localhost:8000/ in your browser to confirm.
# =============================================================================

@app.get("/", summary="Health check")
def health():
    return {
        "status": "running",
        "endpoints": {
            "audio": "POST /audio",
            "image": "POST /image",
            "video": "POST /video",
            "call":  "WS   /call",
            "docs":  "GET  /docs"
        }
    }


# =============================================================================
# RUN (optional — only needed if you run this file directly with `python main.py`)
# Normally you should use: uvicorn main:app --reload --port 8000
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

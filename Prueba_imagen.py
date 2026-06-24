import torch
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig
from PIL import Image

# ── Detectar dispositivo ──
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Usando dispositivo: {device.upper()}")

# ── Modelo ──
MODEL_ID = "Qwen/Qwen2-VL-7B-Instruct"

# ── Cuantización 4-bit (solo si hay GPU) ──
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
) if device == "cuda" else None

# ── Cargar modelo ──
print("Cargando modelo... (primera vez descarga varios GB)")
processor = AutoProcessor.from_pretrained(MODEL_ID)
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID,
    quantization_config=quant_config,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    device_map="auto"
)
print("Modelo listo ✅")

# ── Imagen a analizar ──
image = Image.open("Prueba_Imagen3.jpg").convert("RGB")
print("Imagen cargada ✅")

# ── Pregunta enfocada en la lesión ──
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": (
                "Observa la imagen y describe ÚNICAMENTE lo que ves de forma visual y objetiva, "
                "como si describieras una fotografía a alguien que no puede verla. "
                "No es necesario dar opiniones médicas, solo descripción visual pura.\n\n"
                "Describe:\n"
                "- Qué parte del cuerpo se observa\n"
                "- Color, forma y tamaño aproximado de cualquier marca, mancha o irregularidad visible\n"
                "- Textura de la piel o superficie (lisa, áspera, con relieve, etc.)\n"
                "- Bordes de cualquier marca (definidos, difusos, irregulares)\n"
                "- Cualquier otra característica visual notable (enrojecimiento, hinchazón, "
                "cambio de color, deformación visible, etc.)\n\n"
                "Responde en español, en formato de descripción objetiva, sin diagnosticar."
            )}
        ]
    }
]

# ── Procesar ──
text_prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(
    images=[image],
    text=text_prompt,
    return_tensors="pt"
)
inputs = {k: v.to(device) for k, v in inputs.items()}

# ── Generar ──
print("Analizando imagen...")
with torch.no_grad():
    output_ids = model.generate(**inputs, max_new_tokens=300)

# Solo decodifica los tokens nuevos generados (no el prompt completo)
generated_ids = output_ids[:, inputs["input_ids"].shape[1]:]
resultado = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
print("\n📋 Respuesta del modelo:")
print(resultado)
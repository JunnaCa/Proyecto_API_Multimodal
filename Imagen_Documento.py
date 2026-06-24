"""
CONVERSOR UNIVERSAL: Cualquier Documento → Cualquier Formato de Imagen
Soporta entradas: .docx, .doc, .pdf, .xlsx, .xls, .pptx, .ppt, .odt, .txt, etc.
Soporta salidas:  PNG, JPEG, WEBP, BMP, TIFF, etc.

Requisitos:
    sudo apt install libreoffice poppler-utils
    pip install pdf2image pillow
"""

import sys
import subprocess
from pathlib import Path
from pdf2image import convert_from_path

# ─── CONFIGURACIÓN DE ENTRADA Y SALIDA ────────────────────────────────────────

# 1. Coloca aquí el archivo que quieras (ej: .docx, .xlsx, .pdf, .pptx)
ARCHIVO_ENTRADA = "Documento_Prueba1.docx"  

# 2. Define el formato de imagen de salida: 'PNG', 'JPEG', 'WEBP', 'BMP'
FORMATO_IMAGEN = "PNG"  

# 3. Directorio donde se guardarán las imágenes
CARPETA_DESTINO = "./documentos_convertidos"

# 4. Calidad/Resolución (DPI). 200 es óptimo para lectura y pantallas.
DPI_CALIDAD = 200


# ─── FUNCIÓN PRINCIPAL DE CONVERSIÓN ──────────────────────────────────────────

def conversor_universal(ruta_archivo: Path, carpeta_salida: Path, formato: str, dpi: int):
    formato = formato.upper()
    
    # Validar que el archivo de origen exista
    if not ruta_archivo.exists():
        print(f"❌ Error: El archivo '{ruta_archivo}' no existe.")
        sys.exit(1)
        
    print(f"🚀 Iniciando conversión universal para: {ruta_archivo.name}")
    
    # Crear una subcarpeta específica para este documento
    subcarpeta_documento = carpeta_salida / ruta_archivo.stem
    subcarpeta_documento.mkdir(parents=True, exist_ok=True)
    
    pdf_temporal = None

    try:
        # CASO 1: El archivo ya es un PDF, no necesitamos LibreOffice
        if ruta_archivo.suffix.lower() == '.pdf':
            print("📄 El archivo ya es un PDF. Saltando paso de LibreOffice...")
            pdf_temporal = ruta_archivo
        
        # CASO 2: Cualquier otro documento (Word, Excel, PowerPoint, etc.)
        else:
            print(f"⏳ Paso 1/2: Convirtiendo '{ruta_archivo.suffix}' a PDF con LibreOffice...")
            
            comando_libreoffice = [
                'libreoffice', '--headless',
                '--convert-to', 'pdf',
                '--outdir', str(subcarpeta_documento.resolve()),
                str(ruta_archivo.resolve())
            ]
            
            subprocess.run(comando_libreoffice, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            # Ubicar el PDF generado por LibreOffice
            pdf_temporal = subcarpeta_documento / f"{ruta_archivo.stem}.pdf"
            
            if not pdf_temporal.exists():
                raise FileNotFoundError("LibreOffice no pudo generar el archivo PDF intermedio.")

        # Paso 2: Renderizar el PDF a las imágenes deseadas
        print(f"⏳ Paso 2/2: Renderizando páginas a formato {formato} ({dpi} DPI)...")
        
        # convert_from_path lee el PDF y genera objetos Image de Pillow
        paginas = convert_from_path(str(pdf_temporal.resolve()), dpi=dpi)
        total_paginas = len(paginas)
        print(f"📸 Se detectaron {total_paginas} página(s).")

        # Guardar cada página en el formato de imagen elegido
        for i, img_pagina in enumerate(paginas):
            # Formato de nombre: NombreArchivo_pag_01.png
            num_pag = str(i + 1).zfill(2)
            # La extensión en el nombre del archivo debe ir en minúsculas (ej: .png, .jpg)
            nombre_imagen = f"{ruta_archivo.stem}_pag_{num_pag}.{formato.lower()}"
            ruta_imagen_final = subcarpeta_documento / nombre_imagen
            
            # Guardar físicamente en disco usando Pillow
            # Mapeo automático de JPEG -> JPG para evitar problemas de extensión estándar
            formato_guardado = "JPEG" if formato == "JPG" else formato
            img_pagina.save(str(ruta_imagen_final.resolve()), format=formato_guardado)
            print(f"  ✅ Guardada: {nombre_imagen}")

        print(f"\n🎉 ¡Éxito! Todas las páginas se guardaron en: {subcarpeta_documento.resolve()}")

    except subprocess.CalledProcessError:
        print("\n❌ Error crítico: LibreOffice falló al procesar el documento.")
        print("Asegúrate de que el formato sea compatible y LibreOffice esté instalado.")
    except Exception as e:
        print(f"\n❌ Ocurrió un error inesperado: {e}")
        
    finally:
        # LIMPIEZA: Si usamos LibreOffice, borramos el PDF temporal que se creó
        if ruta_archivo.suffix.lower() != '.pdf' and pdf_temporal and pdf_temporal.exists():
            print("🧹 Limpiando archivos temporales...")
            pdf_temporal.unlink()


# ─── PUNTO DE ENTRADA (MAIN) ──────────────────────────────────────────────────

if __name__ == "__main__":
    conversor_universal(
        ruta_archivo=Path(ARCHIVO_ENTRADA),
        carpeta_salida=Path(CARPETA_DESTINO),
        formato=FORMATO_IMAGEN,
        dpi=DPI_CALIDAD
    )
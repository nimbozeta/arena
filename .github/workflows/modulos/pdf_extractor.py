"""
Módulo de Extracción de PDF
Ubicación en el repositorio: /modulos/pdf_extractor.py

Responsabilidad única: dado un PDF, devolver fragmentos de texto de
10-25 palabras, ya divididos en bloque superior/inferior (formato meme),
sin repetir fragmentos ya usados (historial persistente).

Esta es la reintegración del módulo "2.A" del documento de arquitectura
original — se había perdido en los pivotes hacia Bluesky/Instagram y
luego hacia Are.na. Ver Documento Maestro, sección 3.
"""
import fitz  # PyMuPDF
import re
import random
import json
import os
import hashlib

PDF_PATH = os.environ.get('PDF_SOURCE_PATH', 'pdf_source/texto.pdf')
HISTORIAL_PATH = os.environ.get('FRAGMENT_HISTORY_PATH', 'estado/historial_fragmentos.json')
MIN_PALABRAS = 10
MAX_PALABRAS = 25
MINIMO_PARA_DIVIDIR = 6  # por debajo de esto, todo el texto va al bloque superior


def cargar_texto_pdf(ruta):
    doc = fitz.open(ruta)
    texto_crudo = ""
    for pagina in doc:
        texto_crudo += pagina.get_text()
    doc.close()
    return texto_crudo


def limpiar_texto(texto_crudo):
    texto = texto_crudo.replace('\n', ' ')
    texto = re.sub(r'-\s+', '', texto)          # reúne palabras cortadas con guion de salto de línea
    texto = re.sub(r'\s+', ' ', texto).strip()  # colapsa espacios/dobles espacios
    return texto


def segmentar_en_oraciones(texto):
    oraciones = re.split(r'(?<=[.!?])\s+', texto)
    return [o.strip() for o in oraciones if o.strip()]


def generar_fragmentos_candidatos(oraciones, min_palabras=MIN_PALABRAS, max_palabras=MAX_PALABRAS):
    """Agrupa oraciones consecutivas hasta alcanzar el rango de palabras deseado."""
    candidatos = []
    buffer, conteo = [], 0
    for oracion in oraciones:
        buffer.append(oracion)
        conteo += len(oracion.split())
        if conteo >= min_palabras:
            fragmento = ' '.join(buffer)
            n_palabras = len(fragmento.split())
            if min_palabras <= n_palabras <= max_palabras:
                candidatos.append(fragmento)
            buffer, conteo = [], 0
    return candidatos


def hash_fragmento(fragmento):
    return hashlib.sha256(fragmento.encode('utf-8')).hexdigest()[:16]


def cargar_historial():
    if os.path.exists(HISTORIAL_PATH):
        with open(HISTORIAL_PATH, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()


def guardar_historial(historial):
    os.makedirs(os.path.dirname(HISTORIAL_PATH), exist_ok=True)
    with open(HISTORIAL_PATH, 'w', encoding='utf-8') as f:
        json.dump(sorted(historial), f, ensure_ascii=False, indent=2)


def dividir_superior_inferior(fragmento, minimo_para_dividir=MINIMO_PARA_DIVIDIR):
    palabras = fragmento.upper().split()
    if len(palabras) < minimo_para_dividir:
        return fragmento.upper(), ""
    mitad = len(palabras) // 2
    return ' '.join(palabras[:mitad]), ' '.join(palabras[mitad:])


def obtener_fragmentos(cantidad):
    """
    Punto de entrada del módulo. Devuelve una lista de `cantidad` tuplas
    (texto_superior, texto_inferior), sin repetir fragmentos ya usados.
    Si el pool de fragmentos únicos se agota, reinicia el historial
    (política explícita — ver Documento Maestro, sección 3.5).
    """
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(
            f"No se encontró el PDF en '{PDF_PATH}'. Verifica que el archivo "
            f"esté en /pdf_source/ y que PDF_SOURCE_PATH apunte ahí."
        )

    texto_limpio = limpiar_texto(cargar_texto_pdf(PDF_PATH))
    oraciones = segmentar_en_oraciones(texto_limpio)
    candidatos = generar_fragmentos_candidatos(oraciones)

    if not candidatos:
        raise RuntimeError("El PDF no produjo ningún fragmento válido de 10 a 25 palabras.")

    historial = cargar_historial()
    disponibles = [c for c in candidatos if hash_fragmento(c) not in historial]

    if len(disponibles) < cantidad:
        print(f"⚠️ Pool de fragmentos agotado ({len(disponibles)} disponibles, se necesitan {cantidad}) — reiniciando historial.")
        historial = set()
        disponibles = candidatos

    seleccionados = random.sample(disponibles, min(cantidad, len(disponibles)))
    for frag in seleccionados:
        historial.add(hash_fragmento(frag))
    guardar_historial(historial)

    return [dividir_superior_inferior(f) for f in seleccionados]


if __name__ == "__main__":
    # Modo de prueba manual: python modulos/pdf_extractor.py
    for arriba, abajo in obtener_fragmentos(3):
        print(f"ARRIBA: {arriba}\nABAJO: {abajo}\n---")

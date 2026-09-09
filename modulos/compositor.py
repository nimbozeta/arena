"""
Módulo de Composición Visual (Pillow)
Ubicación en el repositorio: /modulos/compositor.py

Responsabilidad única: fusionar una imagen base + texto superior/inferior
en un único archivo PNG, ANTES de que nada se suba a Are.na.

Este módulo reintegra la "Fase 3: Fusión Visual" del documento de
arquitectura original. En el pivote a Are.na se había delegado esta
tarea al navegador (JavaScript, en index.html), lo que dejaba imagen y
texto como dos bloques sueltos sin ningún vínculo garantizado entre
ellos. Ahora el vínculo se hace aquí, una sola vez, antes de subir nada.
"""
from PIL import Image, ImageDraw, ImageFont
import os

FUENTE_PATH = os.environ.get('FONT_PATH', 'assets/LiberationSans-Bold.ttf')
ANCHO, ALTO = 1920, 1080
MARGEN = 40


def normalizar_lienzo(imagen):
    return imagen.convert('RGB').resize((ANCHO, ALTO))


def calcular_fuente_ajustada(draw, texto, ancho_max, tamano_inicial=90, minimo=30):
    """Reduce el tamaño de fuente hasta que el texto entre en el ancho disponible."""
    tamano = tamano_inicial
    while tamano > minimo:
        fuente = ImageFont.truetype(FUENTE_PATH, tamano)
        bbox = draw.textbbox((0, 0), texto, font=fuente)
        if (bbox[2] - bbox[0]) <= ancho_max:
            return fuente
        tamano -= 4
    return ImageFont.truetype(FUENTE_PATH, minimo)


def dibujar_texto_con_contorno(draw, texto, y, fuente, ancho_lienzo, grosor=3):
    """Contorno rígido (sin difuminar) — el estilo definido desde el primer documento de arquitectura."""
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    x = (ancho_lienzo - (bbox[2] - bbox[0])) / 2
    for dx in range(-grosor, grosor + 1):
        for dy in range(-grosor, grosor + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), texto, font=fuente, fill='black')
    draw.text((x, y), texto, font=fuente, fill='white')


def componer_meme(ruta_imagen_entrada, texto_superior, texto_inferior, ruta_salida):
    """
    Entrada:  ruta de una imagen base + texto_superior + texto_inferior (puede venir vacío)
    Salida:   un archivo PNG en ruta_salida, con el texto ya incrustado en la imagen
    """
    imagen = normalizar_lienzo(Image.open(ruta_imagen_entrada))
    draw = ImageDraw.Draw(imagen)
    ancho_disponible = ANCHO - 2 * MARGEN

    if texto_superior:
        fuente = calcular_fuente_ajustada(draw, texto_superior, ancho_disponible)
        dibujar_texto_con_contorno(draw, texto_superior, MARGEN, fuente, ANCHO)

    if texto_inferior:
        fuente = calcular_fuente_ajustada(draw, texto_inferior, ancho_disponible)
        bbox = draw.textbbox((0, 0), texto_inferior, font=fuente)
        y = ALTO - MARGEN - (bbox[3] - bbox[1]) - 20
        dibujar_texto_con_contorno(draw, texto_inferior, y, fuente, ANCHO)

    imagen.save(ruta_salida, 'PNG')
    return ruta_salida

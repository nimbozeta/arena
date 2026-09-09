import os
import time
import random
import requests
import tempfile
import sys

from pdf_extractor import obtener_fragmentos
from compositor import componer_meme

# ==============================================================
# CONFIGURACIÓN
# ==============================================================
ARENA_TOKEN = os.environ.get('ARENA_WRITE_TOKEN')
CHANNEL_SLUG = os.environ.get('CHANNEL_SLUG', 'mi-canal-prueba')
LIMIT = 50
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
MIN_SUCCESSFUL_UPLOADS = 25

# ==============================================================
# FUNCIONES DE UTILIDAD (reintentos, descarga, subida)
# ==============================================================
def request_with_retry(method, url, **kwargs):
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, timeout=15, **kwargs)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"Error de servidor {resp.status_code}")
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            last_exception = e
            wait = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(f"   ⚠️ Intento {attempt}/{MAX_RETRIES} falló ({e}). Reintentando en {wait}s...")
            time.sleep(wait)
    raise last_exception


def descargar_imagen(url):
    """Descarga una imagen desde una URL y la guarda en un archivo temporal."""
    resp = request_with_retry('GET', url)
    resp.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


def subir_archivo_a_arena(channel_id, file_path, token):
    """
    Sube un archivo local (PNG/JPEG) a Are.na usando multipart/form-data.
    """
    url = f"https://api.are.na/v2/channels/{channel_id}/blocks"
    headers = {'Authorization': f'Bearer {token}'}
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'image/png')}
        resp = request_with_retry('POST', url, headers=headers, files=files)
    resp.raise_for_status()
    return resp.json()


def validate_write_scope(slug, token):
    url = f"https://api.are.na/v2/channels/{slug}"
    headers = {'Authorization': f'Bearer {token}'}
    resp = request_with_retry('GET', url, headers=headers)
    scope = resp.headers.get('X-Auth-Scope')
    print(f"🔍 GET /channels/{slug} -> {resp.status_code} | X-Auth-Scope: {scope}")
    if resp.status_code != 200:
        raise RuntimeError(f"No se pudo leer el canal (status {resp.status_code}).")
    if scope != 'write':
        raise RuntimeError(
            f"El token no tiene alcance de escritura (X-Auth-Scope='{scope}'). "
            f"Genera un token NUEVO con permiso de escritura explícito."
        )
    return resp.json()['id']


def get_channel_blocks(slug, token):
    url = f"https://api.are.na/v2/channels/{slug}?per=100"
    headers = {'Authorization': f'Bearer {token}'}
    resp = request_with_retry('GET', url, headers=headers)
    resp.raise_for_status()
    return resp.json().get('contents', [])


def delete_block(block_id, token):
    url = f"https://api.are.na/v2/blocks/{block_id}"
    headers = {'Authorization': f'Bearer {token}'}
    resp = request_with_retry('DELETE', url, headers=headers)
    resp.raise_for_status()


# ==============================================================
# FLUJO PRINCIPAL
# ==============================================================
def main():
    if not ARENA_TOKEN:
        print("❌ Error: ARENA_WRITE_TOKEN no está configurado.")
        return 1

    print(f"🚀 Iniciando actualización diaria para el canal: {CHANNEL_SLUG}")

    # 1. Validar token
    try:
        channel_id = validate_write_scope(CHANNEL_SLUG, ARENA_TOKEN)
        print(f"✅ Token validado. ID del canal: {channel_id}")
    except RuntimeError as e:
        print(f"❌ {e}")
        print("🛑 Abortando SIN tocar el canal.")
        return 1

    # 2. Obtener fragmentos de texto del PDF
    try:
        print("📄 Extrayendo fragmentos de texto del PDF...")
        fragmentos = obtener_fragmentos(LIMIT)  # Devuelve lista de tuplas (superior, inferior)
        print(f"✅ Se obtuvieron {len(fragmentos)} fragmentos.")
    except Exception as e:
        print(f"❌ Error al extraer texto del PDF: {e}")
        print("🛑 Abortando para no subir imágenes sin texto.")
        return 1

    if len(fragmentos) < LIMIT:
        print(f"⚠️ Solo se obtuvieron {len(fragmentos)} fragmentos, pero se necesitan {LIMIT}. Continuando con los disponibles.")
        LIMIT_EFECTIVO = len(fragmentos)
    else:
        LIMIT_EFECTIVO = LIMIT

    # 3. Para cada fragmento, generar una imagen compuesta y subirla
    print(f"📸 Generando {LIMIT_EFECTIVO} imágenes compuestas desde Picsum + texto del PDF...")
    nuevas_subidas = []

    for i in range(LIMIT_EFECTIVO):
        try:
            # 3a. Descargar imagen de Picsum
            img_url = f"https://picsum.photos/seed/{random.randint(1, 100000)}/1920/1080"
            print(f"   [{i+1}/{LIMIT_EFECTIVO}] Descargando imagen...")
            img_temp = descargar_imagen(img_url)

            # 3b. Obtener texto superior/inferior
            top, bottom = fragmentos[i]

            # 3c. Componer meme
            print(f"   [{i+1}/{LIMIT_EFECTIVO}] Componiendo meme...")
            salida_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            salida_temp.close()
            componer_meme(img_temp, top, bottom, salida_temp.name)

            # 3d. Subir a Are.na
            print(f"   [{i+1}/{LIMIT_EFECTIVO}] Subiendo a Are.na...")
            resultado = subir_archivo_a_arena(channel_id, salida_temp.name, ARENA_TOKEN)
            nuevas_subidas.append(resultado['id'])
            print(f"   ✅ Imagen compuesta subida (block_id: {resultado['id']})")

            # Limpiar archivos temporales
            os.unlink(img_temp)
            os.unlink(salida_temp.name)

            time.sleep(0.3)  # evitar límite de tasa

        except Exception as e:
            print(f"   ❌ Falló procesamiento del elemento {i+1}: {e}")
            # No detenemos todo, continuamos con el siguiente

    print(f"✅ {len(nuevas_subidas)} imágenes compuestas subidas exitosamente.")

    if len(nuevas_subidas) < MIN_SUCCESSFUL_UPLOADS:
        print(f"🛑 Solo se subieron {len(nuevas_subidas)} (mínimo {MIN_SUCCESSFUL_UPLOADS}). NO se borra nada viejo.")
        return 1

    # 4. Borrar bloques antiguos (los que no son los que acabamos de subir)
    try:
        all_blocks = get_channel_blocks(CHANNEL_SLUG, ARENA_TOKEN)
        ids_nuevos = set(nuevas_subidas)
        bloques_a_borrar = [b for b in all_blocks if b['id'] not in ids_nuevos]
        print(f"🧹 Eliminando {len(bloques_a_borrar)} bloques antiguos...")
        for block in bloques_a_borrar:
            try:
                delete_block(block['id'], ARENA_TOKEN)
                print(f"   🗑️ Eliminado {block['id']}")
            except Exception as e:
                print(f"   ⚠️ No se pudo eliminar {block['id']}: {e}")
            time.sleep(0.3)
    except Exception as e:
        print(f"⚠️ No se pudo leer el canal para limpiar: {e}")

    print("🎉 Ciclo diario completado.")
    print(f"RESUMEN::{len(nuevas_subidas)}/{LIMIT_EFECTIVO} imágenes compuestas subidas")
    return 0


if __name__ == "__main__":
    exit(main())

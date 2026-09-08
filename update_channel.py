import os
import requests
import json
import random
from datetime import datetime, timezone

# ==============================================================
# CONFIGURACIÓN (tomada de variables de entorno en GitHub Actions)
# ==============================================================
ARENA_TOKEN = os.environ.get('ARENA_WRITE_TOKEN')
CHANNEL_SLUG = os.environ.get('CHANNEL_SLUG', 'mi-canal-prueba')
LIMIT = 50  # Número de imágenes a subir

# ==============================================================
# 1. GENERAR IMÁGENES DESDE PICSUM (sin autenticación)
# ==============================================================
def fetch_images_from_picsum(count=50):
    """
    Genera URLs de imágenes aleatorias de Lorem Picsum.
    Usa diferentes semillas para obtener imágenes distintas.
    """
    image_urls = []
    # Generamos semillas aleatorias únicas
    seeds = random.sample(range(1, 100000), count)
    for seed in seeds:
        # Tamaño fijo 1920x1080, pero puedes ajustarlo
        url = f"https://picsum.photos/seed/{seed}/1920/1080"
        image_urls.append(url)
    return image_urls

# ==============================================================
# 2. CONECTAR CON ARENA (leer, eliminar, subir)
# ==============================================================
def get_channel_id(slug, token):
    """Obtiene el ID interno del canal a partir del slug."""
    url = f"https://api.are.na/v2/channels/{slug}"
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data['id']

def get_channel_blocks(slug, token):
    """Obtiene todos los bloques actuales del canal."""
    url = f"https://api.are.na/v2/channels/{slug}?per=100"
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data.get('contents', [])

def delete_block(block_id, token):
    """Elimina un bloque específico de Are.na."""
    url = f"https://api.are.na/v2/blocks/{block_id}"
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    print(f"   🗑️ Eliminado bloque {block_id}")

def upload_image_to_channel(channel_id, image_url, token):
    """Sube una imagen (por URL) al canal de Are.na."""
    url = f"https://api.are.na/v2/channels/{channel_id}/blocks"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = json.dumps({"source": image_url})
    resp = requests.post(url, headers=headers, data=payload)
    resp.raise_for_status()
    print(f"   ✅ Subida: {image_url[:60]}...")

# ==============================================================
# 3. FLUJO PRINCIPAL
# ==============================================================
def main():
    if not ARENA_TOKEN:
        print("❌ Error: ARENA_WRITE_TOKEN no está configurado.")
        return 1

    print(f"🚀 Iniciando actualización diaria para el canal: {CHANNEL_SLUG}")
    
    # 3.1 Generar imágenes (usando Picsum)
    print(f"📸 Generando {LIMIT} imágenes desde Picsum...")
    new_images = fetch_images_from_picsum(LIMIT)
    
    if len(new_images) < 10:
        print(f"⚠️ Solo se generaron {len(new_images)} imágenes. Se necesitan al menos 10 para continuar.")
        return 1
    
    print(f"✅ Se generaron {len(new_images)} imágenes.")
    
    # 3.2 Obtener ID del canal
    try:
        channel_id = get_channel_id(CHANNEL_SLUG, ARENA_TOKEN)
        print(f"📡 ID del canal: {channel_id}")
    except Exception as e:
        print(f"❌ Error al obtener el canal: {e}")
        return 1
    
    # 3.3 Obtener bloques actuales
    try:
        current_blocks = get_channel_blocks(CHANNEL_SLUG, ARENA_TOKEN)
        print(f"📦 Bloques actuales en el canal: {len(current_blocks)}")
    except Exception as e:
        print(f"❌ Error al leer bloques: {e}")
        return 1
    
    # 3.4 Eliminar TODOS los bloques existentes
    if current_blocks:
        print(f"🧹 Eliminando {len(current_blocks)} bloques antiguos...")
        for block in current_blocks:
            try:
                delete_block(block['id'], ARENA_TOKEN)
            except Exception as e:
                print(f"   ⚠️ No se pudo eliminar {block['id']}: {e}")
    else:
        print("✅ El canal ya estaba vacío.")
    
    # 3.5 Subir las nuevas imágenes
    print(f"⬆️ Subiendo {len(new_images)} imágenes al canal...")
    success_count = 0
    for idx, img_url in enumerate(new_images):
        try:
            upload_image_to_channel(channel_id, img_url, ARENA_TOKEN)
            success_count += 1
        except Exception as e:
            print(f"   ❌ Falló subida {idx+1}: {e}")
    
    print(f"🎉 Proceso completado. {success_count} imágenes subidas exitosamente.")
    return 0

if __name__ == "__main__":
    exit(main())

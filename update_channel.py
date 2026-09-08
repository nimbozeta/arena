import os
import requests
import json
import random
from datetime import datetime, timezone

# ==============================================================
# CONFIGURACIÓN (tomada de variables de entorno en GitHub Actions)
# ==============================================================
ARENA_TOKEN = os.environ.get('ARENA_WRITE_TOKEN')
CHANNEL_SLUG = os.environ.get('CHANNEL_SLUG', 'mi-canal-prueba')  # Reemplaza o usa secret
REDDIT_SUBREDDIT = os.environ.get('REDDIT_SUBREDDIT', 'wallpaper')
LIMIT = 50  # Número de imágenes a obtener y subir

# ==============================================================
# 1. OBTENER IMÁGENES DE REDDIT (usando JSON público)
# ==============================================================
import xml.etree.ElementTree as ET

def fetch_reddit_images(subreddit, limit=50):
    """
    Obtiene URLs de imágenes de un subreddit usando su feed RSS.
    No requiere autenticación y evita el bloqueo 403.
    """
    # Usamos el feed RSS del subreddit (hot)
    url = f"https://www.reddit.com/r/{subreddit}/.rss"
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; Bot/1.0)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parsear el XML del feed RSS
        root = ET.fromstring(response.content)
        
        # Namespace de RSS
        ns = {'': 'http://www.w3.org/2005/Atom'}
        
        image_urls = []
        for entry in root.findall('.//entry', ns):
            # Buscar enlaces dentro del contenido HTML de la entrada
            content = entry.find('content', ns)
            if content is not None and content.text:
                # Buscar URLs de imágenes en el contenido HTML
                # Patrón simple: buscar src="..." que apunte a i.redd.it o external-preview
                import re
                img_pattern = r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"'
                found = re.findall(img_pattern, content.text)
                for img_url in found:
                    # Limpiar URLs (eliminar parámetros extra)
                    img_url = img_url.split('?')[0]
                    if img_url not in image_urls:
                        image_urls.append(img_url)
        
        return image_urls[:limit]
    
    except Exception as e:
        print(f"❌ Error al obtener imágenes desde RSS: {e}")
        return []
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
    # La API permite subir por URL usando "source"
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
    
    # 3.1 Obtener imágenes de Reddit
    print(f"📸 Buscando {LIMIT} imágenes en r/{REDDIT_SUBREDDIT}...")
    new_images = fetch_reddit_images(REDDIT_SUBREDDIT, LIMIT)
    
    if len(new_images) < 10:
        print(f"⚠️ Solo se encontraron {len(new_images)} imágenes. Se necesitan al menos 10 para continuar.")
        return 1
    
    print(f"✅ Se obtuvieron {len(new_images)} imágenes válidas.")
    
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
    
    # 3.4 Decisión de limpieza: Eliminar TODOS los bloques actuales
    #     (así el tablero siempre tiene exactamente las últimas 50 imágenes).
    #     Si prefieres eliminar solo los más antiguos, cambia esta lógica.
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

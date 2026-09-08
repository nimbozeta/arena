import os
import requests

TOKEN = os.environ.get('ARENA_WRITE_TOKEN')
SLUG = os.environ.get('CHANNEL_SLUG', 'mi-canal-prueba')

def test_write_permission():
    if not TOKEN:
        print("❌ Token no encontrado")
        return
    
    # 1. Obtener el ID del canal
    url = f"https://api.are.na/v2/channels/{SLUG}"
    headers = {'Authorization': f'Bearer {TOKEN}'}
    resp = requests.get(url, headers=headers)
    print(f"🔍 GET /channels/{SLUG} -> {resp.status_code}")
    print(f"🔍 X-Auth-Scope: {resp.headers.get('X-Auth-Scope')}")
    
    if resp.status_code != 200:
        print("❌ Error al obtener el canal")
        return
    
    channel_id = resp.json()['id']
    print(f"✅ Channel ID: {channel_id}")
    
    # 2. Intentar subir un bloque de prueba (usando una imagen pública)
    test_url = "https://picsum.photos/seed/test/800/600"
    post_url = f"https://api.are.na/v2/channels/{channel_id}/blocks"
    payload = {"source": test_url}
    resp2 = requests.post(post_url, headers=headers, json=payload)
    print(f"🔍 POST /channels/{channel_id}/blocks -> {resp2.status_code}")
    print(f"🔍 Respuesta: {resp2.text[:200]}")
    
    if resp2.status_code == 201:
        print("✅ ¡El token tiene permisos de escritura!")
        # Eliminar el bloque de prueba (opcional)
        block_id = resp2.json()['id']
        delete_url = f"https://api.are.na/v2/blocks/{block_id}"
        requests.delete(delete_url, headers=headers)
        print("🧹 Bloque de prueba eliminado")
    else:
        print("❌ El token NO tiene permisos de escritura. Revisa los permisos en Are.na.")

if __name__ == "__main__":
    test_write_permission()


from ditupy.ditu import DituClient

client = DituClient()

# 1. Buscar canal
canal = client.find_channel("desafio")

# 3. Obtener URL para grabar
manifest_url = client.get_manifest_url(canal["channelId"])

print(f"Manifest URL: {manifest_url}")
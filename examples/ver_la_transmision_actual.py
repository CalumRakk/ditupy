import os
import sys

sys.path.append(os.getcwd())

from ditupy.ditu import DituClient

client = DituClient()

# 1. Buscar canal
canal = client.find_channel("desafio")

programa_actual = client.get_current_live_program(canal["channelId"])
print(f"Viendo: {programa_actual.title}")

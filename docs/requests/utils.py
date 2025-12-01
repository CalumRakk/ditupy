import json
import os
from pathlib import Path
from urllib.parse import urlparse


def save_api_response(url: str, data: dict, base_dir: str = "../api_samples"):
    """
    Guarda la respuesta JSON replicando la estructura de carpetas de la URL.
    Ej: .../PAGE/402 -> docs/api_samples/PAGE/402.json

    - Se asume que este script corre desde docs/requests/
    """
    parsed = urlparse(url)

    # 1. Limpiamos la ruta para quitar la parte común que no aporta info (/AGL/1.6/...)
    # Asumimos que lo interesante empieza después de /ALL/
    clean_path = parsed.path.split("/ALL/")[-1]

    # Si la URL tiene query params (?filter=...), se agrega al nombre para no perder contexto
    if parsed.query:
        safe_query = parsed.query.replace("=", "_").replace("&", "-")
        filename = f"{os.path.basename(clean_path)}_{safe_query}.json"
        folder_path = os.path.dirname(clean_path)
    else:
        filename = f"{os.path.basename(clean_path)}.json"
        folder_path = os.path.dirname(clean_path)

    # 2. Construir ruta absoluta
    output_dir = Path(__file__).parent / base_dir / folder_path
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / filename
    output_file.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Guardado en: {folder_path}/{filename}")
    return output_file

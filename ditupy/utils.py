import logging
import re
from time import sleep
from typing import Dict
from urllib.parse import unquote

logger = logging.getLogger(__name__)


def cookies_to_requests(raw: str, unquote_value=True) -> Dict[str, str]:
    """
    Convierte un header Cookie o Set-Cookie en un dict simple para requests. Esto implica unquote de los valores.

    Args:
        unquote_value (bool, optional): Decodificar los valores con unquote. Defaults to True.
    """
    cookies = {}
    # Dividir por coma solo cuando empieza una nueva cookie (key=...)
    parts = [p.strip() for p in raw.split(",")]
    for part in parts:
        segments = [s.strip() for s in part.split(";")]
        if "=" in segments[0]:
            name, value = segments[0].split("=", 1)
            cookies[name] = unquote(value) if unquote_value else value  # decodifica %xx
    return cookies


def normalize_windows_name(name: str) -> str:
    invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
    name = re.sub(invalid_chars, "_", name)
    name = name.rstrip(" .")
    if len(name) < 0:
        raise ValueError("Invalid name")
    return name


def sleep_progress(seconds: float):
    total = int(seconds)
    if total <= 0:
        return

    logger.info(
        f"Esperando {total // 60} minutos y {total % 60} segundos antes de continuar..."
    )

    for i in range(total, 0, -1):
        sleep(1)
        if i % 60 == 0:
            mins_left = i // 60
            logger.info(f"Faltan {mins_left} minutos...")
        elif i <= 10:  # Mostrar segundos finales
            logger.info(f"{i} segundos restantes...")

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class SegmentDownloader:
    def __init__(self, output_dir: Union[Path, str], max_workers: int = 4):
        output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir

        self.output_dir = output_dir
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "okhttp/4.12.0", "Accept-Encoding": "gzip, deflate, br"}
        )

    def download_file(self, url: str, subdir: str = "") -> bool:
        """Descarga un archivo si no existe. Retorna True si se descargó."""
        filename = Path(urlparse(url).path).name
        target_dir = self.output_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename

        if target_path.exists():
            return False

        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            target_path.write_bytes(resp.content)
            return True
        except Exception as e:
            logger.error(f"Fallo descargando {filename}: {e}")
            return False

    def download_batch(self, urls: list[str], subdir: str = ""):
        """Descarga una lista de URLs en paralelo."""
        if not urls:
            return

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.download_file, url, subdir) for url in urls]
            for f in futures:
                f.result()

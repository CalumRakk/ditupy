import json
import logging
from pathlib import Path
from typing import Union

import requests

from ditupy.dash import DashManifest
from ditupy.schemas.types import Manifest
from ditupy.services.downloader import SegmentDownloader

logger = logging.getLogger(__name__)


class VodDownloader:
    def __init__(
        self,
        manifest: Manifest,
        output_path: Union[Path, str],
    ):
        """
        :param manifest: Objeto Manifest obtenido de client.get_stream_url()
        :param output_path: Ruta base donde se guardará el contenido
        """
        self.output_path = (
            Path(output_path) if isinstance(output_path, str) else output_path
        )
        self.manifest_data = manifest
        self.downloader = SegmentDownloader(self.output_path, max_workers=8)

    def _save_metadata(self, xml_content: str):
        """
        Guarda los datos necesarios trabajar con el DRM.
        """
        # Guardar el Manifiesto crudo (.mpd)
        # Es necesario para extraer el PSSH.
        mpd_path = self.output_path / "manifest.mpd"
        mpd_path.write_text(xml_content, encoding="utf-8")
        logger.info(f"Manifiesto guardado en: {mpd_path}")

        # Guardar Token y URL del servidor de licencias
        # TODO: conseguir la URL del servidor de licencias y guardarla junto aqui. Esta suele ser estatica.
        meta_data = {
            "manifest_url": self.manifest_data.src,
            "token": self.manifest_data.token,
            "license_type": "com.widevine.alpha",
            "license_url": "",
        }

        meta_path = self.output_path / "drm_info.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=4)

        logger.info(f"Metadatos DRM guardados en: {meta_path}")

    def download(self) -> Path:
        self.output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"--- PASO 1: Obtención del Manifiesto ---")
        logger.info(f"URL: {self.manifest_data.src}")

        try:
            resp = requests.get(self.manifest_data.src)
            resp.raise_for_status()
            xml_content = resp.text
            logger.debug(
                "Manifiesto descargado correctamente (tamaño: %d bytes)",
                len(xml_content),
            )
        except Exception as e:
            logger.error(f"Error fatal obteniendo manifiesto: {e}")
            raise e

        logger.info(f"--- PASO 2: Persistencia de Metadatos DRM ---")
        self._save_metadata(xml_content)

        logger.info(f"--- PASO 3: Análisis DASH y Selección ---")
        dash = DashManifest(xml_content, source_url=self.manifest_data.src)
        period = dash.get_content_period()

        # Seleccionar mejores representaciones
        video_sets = period.get_adaptation_sets(type_filter="video")
        audio_sets = period.get_adaptation_sets(type_filter="audio")

        if not video_sets or not audio_sets:
            msg = "El manifiesto no contiene pistas de video o audio válidas."
            logger.error(msg)
            raise ValueError(msg)

        video_rep = video_sets[0].get_best_representation()
        audio_rep = audio_sets[0].get_best_representation()

        if not audio_rep or not video_rep:
            msg = "Fallo en la selección de representaciones."
            logger.error(msg)
            raise ValueError(msg)

        logger.info(f"--- PASO 4: Descarga de Segmentos ---")

        # Descargar inits
        logger.info("Descargando segmentos de inicialización (init.mp4)...")
        self.downloader.download_file(video_rep.initialization_url, "video")
        self.downloader.download_file(audio_rep.initialization_url, "audio")

        # Descargar segmentos
        video_segments = video_rep.get_segments()
        audio_segments = audio_rep.get_segments()

        logger.info(
            f"Cola de descarga: Video ({len(video_segments)} segmentos) + Audio ({len(audio_segments)} segmentos)"
        )

        self.downloader.download_batch(video_segments, "video")
        self.downloader.download_batch(audio_segments, "audio")

        logger.info(f"--- PROCESO FINALIZADO ---")
        logger.info(f"Contenido guardado en: {self.output_path}")
        return self.output_path

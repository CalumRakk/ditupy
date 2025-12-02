# archivo: ditupy/vod_recorder.py

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
        :param output_path: Ruta base donde se guardará el contenido (ej: downloads/Nombre_Capitulo)
        """
        self.output_path = (
            Path(output_path) if isinstance(output_path, str) else output_path
        )
        self.manifest_url = manifest.src
        # TODO: Acopla esta logica hasta que realmente se justique inyectarla.
        self.downloader = SegmentDownloader(self.output_path, max_workers=8)

    def download(self) -> Path:
        logger.info(f"Iniciando descarga VOD desde: {self.manifest_url}")
        try:
            resp = requests.get(self.manifest_url)
            resp.raise_for_status()
            xml_content = resp.text
        except Exception as e:
            logger.error(f"Error obteniendo manifiesto: {e}")
            raise e

        dash = DashManifest(xml_content, source_url=self.manifest_url)

        period = dash.get_content_period()

        # Seleccionar mejores representaciones (Video y Audio)
        video_sets = period.get_adaptation_sets(type_filter="video")
        audio_sets = period.get_adaptation_sets(type_filter="audio")

        if not video_sets or not audio_sets:
            logger.error("No se encontraron pistas de video o audio en el manifiesto.")
            raise ValueError(
                "No se encontraron pistas de video o audio en el manifiesto."
            )

        video_rep = video_sets[0].get_best_representation()
        audio_rep = audio_sets[0].get_best_representation()
        if not audio_rep or not video_rep:
            logger.error("No se encontraron representaciones de video o audio.")
            raise ValueError("No se encontraron representaciones de video o audio.")

        logger.info(
            f"Calidad seleccionada: Video {video_rep.height}p | Audio {audio_rep.bandwidth}bps"
        )

        # Descargar segmentos de inicialización (init.mp4)
        logger.info("Descargando segmentos de inicialización...")
        self.downloader.download_file(video_rep.initialization_url, "video")
        self.downloader.download_file(audio_rep.initialization_url, "audio")

        # Generar lista completa de segmentos
        logger.info("Calculando segmentos...")
        video_segments = video_rep.get_segments()
        audio_segments = audio_rep.get_segments()

        logger.info(
            f"Total segmentos a descargar: Video: {len(video_segments)} | Audio: {len(audio_segments)}"
        )

        # Descarga masiva en paralelo
        self.downloader.download_batch(video_segments, "video")
        self.downloader.download_batch(audio_segments, "audio")

        logger.info("Descarga de segmentos finalizada.")
        return self.output_path

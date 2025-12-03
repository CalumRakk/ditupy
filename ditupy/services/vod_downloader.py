import logging
from pathlib import Path
from typing import Optional

import requests

from ditupy.dash import DashManifest, Representation
from ditupy.schemas.types import DRMInfo, Manifest, StreamInfo
from ditupy.services.downloader import SegmentDownloader

logger = logging.getLogger(__name__)


class VodDownloader:
    def __init__(self, manifest: Manifest):
        """
        :param manifest: Objeto Manifest obtenido de client.get_stream_url()
        :param output_path: Ruta base donde se guardará el contenido
        """
        self.manifest_data = manifest

        # Estado interno para no parsear dos veces
        self._dash: Optional[DashManifest] = None
        self._video_rep: Optional[Representation] = None
        self._audio_rep: Optional[Representation] = None
        self._xml_content: Optional[str] = None
        self._pssh: Optional[str] = None

    def extract_info(self) -> StreamInfo:
        """
        Descarga el manifiesto, lo analiza y selecciona las mejores pistas y devuelve StreamInfo.
        """
        logger.info(f"--- Analizando Manifiesto ---")

        if not self._xml_content:
            resp = requests.get(self.manifest_data.src)
            resp.raise_for_status()
            self._xml_content = resp.text

        self._dash = DashManifest(self._xml_content, source_url=self.manifest_data.src)
        period = self._dash.get_content_period()

        video_sets = period.get_adaptation_sets(type_filter="video")
        audio_sets = period.get_adaptation_sets(type_filter="audio")
        if not video_sets or not audio_sets:
            raise ValueError("El manifiesto no contiene pistas válidas.")

        self._video_rep = video_sets[0].get_best_representation()
        self._audio_rep = audio_sets[0].get_best_representation()
        if not self._video_rep or not self._audio_rep:
            raise ValueError("Fallo seleccionando calidades.")

        protection_widevine = [
            i
            for i in self._video_rep.get_content_protections()
            if "edef8ba9" in i.scheme_id_uri.lower()
        ]
        if not protection_widevine:
            # Intentar buscar en el AdaptationSet si no está en la Representation
            protection_widevine = [
                i
                for i in video_sets[0].get_content_protections()
                if "edef8ba9" in i.scheme_id_uri.lower()
            ]

        if protection_widevine:
            self._pssh = protection_widevine[0].pssh
        else:
            logger.warning(
                "No se encontró PSSH de Widevine. El video no se podrá reproducir."
            )
            self._pssh = ""

        logger.info(
            f"Calidad seleccionada: {self._video_rep.height}p ({self._video_rep.bandwidth} bps)"
        )

        return StreamInfo(
            height=self._video_rep.height if self._video_rep.height else 0,
            width=self._video_rep.width,
            duration=self._dash.duration_seconds,
            pssh=self._pssh,
        )

    def _save_metadata(self, output_path: Path):
        """
        Guarda los datos necesarios trabajar con el DRM.
        """
        # Guardar el Manifiesto crudo (.mpd)
        # Es necesario para extraer el PSSH.
        mpd_path = output_path / "manifest.mpd"
        mpd_path.write_text(self._xml_content, encoding="utf-8")  # type: ignore

        meta_data = DRMInfo(
            manifest_url=self.manifest_data.src,
            token=self.manifest_data.token,
            cookies=self.manifest_data.cookies,
            pssh_widevine=self._pssh if self._pssh else "",
        )
        meta_path = output_path / "drm_info.json"
        meta_path.write_text(meta_data.model_dump_json(indent=4), encoding="utf-8")

        logger.info(f"Metadatos DRM guardados en: {meta_path}")

    def download(self, output_path: Path):
        """
        Ejecuta la descarga física de los segmentos.
        Requiere que extract_info() se haya ejecutado antes (o lo ejecuta si no).
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        if not self._video_rep:
            self.extract_info()

        # # TODO: Comprobar si realmente este acoplamiento es necesario o lo inyectamos en el constructor
        seg_downloader = SegmentDownloader(output_path, max_workers=8)

        logger.info(f"--- Guardando Metadatos ---")
        self._save_metadata(output_path)

        logger.info(f"--- Descargando Segmentos en: {output_path} ---")

        # Descargar inits
        seg_downloader.download_file(self._video_rep.initialization_url, "video")  # type: ignore
        seg_downloader.download_file(self._audio_rep.initialization_url, "audio")  # type: ignore

        # Descargar segmentos
        video_segments = self._video_rep.get_segments()  # type: ignore
        audio_segments = self._audio_rep.get_segments()  # type: ignore

        logger.info(
            f"Cola: Video ({len(video_segments)}) + Audio ({len(audio_segments)})"
        )
        seg_downloader.download_batch(video_segments, "video")
        seg_downloader.download_batch(audio_segments, "audio")

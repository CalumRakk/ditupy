import logging
import time
from pathlib import Path
from typing import Union

import requests

from ditupy.dash import DashManifest
from ditupy.downloader import SegmentDownloader
from ditupy.schemas.simple_schedule import SimpleSchedule

logger = logging.getLogger(__name__)

class LiveRecorder:
    def __init__(self,manifest_url:str,  schedule: SimpleSchedule, output_base: Union[Path, str]):
        self.schedule = schedule
        self.manifest_url = manifest_url
        output_base= Path(output_base) if isinstance(output_base, str) else output_base
        self.output_path = output_base / f"{schedule.title_slug}_{schedule.content_id}"
        self.downloader = SegmentDownloader(self.output_path)        

    def _is_content_period(self, manifest: DashManifest) -> bool:
        """Logica 'magica' para saber si es contenido o anuncio."""
        # Si solo hay 1 periodo, asumimos que es contenido (logica magica que deberia cambiarse)
        periods = manifest.get_periods()
        return len(periods) == 1

    def record(self):
        logger.info(f"Iniciando grabación: {self.schedule.title}")
        
        # 1. Esperar contenido real
        while True:
            try:
                xml = requests.get(self.manifest_url).text
                manifest = DashManifest(xml, source_url=self.manifest_url)
                
                if self._is_content_period(manifest):
                    break
                
                logger.info("Comerciales detectados... esperando.")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error obteniendo manifiesto: {e}")
                time.sleep(2)

        # 2. Configurar representaciones iniciales
        period = manifest.get_content_period()
        video_rep = period.get_adaptation_sets(type_filter="video")[0].get_best_representation()
        audio_rep = period.get_adaptation_sets(type_filter="audio")[0].get_best_representation()
        
        if not video_rep or not audio_rep:
            raise ValueError("No se encontraron representaciones de video o audio.")
        
        logger.info(f"Calidad seleccionada: Video {video_rep.height}p | Audio {audio_rep.bandwidth}")

        # Descargar inits       
        self.downloader.download_file(video_rep.initialization_url, "video")
        self.downloader.download_file(audio_rep.initialization_url, "audio")

        # 3. Bucle de captura principal
        for _ in range(5):
            start_loop = time.time()
            
            # Refrescar manifiesto
            xml = requests.get(self.manifest_url).text
            manifest = DashManifest(xml, source_url=self.manifest_url)
            period = manifest.get_content_period()
            # Asumo que el ID se mantiene o re-buscas por calidad.
            
            current_video = period.get_adaptation_sets(type_filter="video")[0].get_best_representation()
            current_audio = period.get_adaptation_sets(type_filter="audio")[0].get_best_representation()
            if not current_video or not current_audio:
                logger.warning("No se encontraron representaciones actuales. Saltando ciclo.")
                time.sleep(2)
                continue

            # Descargar segmentos en paralelo
            self.downloader.download_batch(current_video.get_segments(), "video")
            self.downloader.download_batch(current_audio.get_segments(), "audio")
            
            # Control de ciclo
            elapsed = time.time() - start_loop
            sleep_time = max(0, 4 - elapsed)
            time.sleep(sleep_time)

    def _should_stop(self) -> bool:
        return False
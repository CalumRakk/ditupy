from pathlib import Path

from ditupy.ditu import DituClient
from ditupy.logging_config import setup_logging
from ditupy.schemas.types import DRMInfo
from ditupy.services.license_manager import LicenseManager
from ditupy.services.processor import PostProcessor
from ditupy.services.vod_downloader import VodDownloader

setup_logging()

client = DituClient()
series = client.get_series()
device_path = "dumper-main/key_dumps/Android Emulator 5554/private_keys/4464/2137596953"
for serie in series:
    if "suite" in serie.metadata.title.lower():
        episodes = [
            i
            for i in client.get_episodes(serie_id=serie.id)
            if i.metadata.contentSubtype == "EPISODE"
        ]
        episodes.sort(key=lambda x: x.metadata.episodeNumber)  # type: ignore
        for episode in episodes:
            title = episode.title_slug
            episode_number = episode.metadata.episodeNumber

            manifest = client.get_stream_url(content_id=episode.metadata.contentId)

            downloader = VodDownloader(manifest=manifest)
            stream_info = downloader.extract_info()

            # Construir ruta
            folder_name = f"{title}.{episode.metadata.year}.capitulo.{str(episode_number).zfill(2)}.ditu.{stream_info.height}p"
            output_path = Path("downloads") / folder_name

            filename = f"{folder_name}.mp4"
            final_file = output_path / filename
            if final_file.exists():
                print(f"Saltando: {filename} (Ya existe)")
                continue

            print(f"Iniciando descarga de: {filename}")
            downloader.download(output_path=output_path)

            # Obtiene las Key de descifrado.
            drm_info_path = output_path / "drm_info.json"
            drm_info = DRMInfo.parse_file(drm_info_path)

            license_manager = LicenseManager(device_path=device_path)
            keys = license_manager.get_keys(drm_info)

            # Procesa los segmentos descargados/cifrados y los descifra si se proporcionan las keys.
            processor = PostProcessor(output_path)
            processor.process(filename, keys=keys)

            if processor.verify_integrity(final_file, stream_info.duration):
                print(f"Descargado y Verificado: {episode.metadata.title}")
            else:
                print(f"WARNING: Descarga incompleta para: {episode.metadata.title}")
                raise Exception("Descarga incompleta")

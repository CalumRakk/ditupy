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
    if "desafío" in serie.metadata.title.lower():
        episodes = client.get_episodes(serie_id=serie.id)
        for episode in episodes:
            title = episode.title_slug
            episode_number = episode.metadata.episodeNumber
            output_path = f"downloads/{title}_{episode_number}"

            manifest = client.get_stream_url(content_id=episode.metadata.contentId)
            downloader = VodDownloader(manifest=manifest, output_path=output_path)
            processor = PostProcessor(output_path)

            downloader.download()

            drm_info_path = Path(output_path) / "drm_info.json"
            drm_info = DRMInfo.parse_file(drm_info_path)

            license_manager = LicenseManager(device_path=device_path)
            keys = license_manager.get_keys(drm_info)

            processor = PostProcessor(output_path)
            filename = f"{title}_{episode_number}.mp4"
            processor.process(filename, keys=keys)

            print(f"Downloaded: {episode.metadata.title}")
            exit()

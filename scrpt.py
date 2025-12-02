from ditupy.ditu import DituClient
from ditupy.logging_config import setup_logging
from ditupy.services.processor import PostProcessor
from ditupy.services.vod_downloader import VodDownloader

setup_logging()

client = DituClient()
series = client.get_series()

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

            filename = f"{title}_{episode_number}.mp4"
            processor.process(filename)

            print(f"Downloaded: {episode.metadata.title}")
            exit()

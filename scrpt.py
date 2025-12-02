from ditupy.ditu import DituClient
from ditupy.services.vod_downloader import VodDownloader

client = DituClient()

series = client.get_series()

for serie in series:
    if "desafío" in serie.metadata.title.lower():
        episodes = client.get_episodes(serie_id=serie.id)
        for episode in episodes:
            manifest = client.get_stream_url(content_id=episode.metadata.contentId)
            downloader = VodDownloader(
                manifest=manifest, output_path=f"downloads/{episode.title_slug}"
            )
            downloader.download()
            print(f"Downloaded: {episode.metadata.title}")
            exit()

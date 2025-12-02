from ditupy.ditu import DituClient

client = DituClient()

series = client.get_series()

for serie in series:
    if "desafío" in serie.metadata.title.lower():
        episodes = client.get_episodes(serie_id=serie.id)
        for episode in episodes:
            manifest = client.get_stream_url(content_id=episode.metadata.contentId)
            print(manifest)

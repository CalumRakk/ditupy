from ditupy.ditu import DituClient

client = DituClient()

for i, programa in enumerate(client.get_catalog_iterator()):
    print(f"[{i}] {programa.title} (ID: {programa.contentId})")

    if "Desafío" in programa.title:
        print(f"¡ENCONTRADO! En colección {programa.source_collection_id}")

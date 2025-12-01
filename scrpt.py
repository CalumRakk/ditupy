from ditupy.ditu import DituClient
from ditupy.logging_config import setup_logging

setup_logging()

client = DituClient()
for collection in client.get_collections():
    print(f"Collection: {collection.layout}", collection.title)
    items = client.get_collection(collection)
    for item in items:
        print("\t" + item.metadata.title)
        data = client.get_item(item)
        print("\t\tData keys:", list(data.keys()))

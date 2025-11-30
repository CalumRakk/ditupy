import json
from pathlib import Path

import requests

headers = {
    "Restful": "yes",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "okhttp/4.12.0",
    "Connection": "keep-alive",
}

base_url = "https://varnish-prod.avscaracoltv.com"

url = f"{base_url}/AGL/1.6/A/ENG/ANDROID/ALL/TRAY/EXTCOLLECTION/2213"
resp = requests.get(url, headers=headers)

Path("tray_2213_collection.json").write_text(json.dumps(resp.json()))

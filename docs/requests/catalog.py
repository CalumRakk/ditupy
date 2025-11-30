import json
from pathlib import Path

import requests

headers = {
    "Restful": "yes",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "okhttp/4.12.0",
    "Connection": "keep-alive",
}
url = f"https://varnish-prod.avscaracoltv.com/AGL/1.6/A/ENG/ANDROID/ALL/PAGE/402"

resp = requests.get(url, headers=headers)

print(resp.status_code)

Path("page_402_catalog_root.json").write_text(json.dumps(resp.json()))

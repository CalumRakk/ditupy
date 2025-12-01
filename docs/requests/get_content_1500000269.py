import requests
from utils import save_api_response

headers = {
    "Restful": "yes",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "okhttp/4.12.0",
    "Connection": "keep-alive",
}

base_url = "https://varnish-prod.avscaracoltv.com"
url2 = f"{base_url}/AGL/1.6/A/ENG/ANDROID/ALL/CONTENT/DETAIL/BUNDLE/1500000269"
resp2 = requests.get(url2, headers=headers)

save_api_response(url2, resp2.json())

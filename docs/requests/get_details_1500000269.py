import requests
from utils import save_api_response

headers = {
    "Restful": "yes",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "okhttp/4.12.0",
    "Connection": "keep-alive",
}

base_url = "https://varnish-prod.avscaracoltv.com"
url1 = f"{base_url}/AGL/1.6/A/ENG/ANDROID/ALL/PAGE/DETAILS/BUNDLE/1500000269"
resp = requests.get(url1, headers=headers)
save_api_response(url1, resp.json())

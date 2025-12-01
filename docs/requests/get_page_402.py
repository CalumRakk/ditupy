import requests
from utils import save_api_response

url = "https://varnish-prod.avscaracoltv.com/AGL/1.6/A/ENG/ANDROID/ALL/PAGE/402"
headers = {
    "Restful": "yes",
    "User-Agent": "okhttp/4.12.0",
}
resp = requests.get(url, headers=headers)
resp.raise_for_status()

save_api_response(url, resp.json())

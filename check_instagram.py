import os
import requests
import json

TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")
PAGE_ID = "126905452957956"

url = f"https://graph.facebook.com/v26.0/{PAGE_ID}"

params = {
    "fields": "instagram_business_account",
    "access_token": TOKEN
}

response = requests.get(url, params=params)

print("Status:", response.status_code)

try:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception:
    print(response.text)

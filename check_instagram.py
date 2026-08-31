import os
import json
import requests

TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")

if not TOKEN:
    raise RuntimeError("FACEBOOK_PAGE_TOKEN is missing")

GRAPH_VERSION = "v26.0"

url = f"https://graph.facebook.com/{GRAPH_VERSION}/me"

params = {
    "fields": "id,name,instagram_business_account",
    "access_token": TOKEN
}

response = requests.get(url, params=params, timeout=30)

print("Status:", response.status_code)

try:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception:
    print(response.text)

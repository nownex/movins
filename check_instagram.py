import os
import requests
import json


TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")

if not TOKEN:
    raise RuntimeError("FACEBOOK_PAGE_TOKEN is missing")


url = "https://graph.facebook.com/v26.0/me"

params = {
    "fields": "id,name,instagram_business_account{id,username}",
    "access_token": TOKEN
}


response = requests.get(url, params=params)


print("Status:", response.status_code)

print(
    json.dumps(
        response.json(),
        indent=2,
        ensure_ascii=False
    )
)


response.raise_for_status()

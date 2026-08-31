import os
import json
import requests

TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")

if not TOKEN:
    raise RuntimeError("FACEBOOK_PAGE_TOKEN is missing")

GRAPH_VERSION = "v26.0"

# الحصول على الصفحة المرتبطة بهذا الـ Page Access Token
me_url = f"https://graph.facebook.com/{GRAPH_VERSION}/me"

response = requests.get(
    me_url,
    params={
        "fields": "id,name",
        "access_token": TOKEN
    },
    timeout=30
)

print("STEP 1 - PAGE")
print("Status:", response.status_code)

data = response.json()
print(json.dumps(data, indent=2, ensure_ascii=False))

if "id" not in data:
    raise RuntimeError("Could not get Facebook Page ID")

PAGE_ID = data["id"]

# الحصول على حساب Instagram Business المرتبط بالصفحة
ig_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PAGE_ID}"

response = requests.get(
    ig_url,
    params={
        "fields": "instagram_business_account{id,username}",
        "access_token": TOKEN
    },
    timeout=30
)

print("\nSTEP 2 - INSTAGRAM CONNECTION")
print("Status:", response.status_code)

ig_data = response.json()
print(json.dumps(ig_data, indent=2, ensure_ascii=False))

instagram = ig_data.get("instagram_business_account")

if instagram:
    print("\nSUCCESS!")
    print("Instagram ID:", instagram.get("id"))
    print("Instagram username:", instagram.get("username"))
else:
    print("\nNO INSTAGRAM BUSINESS ACCOUNT FOUND")

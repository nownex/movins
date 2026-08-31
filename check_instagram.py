import os
import json
import requests


TOKEN = os.environ.get(
    "FACEBOOK_PAGE_TOKEN"
)

if not TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing"
    )


GRAPH_VERSION = "v26.0"

BASE_URL = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}"
)


# =========================================================
# STEP 1
# CHECK TOKEN PAGE
# =========================================================

print("=" * 60)
print("STEP 1 - PAGE")
print("=" * 60)

response = requests.get(

    f"{BASE_URL}/me",

    params={

        "fields":
            "id,name,instagram_business_account{id,username}",

        "access_token":
            TOKEN

    },

    timeout=30

)

print(
    "Status:",
    response.status_code
)

data = response.json()

print(
    json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )
)


# =========================================================
# PAGE ID
# =========================================================

PAGE_ID = data.get(
    "id"
)

if not PAGE_ID:

    print(
        "ERROR: Could not get Page ID"
    )

    raise SystemExit(1)


# =========================================================
# STEP 2
# CHECK PAGE INSTAGRAM FIELD
# =========================================================

print()
print("=" * 60)
print("STEP 2 - PAGE INSTAGRAM BUSINESS ACCOUNT")
print("=" * 60)

response = requests.get(

    f"{BASE_URL}/{PAGE_ID}",

    params={

        "fields":
            "id,name,instagram_business_account{id,username}",

        "access_token":
            TOKEN

    },

    timeout=30

)

print(
    "Status:",
    response.status_code
)

page_data = response.json()

print(
    json.dumps(
        page_data,
        ensure_ascii=False,
        indent=2
    )
)


instagram = page_data.get(
    "instagram_business_account"
)


# =========================================================
# RESULT
# =========================================================

print()
print("=" * 60)
print("RESULT")
print("=" * 60)

if instagram:

    print()
    print(
        "SUCCESS! INSTAGRAM BUSINESS ACCOUNT FOUND"
    )

    print(
        "Instagram ID:",
        instagram.get("id")
    )

    print(
        "Username:",
        instagram.get("username")
    )

else:

    print()
    print(
        "INSTAGRAM ACCOUNT NOT EXPOSED TO GRAPH API"
    )

    print()
    print(
        "The Meta interface shows the account is linked,"
    )

    print(
        "but the current Page Access Token cannot retrieve"
    )

    print(
        "instagram_business_account."
    )

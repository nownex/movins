import os
import requests
import json


TOKEN = os.environ.get(
    "FACEBOOK_PAGE_TOKEN"
)


if not TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing"
    )


GRAPH_VERSION = "v26.0"


url = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}/me"
)


params = {
    "fields": (
        "id,"
        "name,"
        "instagram_business_account{id,username}"
    ),
    "access_token": TOKEN
}


response = requests.get(
    url,
    params=params,
    timeout=30
)


print(
    "Status:",
    response.status_code
)


try:

    result = response.json()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )

except Exception:

    print(
        response.text
    )

import json
import os
from datetime import datetime, timezone

import requests


API_KEY = os.environ.get("TMDB_API_KEY")

if not API_KEY:
    raise RuntimeError("TMDB_API_KEY is missing")

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "accept": "application/json",
}


def get_trending(media_type):
    url = f"{BASE_URL}/trending/{media_type}/week"

    params = {
        "language": "ar-SA",
    }

    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    response.raise_for_status()
    return response.json().get("results", [])


def clean_item(item, media_type):
    title = item.get("title") if media_type == "movie" else item.get("name")

    date = (
        item.get("release_date")
        if media_type == "movie"
        else item.get("first_air_date")
    )

    year = date[:4] if date else ""

    overview = (item.get("overview") or "").strip()

    return {
        "id": item.get("id"),
        "type": "فيلم" if media_type == "movie" else "مسلسل",
        "title": title or "بدون عنوان",
        "year": year,
        "overview": overview or "لا يوجد ملخص متوفر حاليًا.",
        "rating": round(float(item.get("vote_average") or 0), 1),
        "poster": (
            IMAGE_BASE + item["poster_path"]
            if item.get("poster_path")
            else ""
        ),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    movies = get_trending("movie")
    tv = get_trending("tv")

    results = []

    for item in movies:
        if item.get("poster_path"):
            results.append(clean_item(item, "movie"))

    for item in tv:
        if item.get("poster_path"):
            results.append(clean_item(item, "tv"))

    results = results[:30]

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": results,
    }

    with open("movies.json", "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"MOVINS: {len(results)} items saved.")


if __name__ == "__main__":
    main()

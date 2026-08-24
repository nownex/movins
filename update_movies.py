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


# =========================================================
# TMDB GENRES
# =========================================================

GENRES_AR = {
    28: "أكشن",
    12: "مغامرة",
    16: "رسوم متحركة",
    35: "كوميدي",
    80: "جريمة",
    99: "وثائقي",
    18: "دراما",
    10751: "عائلي",
    14: "فانتازيا",
    36: "تاريخي",
    27: "رعب",
    10402: "موسيقى",
    9648: "غموض",
    10749: "رومانسي",
    878: "خيال علمي",
    10770: "فيلم تلفزيوني",
    53: "إثارة",
    10752: "حربي",
    37: "غربي",
}


# =========================================================
# GET TRENDING
# =========================================================

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

    return response.json().get(
        "results",
        []
    )


# =========================================================
# GENRE TEXT
# =========================================================

def get_genres(item):

    genre_ids = item.get(
        "genre_ids",
        []
    )

    genres = []

    for genre_id in genre_ids:

        genre_name = GENRES_AR.get(
            genre_id
        )

        if genre_name:
            genres.append(
                genre_name
            )

    # Remove duplicates
    genres = list(
        dict.fromkeys(genres)
    )

    return genres


# =========================================================
# DETAILED TYPE
# =========================================================

def get_detailed_type(
    media_type,
    genres
):

    base_type = (
        "فيلم"
        if media_type == "movie"
        else "مسلسل"
    )

    if not genres:
        return base_type

    # Maximum 3 genres in the displayed type
    selected = genres[:3]

    return (
        base_type
        + " "
        + " • ".join(selected)
    )


# =========================================================
# CLEAN ITEM
# =========================================================

def clean_item(
    item,
    media_type
):

    title = (
        item.get("title")
        if media_type == "movie"
        else item.get("name")
    )

    date = (
        item.get("release_date")
        if media_type == "movie"
        else item.get("first_air_date")
    )

    year = (
        date[:4]
        if date
        else ""
    )

    overview = (
        item.get("overview")
        or ""
    ).strip()


    genres = get_genres(
        item
    )


    detailed_type = get_detailed_type(
        media_type,
        genres
    )


    return {

        "id": item.get("id"),

        "type": (
            "فيلم"
            if media_type == "movie"
            else "مسلسل"
        ),

        "detailed_type":
            detailed_type,

        "genres":
            genres,

        "title":
            title or "بدون عنوان",

        "year":
            year,

        "overview":
            overview
            or "لا يوجد ملخص متوفر حاليًا.",

        "rating":
            round(
                float(
                    item.get(
                        "vote_average"
                    )
                    or 0
                ),
                1
            ),

        "poster": (
            IMAGE_BASE
            + item["poster_path"]
            if item.get("poster_path")
            else ""
        ),

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


# =========================================================
# MAIN
# =========================================================

def main():

    movies = get_trending(
        "movie"
    )

    tv = get_trending(
        "tv"
    )


    results = []


    for item in movies:

        if item.get(
            "poster_path"
        ):

            results.append(
                clean_item(
                    item,
                    "movie"
                )
            )


    for item in tv:

        if item.get(
            "poster_path"
        ):

            results.append(
                clean_item(
                    item,
                    "tv"
                )
            )


    # Maximum 30 items
    results = results[:30]


    data = {

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "items":
            results,
    }


    with open(
        "movies.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


    print(
        f"MOVINS: "
        f"{len(results)} items saved."
    )


    # Show genres in GitHub Actions log
    for item in results[:10]:

        print(
            f"{item['title']} "
            f"→ "
            f"{item['detailed_type']}"
        )


# =========================================================

if __name__ == "__main__":
    main()

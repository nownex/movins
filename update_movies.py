import json
import os
from datetime import datetime, timezone

import requests


# =========================================================
# MOVINS — TMDB MOVIE / TV ENGINE
# =========================================================

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

MOVIE_GENRES = {
    28: "أكشن",
    12: "مغامرة",
    16: "رسوم",
    35: "كوميديا",
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
    10770: "تلفزيوني",
    53: "إثارة",
    10752: "حربي",
    37: "غربي",
}


TV_GENRES = {
    10759: "أكشن",
    16: "رسوم",
    35: "كوميديا",
    80: "جريمة",
    99: "وثائقي",
    18: "دراما",
    10751: "عائلي",
    10762: "أطفال",
    9648: "غموض",
    10763: "أخبار",
    10764: "واقعي",
    10765: "خيال علمي",
    10766: "دراما",
    10767: "حواري",
    10768: "حربي وسياسي",
    37: "غربي",
}


# =========================================================
# GENRE PRIORITY
# =========================================================

MAIN_GENRE_ORDER = [
    "دراما",
    "أكشن",
    "كوميديا",
    "رعب",
    "خيال علمي",
    "رسوم",
]


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

    return response.json().get("results", [])


# =========================================================
# GET GENRES
# =========================================================

def get_genres(item, media_type):

    genre_ids = item.get("genre_ids") or []

    mapping = (
        MOVIE_GENRES
        if media_type == "movie"
        else TV_GENRES
    )

    genres = []

    for genre_id in genre_ids:

        name = mapping.get(genre_id)

        if name and name not in genres:
            genres.append(name)

    return genres


# =========================================================
# TITLE LOGIC
# =========================================================

def get_title(item, media_type):

    original_language = (
        item.get("original_language") or ""
    ).lower()

    original_title = (
        item.get("original_title")
        if media_type == "movie"
        else item.get("original_name")
    )

    translated_title = (
        item.get("title")
        if media_type == "movie"
        else item.get("name")
    )


    # العربية / الإنجليزية / الفرنسية
    # نحافظ على العنوان الأصلي

    if original_language in {
        "ar",
        "en",
        "fr",
    }:

        return (
            original_title
            or translated_title
            or "بدون عنوان"
        )


    # اللغات الأخرى:
    # نستخدم العنوان العربي القادم من TMDB

    return (
        translated_title
        or original_title
        or "بدون عنوان"
    )


# =========================================================
# DETAILED TYPE
# =========================================================

def get_detailed_type(
    item,
    media_type,
    genres
):

    if media_type == "movie":

        prefix = "فيلم"

    else:

        prefix = "مسلسل"


    # الأولوية للتصنيفات المهمة للموقع

    preferred = [
        "دراما",
        "أكشن",
        "كوميديا",
        "رعب",
        "خيال علمي",
        "رسوم",
    ]

    for genre in preferred:

        if genre in genres:

            return f"{prefix} {genre}"


    if genres:

        return f"{prefix} {genres[0]}"


    return prefix


# =========================================================
# HASHTAGS
# =========================================================

def create_hashtags(
    title,
    media_type,
    genres
):

    tags = []

    tags.append("#MOVINS")

    if media_type == "movie":

        tags.append("#أفلام")

    else:

        tags.append("#مسلسلات")


    for genre in genres:

        if genre == "دراما":
            tags.append("#دراما")

        elif genre == "أكشن":
            tags.append("#أكشن")

        elif genre == "كوميديا":
            tags.append("#كوميديا")

        elif genre == "رعب":
            tags.append("#رعب")

        elif genre == "خيال علمي":
            tags.append("#خيال_علمي")

        elif genre == "رسوم":
            tags.append("#رسوم")


    return tags[:7]


# =========================================================
# CLEAN ITEM
# =========================================================

def clean_item(item, media_type):

    title = get_title(
        item,
        media_type
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
        item,
        media_type
    )


    detailed_type = get_detailed_type(
        item,
        media_type,
        genres
    )


    hashtags = create_hashtags(
        title,
        media_type,
        genres
    )


    poster = ""

    if item.get("poster_path"):

        poster = (
            IMAGE_BASE +
            item["poster_path"]
        )


    return {

        "id":
            item.get("id"),

        "type":
            "فيلم"
            if media_type == "movie"
            else "مسلسل",

        "detailed_type":
            detailed_type,

        "title":
            title,

        "original_title":
            (
                item.get("original_title")
                if media_type == "movie"
                else item.get("original_name")
            ),

        "original_language":
            item.get(
                "original_language",
                ""
            ),

        "year":
            year,

        "overview":
            overview
            or
            "لا يوجد ملخص متوفر حاليًا.",

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

        "poster":
            poster,

        "genre_ids":
            item.get(
                "genre_ids",
                []
            ),

        "genres":
            genres,

        "hashtags":
            hashtags,

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

    }


# =========================================================
# MAIN
# =========================================================

def main():

    movies = get_trending("movie")

    tv = get_trending("tv")


    results = []


    # الأفلام

    for item in movies:

        if item.get("poster_path"):

            results.append(
                clean_item(
                    item,
                    "movie"
                )
            )


    # المسلسلات

    for item in tv:

        if item.get("poster_path"):

            results.append(
                clean_item(
                    item,
                    "tv"
                )
            )


    # إزالة التكرار

    unique = {}

    for item in results:

        key = (
            item["type"],
            item["id"]
        )

        unique[key] = item


    results = list(
        unique.values()
    )


    # أقصى عدد

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
        f"MOVINS: {len(results)} items saved."
    )


if __name__ == "__main__":
    main()

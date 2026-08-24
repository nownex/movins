import json
import os
import re
from datetime import datetime, timezone

import requests


# =========================================================
# MOVINS — TMDB UPDATE ENGINE
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
# GENRES
# =========================================================

MOVIE_GENRES = {
    28: "أكشن",
    12: "مغامرة",
    16: "رسوم متحركة",
    35: "كوميديا",
    80: "جريمة",
    99: "وثائقي",
    18: "دراما",
    10751: "عائلي",
    14: "خيال",
    36: "تاريخي",
    27: "رعب",
    10402: "موسيقى",
    9648: "غموض",
    10749: "رومانسي",
    878: "خيال علمي",
    10770: "فيلم تلفزيوني",
    53: "إثارة",
    10752: "حرب",
    37: "غربي",
}


TV_GENRES = {
    10759: "أكشن ومغامرة",
    16: "رسوم متحركة",
    35: "كوميديا",
    80: "جريمة",
    99: "وثائقي",
    18: "دراما",
    10751: "عائلي",
    10762: "أطفال",
    9648: "غموض",
    10763: "أخبار",
    10764: "واقعي",
    10765: "خيال علمي وفانتازيا",
    10766: "صابونيات",
    10767: "حديث",
    10768: "حرب وسياسة",
    37: "غربي",
}


# =========================================================
# LANGUAGE DETECTION
# =========================================================

def contains_arabic(text):

    if not text:
        return False

    return bool(
        re.search(
            r"[\u0600-\u06FF]",
            str(text)
        )
    )


def contains_french_chars(text):

    if not text:
        return False

    return bool(
        re.search(
            r"[àâçéèêëîïôùûüÿœæÀÂÇÉÈÊËÎÏÔÙÛÜŸŒÆ]",
            str(text)
        )
    )


def contains_latin(text):

    if not text:
        return False

    return bool(
        re.search(
            r"[A-Za-z]",
            str(text)
        )
    )


def contains_non_latin(text):

    if not text:
        return False

    text = str(text)

    # Remove spaces, numbers and punctuation
    cleaned = re.sub(
        r"[\s\d\W_]+",
        "",
        text,
        flags=re.UNICODE
    )

    if not cleaned:
        return False

    # Arabic is handled separately
    if contains_arabic(text):
        return False

    # Latin languages are handled separately
    if contains_latin(text):
        return False

    # Remaining scripts such as:
    # Japanese
    # Korean
    # Chinese
    # Russian
    # etc.
    return True


# =========================================================
# CHOOSE TITLE
# =========================================================

def choose_title(item, media_type):

    if media_type == "movie":

        original = (
            item.get("original_title")
            or ""
        ).strip()

        arabic = (
            item.get("title")
            or ""
        ).strip()

    else:

        original = (
            item.get("original_name")
            or ""
        ).strip()

        arabic = (
            item.get("name")
            or ""
        ).strip()


    # -----------------------------------------------------
    # Arabic
    # -----------------------------------------------------

    if contains_arabic(original):

        return original


    # -----------------------------------------------------
    # English / French / Latin
    #
    # Keep original.
    # -----------------------------------------------------

    if contains_latin(original):

        return original


    # -----------------------------------------------------
    # Japanese / Korean / Chinese / etc.
    #
    # Use TMDB Arabic title if available.
    # -----------------------------------------------------

    if arabic and contains_arabic(arabic):

        return arabic


    # -----------------------------------------------------
    # Fallback
    # -----------------------------------------------------

    if original:

        return original


    if arabic:

        return arabic


    return "بدون عنوان"


# =========================================================
# GET TRENDING
# =========================================================

def get_trending(media_type):

    url = (
        f"{BASE_URL}/trending/"
        f"{media_type}/week"
    )

    params = {
        # This makes the overview Arabic.
        # Title selection is handled separately.
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
# GET GENRES
# =========================================================

def get_genres(item, media_type):

    genre_ids = item.get(
        "genre_ids",
        []
    )

    genre_map = (
        MOVIE_GENRES
        if media_type == "movie"
        else TV_GENRES
    )

    genres = []

    for genre_id in genre_ids:

        name = genre_map.get(
            genre_id
        )

        if name and name not in genres:

            genres.append(name)

    return genres


# =========================================================
# DETAILED TYPE
# =========================================================

def get_detailed_type(
    media_type,
    genres
):

    prefix = (
        "فيلم"
        if media_type == "movie"
        else "مسلسل"
    )

    priority = [
        "أكشن",
        "أكشن ومغامرة",
        "كوميديا",
        "دراما",
        "رعب",
        "خيال علمي",
        "خيال علمي وفانتازيا",
        "رومانسي",
        "غموض",
        "جريمة",
        "مغامرة",
        "إثارة",
        "وثائقي",
        "رسوم متحركة",
        "تاريخي",
        "عائلي",
        "حرب",
        "حرب وسياسة",
        "موسيقى",
        "غربي",
    ]

    selected = None

    for wanted in priority:

        for genre in genres:

            if wanted in genre:

                selected = genre

                break

        if selected:
            break


    if selected:

        if selected == "أكشن ومغامرة":
            selected = "أكشن"

        elif selected == "خيال علمي وفانتازيا":
            selected = "خيال علمي"

        elif selected == "حرب وسياسة":
            selected = "حرب"

        return f"{prefix} {selected}"


    return prefix


# =========================================================
# HASHTAGS
# =========================================================

def create_hashtags(
    media_type,
    genres
):

    hashtags = [
        "#MOVINS"
    ]

    if media_type == "movie":

        hashtags.extend([
            "#فيلم",
            "#أفلام",
            "#Movies"
        ])

    else:

        hashtags.extend([
            "#مسلسل",
            "#مسلسلات",
            "#TVShows"
        ])


    genre_hashtags = {

        "أكشن": "#أكشن",
        "أكشن ومغامرة": "#أكشن",
        "مغامرة": "#مغامرة",
        "كوميديا": "#كوميديا",
        "دراما": "#دراما",
        "رعب": "#رعب",
        "خيال علمي": "#خيال_علمي",
        "خيال علمي وفانتازيا": "#خيال_علمي",
        "رومانسي": "#رومانسي",
        "غموض": "#غموض",
        "جريمة": "#جريمة",
        "إثارة": "#إثارة",
        "وثائقي": "#وثائقي",
        "رسوم متحركة": "#رسوم_متحركة",
        "تاريخي": "#تاريخي",
        "عائلي": "#عائلي",
        "حرب": "#حرب",
        "حرب وسياسة": "#حرب",
        "موسيقى": "#موسيقى",
        "غربي": "#ويسترن",
    }


    for genre in genres:

        tag = genre_hashtags.get(
            genre
        )

        if tag and tag not in hashtags:

            hashtags.append(tag)


    return " ".join(
        hashtags[:10]
    )


# =========================================================
# CLEAN ITEM
# =========================================================

def clean_item(
    item,
    media_type
):

    title = choose_title(
        item,
        media_type
    )


    if media_type == "movie":

        original_title = (
            item.get("original_title")
            or ""
        )

        date = (
            item.get("release_date")
            or ""
        )

    else:

        original_title = (
            item.get("original_name")
            or ""
        )

        date = (
            item.get("first_air_date")
            or ""
        )


    year = (
        date[:4]
        if date
        else ""
    )


    # -----------------------------------------------------
    # Arabic overview
    # -----------------------------------------------------

    overview = (
        item.get("overview")
        or ""
    ).strip()


    if not overview:

        overview = (
            "لا يوجد ملخص متوفر حاليًا."
        )


    # -----------------------------------------------------
    # Genres
    # -----------------------------------------------------

    genres = get_genres(
        item,
        media_type
    )


    # -----------------------------------------------------
    # Detailed type
    # -----------------------------------------------------

    detailed_type = get_detailed_type(
        media_type,
        genres
    )


    # -----------------------------------------------------
    # Rating
    # -----------------------------------------------------

    try:

        rating = round(
            float(
                item.get(
                    "vote_average"
                )
                or 0
            ),
            1
        )

    except Exception:

        rating = 0


    # -----------------------------------------------------
    # Poster
    # -----------------------------------------------------

    poster = ""

    if item.get("poster_path"):

        poster = (
            IMAGE_BASE
            + item["poster_path"]
        )


    # -----------------------------------------------------
    # Hashtags
    # -----------------------------------------------------

    hashtags = create_hashtags(
        media_type,
        genres
    )


    return {

        "id":
            item.get("id"),

        "type":
            (
                "فيلم"
                if media_type == "movie"
                else "مسلسل"
            ),

        "detailed_type":
            detailed_type,

        "genres":
            genres,

        # Display title
        "title":
            title,

        # Keep original title internally
        "original_title":
            original_title,

        "year":
            year,

        # Arabic summary
        "overview":
            overview,

        "rating":
            rating,

        "poster":
            poster,

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

    print(
        "======================================"
    )

    print(
        "MOVINS — TMDB UPDATE"
    )

    print(
        "======================================"
    )


    movies = get_trending(
        "movie"
    )

    tv = get_trending(
        "tv"
    )


    results = []


    # -----------------------------------------------------
    # MOVIES
    # -----------------------------------------------------

    for item in movies:

        if not item.get(
            "poster_path"
        ):
            continue

        try:

            results.append(
                clean_item(
                    item,
                    "movie"
                )
            )

        except Exception as error:

            print(
                "Movie error:",
                error
            )


    # -----------------------------------------------------
    # TV
    # -----------------------------------------------------

    for item in tv:

        if not item.get(
            "poster_path"
        ):
            continue

        try:

            results.append(
                clean_item(
                    item,
                    "tv"
                )
            )

        except Exception as error:

            print(
                "TV error:",
                error
            )


    # -----------------------------------------------------
    # Remove duplicates
    # -----------------------------------------------------

    unique = {}

    for item in results:

        key = (
            item.get("type"),
            item.get("id")
        )

        unique[key] = item


    results = list(
        unique.values()
    )


    # -----------------------------------------------------
    # Limit
    # -----------------------------------------------------

    results = results[:30]


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    data = {

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "count":
            len(results),

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


    # -----------------------------------------------------
    # LOG
    # -----------------------------------------------------

    print(
        f"MOVINS: {len(results)} items saved."
    )


    print(
        "Sample titles:"
    )


    for item in results[:10]:

        print(
            f"{item['title']} | "
            f"{item['detailed_type']} | "
            f"{item['rating']}"
        )


    print(
        "======================================"
    )


# =========================================================

if __name__ == "__main__":

    main()

import json
import os
from datetime import datetime, timezone

import requests


# =========================================================
# MOVINS — TMDB MOVIE / TV UPDATE ENGINE
# =========================================================

API_KEY = os.environ.get("TMDB_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "TMDB_API_KEY is missing"
    )


BASE_URL = "https://api.themoviedb.org/3"

IMAGE_BASE = (
    "https://image.tmdb.org/t/p/w500"
)


HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "accept": "application/json",
}


OUTPUT_FILE = "movies.json"


# =========================================================
# TMDB GENRES
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
    10766: "دراما تلفزيونية",
    10767: "حواري",
    10768: "حربي وسياسة",
    37: "غربي",
}


# =========================================================
# GENRE PRIORITY
# =========================================================

GENRE_PRIORITY = [
    "أكشن",
    "أكشن ومغامرة",
    "رعب",
    "خيال علمي",
    "خيال علمي وفانتازيا",
    "كوميديا",
    "دراما",
    "غموض",
    "إثارة",
    "مغامرة",
    "فانتازيا",
    "رومانسي",
    "جريمة",
    "رسوم متحركة",
    "عائلي",
    "تاريخي",
    "حربي",
    "وثائقي",
    "موسيقى",
    "غربي",
]


# =========================================================
# LANGUAGE RULES
# =========================================================

# هذه اللغات نحافظ على عنوانها الأصلي.
KEEP_ORIGINAL_TITLE_LANGUAGES = {
    "ar",
    "en",
    "fr",
}


# اللغات التي نفضل لها Poster إنجليزي
# حتى لا يظهر Poster بعنوان غير مفهوم.
FOREIGN_TITLE_LANGUAGES = {
    "ja",   # Japanese
    "ko",   # Korean
    "zh",   # Chinese
    "hi",   # Hindi
    "th",   # Thai
    "ru",   # Russian
    "uk",   # Ukrainian
    "fa",   # Persian
    "tr",   # Turkish
    "he",   # Hebrew
    "id",   # Indonesian
    "vi",   # Vietnamese
}


# =========================================================
# HTTP HELPER
# =========================================================

def tmdb_get(
    endpoint,
    params=None
):
    """
    Common TMDB GET request.
    """

    url = (
        f"{BASE_URL}"
        f"{endpoint}"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        params=params or {},
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# GET TRENDING
# =========================================================

def get_trending(
    media_type
):

    endpoint = (
        f"/trending/"
        f"{media_type}/week"
    )

    params = {
        # Arabic overview
        # and Arabic metadata where available.
        "language": "ar-SA",

        # Keep original language information.
        "include_adult": "false",
    }

    data = tmdb_get(
        endpoint,
        params
    )

    return data.get(
        "results",
        []
    )


# =========================================================
# GET POSTERS
# =========================================================

def get_posters(
    media_type,
    item_id
):
    """
    Get all available posters for a movie/show.
    """

    if media_type == "movie":

        endpoint = (
            f"/movie/"
            f"{item_id}/images"
        )

    else:

        endpoint = (
            f"/tv/"
            f"{item_id}/images"
        )

    try:

        data = tmdb_get(
            endpoint,
            {
                "include_image_language":
                    "ar,en,fr,null"
            }
        )

        return data.get(
            "posters",
            []
        )

    except Exception as error:

        print(
            "Poster API warning:",
            error
        )

        return []


# =========================================================
# SELECT POSTER
# =========================================================

def get_best_poster(
    media_type,
    item
):
    """
    Poster selection rules:

    Arabic / English / French:
        Prefer original-language poster.

    Japanese / Korean / Chinese / other languages:
        Prefer English poster.
        Then Arabic poster.
        Then neutral poster.
        Then original poster.
    """

    item_id = item.get(
        "id"
    )

    original_language = (
        item.get(
            "original_language"
        )
        or ""
    ).lower()


    fallback = ""

    if item.get(
        "poster_path"
    ):

        fallback = (
            IMAGE_BASE
            + item["poster_path"]
        )


    if not item_id:

        return fallback


    posters = get_posters(
        media_type,
        item_id
    )


    if not posters:

        return fallback


    # -----------------------------------------------------
    # Helper
    # -----------------------------------------------------

    def find_language(
        language
    ):

        for poster in posters:

            if poster.get(
                "iso_639_1"
            ) == language:

                path = poster.get(
                    "file_path"
                )

                if path:

                    return (
                        IMAGE_BASE
                        + path
                    )

        return ""


    # -----------------------------------------------------
    # 1. Original language
    # -----------------------------------------------------

    if original_language in KEEP_ORIGINAL_TITLE_LANGUAGES:

        original_poster = find_language(
            original_language
        )

        if original_poster:

            return original_poster


    # -----------------------------------------------------
    # 2. Foreign languages
    # -----------------------------------------------------

    if (
        original_language
        not in KEEP_ORIGINAL_TITLE_LANGUAGES
    ):

        # English first
        english_poster = find_language(
            "en"
        )

        if english_poster:

            return english_poster


        # French second
        french_poster = find_language(
            "fr"
        )

        if french_poster:

            return french_poster


        # Arabic third
        arabic_poster = find_language(
            "ar"
        )

        if arabic_poster:

            return arabic_poster


    # -----------------------------------------------------
    # 3. Neutral poster
    # -----------------------------------------------------

    for poster in posters:

        if poster.get(
            "iso_639_1"
        ) is None:

            path = poster.get(
                "file_path"
            )

            if path:

                return (
                    IMAGE_BASE
                    + path
                )


    # -----------------------------------------------------
    # 4. English fallback
    # -----------------------------------------------------

    english_poster = find_language(
        "en"
    )

    if english_poster:

        return english_poster


    # -----------------------------------------------------
    # 5. Arabic fallback
    # -----------------------------------------------------

    arabic_poster = find_language(
        "ar"
    )

    if arabic_poster:

        return arabic_poster


    # -----------------------------------------------------
    # 6. Original TMDB poster
    # -----------------------------------------------------

    return fallback


# =========================================================
# GET GENRE NAMES
# =========================================================

def get_genres(
    item,
    media_type
):

    genre_map = (
        MOVIE_GENRES
        if media_type == "movie"
        else TV_GENRES
    )


    genre_ids = item.get(
        "genre_ids",
        []
    )


    genres = []


    for genre_id in genre_ids:

        try:

            genre_id = int(
                genre_id
            )

        except (
            TypeError,
            ValueError
        ):

            continue


        name = genre_map.get(
            genre_id
        )


        if name and name not in genres:

            genres.append(
                name
            )


    return genres


# =========================================================
# GET DETAILED TYPE
# =========================================================

def get_detailed_type(
    media_type,
    genres
):
    """
    Examples:

    فيلم أكشن
    فيلم كوميدي
    فيلم دراما

    مسلسل أكشن
    مسلسل دراما
    مسلسل رعب
    """

    base = (
        "فيلم"
        if media_type == "movie"
        else "مسلسل"
    )


    if not genres:

        return base


    selected_genre = None


    for priority in GENRE_PRIORITY:

        if priority in genres:

            selected_genre = priority

            break


    if not selected_genre:

        selected_genre = genres[0]


    return (
        f"{base} "
        f"{selected_genre}"
    )


# =========================================================
# HASHTAGS
# =========================================================

def generate_hashtags(
    title,
    media_type,
    genres
):

    tags = [
        "#MOVINS"
    ]


    if media_type == "movie":

        tags.append(
            "#أفلام"
        )

    else:

        tags.append(
            "#مسلسلات"
        )


    # -----------------------------------------------------
    # Genre hashtags
    # -----------------------------------------------------

    hashtag_map = {

        "أكشن":
            "#أكشن",

        "أكشن ومغامرة":
            "#أكشن",

        "مغامرة":
            "#مغامرة",

        "كوميديا":
            "#كوميديا",

        "دراما":
            "#دراما",

        "رعب":
            "#رعب",

        "خيال علمي":
            "#خيال_علمي",

        "خيال علمي وفانتازيا":
            "#خيال_علمي",

        "فانتازيا":
            "#فانتازيا",

        "غموض":
            "#غموض",

        "إثارة":
            "#إثارة",

        "جريمة":
            "#جريمة",

        "رومانسي":
            "#رومانسي",

        "رسوم متحركة":
            "#رسوم_متحركة",

        "عائلي":
            "#عائلي",

        "تاريخي":
            "#تاريخي",

        "حربي":
            "#حربي",

        "وثائقي":
            "#وثائقي",

        "موسيقى":
            "#موسيقى",

        "غربي":
            "#غربي",
    }


    for genre in genres[:4]:

        tag = hashtag_map.get(
            genre
        )

        if tag and tag not in tags:

            tags.append(
                tag
            )


    # -----------------------------------------------------
    # Title hashtag
    # -----------------------------------------------------

    # Do NOT create Arabic translation
    # of the title.

    clean_title = str(
        title or ""
    ).strip()


    if clean_title:

        # Only simple Latin titles
        # are suitable as hashtags.
        safe_title = (
            clean_title
            .replace(
                " ",
                "_"
            )
            .replace(
                "-",
                "_"
            )
        )


        if (
            safe_title
            and len(safe_title) <= 40
        ):

            tags.append(
                "#" + safe_title
            )


    return " ".join(
        tags[:8]
    )


# =========================================================
# CLEAN ITEM
# =========================================================

def clean_item(
    item,
    media_type
):

    # -----------------------------------------------------
    # ORIGINAL TITLE
    # -----------------------------------------------------

    if media_type == "movie":

        title = (
            item.get(
                "original_title"
            )
            or item.get(
                "title"
            )

        )

        date = (
            item.get(
                "release_date"
            )
        )

    else:

        title = (
            item.get(
                "original_name"
            )
            or item.get(
                "name"
            )
        )

        date = (
            item.get(
                "first_air_date"
            )
        )


    # -----------------------------------------------------
    # YEAR
    # -----------------------------------------------------

    year = (
        date[:4]
        if date
        else ""
    )


    # -----------------------------------------------------
    # ORIGINAL LANGUAGE
    # -----------------------------------------------------

    original_language = (
        item.get(
            "original_language"
        )
        or ""
    ).lower()


    # -----------------------------------------------------
    # ARABIC OVERVIEW
    # -----------------------------------------------------

    overview = (
        item.get(
            "overview"
        )
        or ""
    ).strip()


    if not overview:

        overview = (
            "لا يوجد ملخص "
            "متوفر حاليًا."
        )


    # -----------------------------------------------------
    # GENRES
    # -----------------------------------------------------

    genres = get_genres(
        item,
        media_type
    )


    # -----------------------------------------------------
    # DETAILED TYPE
    # -----------------------------------------------------

    detailed_type = (
        get_detailed_type(
            media_type,
            genres
        )
    )


    # -----------------------------------------------------
    # RATING
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

    except (
        TypeError,
        ValueError
    ):

        rating = 0.0


    # -----------------------------------------------------
    # POSTER
    # -----------------------------------------------------

    poster = get_best_poster(
        media_type,
        item
    )


    # -----------------------------------------------------
    # HASHTAGS
    # -----------------------------------------------------

    hashtags = generate_hashtags(
        title,
        media_type,
        genres
    )


    # =====================================================
    # FINAL OBJECT
    # =====================================================

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

        # Original title.
        # Arabic / English / French stay original.
        "title":
            title
            or "بدون عنوان",

        "original_title":
            title
            or "بدون عنوان",

        "original_language":
            original_language,

        "year":
            year,

        # Arabic overview
        "overview":
            overview,

        "rating":
            rating,

        # Arabic genre names
        "genres":
            genres,

        # Best non-Arabic poster
        # according to language rules
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
        "MOVINS TMDB UPDATE STARTED"
    )

    print(
        "======================================"
    )


    # -----------------------------------------------------
    # TRENDING MOVIES
    # -----------------------------------------------------

    print(
        "Fetching trending movies..."
    )

    movies = get_trending(
        "movie"
    )


    print(
        f"Movies received: "
        f"{len(movies)}"
    )


    # -----------------------------------------------------
    # TRENDING TV
    # -----------------------------------------------------

    print(
        "Fetching trending TV..."
    )

    tv = get_trending(
        "tv"
    )


    print(
        f"TV received: "
        f"{len(tv)}"
    )


    # -----------------------------------------------------
    # COMBINE
    # -----------------------------------------------------

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

            clean = clean_item(
                item,
                "movie"
            )


            if clean.get(
                "poster"
            ):

                results.append(
                    clean
                )


        except Exception as error:

            print(
                "Movie processing error:",
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

            clean = clean_item(
                item,
                "tv"
            )


            if clean.get(
                "poster"
            ):

                results.append(
                    clean
                )


        except Exception as error:

            print(
                "TV processing error:",
                error
            )


    # -----------------------------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------------------------

    unique = {}

    for item in results:

        key = (
            f"{item.get('type')}"
            f"-"
            f"{item.get('id')}"
        )


        if key not in unique:

            unique[key] = item


    results = list(
        unique.values()
    )


    # -----------------------------------------------------
    # LIMIT
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

        "items":
            results,
    }


    with open(
        OUTPUT_FILE,
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
        "======================================"
    )

    print(
        f"MOVINS: "
        f"{len(results)} items saved."
    )

    print(
        "======================================"
    )


    for item in results[:10]:

        print(
            f"{item.get('detailed_type')}: "
            f"{item.get('title')} | "
            f"{item.get('original_language')} | "
            f"{item.get('rating')}"
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()

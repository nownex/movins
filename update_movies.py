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
# LIBRARY SETTINGS
# =========================================================

# عدد صفحات الترند التي يتم جلبها في كل تشغيل.
#
# الصفحة الواحدة من TMDB تحتوي عادةً على حوالي 20 عملًا.
#
# 10 صفحات = حوالي 200 فيلم + 200 مسلسل
# 20 صفحة = حوالي 400 فيلم + 400 مسلسل
#
# الأعمال القديمة الموجودة في movies.json
# لن يتم حذفها.
#
TRENDING_PAGES = 10


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

KEEP_ORIGINAL_TITLE_LANGUAGES = {
    "ar",
    "en",
    "fr",
}


FOREIGN_TITLE_LANGUAGES = {
    "ja",
    "ko",
    "zh",
    "hi",
    "th",
    "ru",
    "uk",
    "fa",
    "tr",
    "he",
    "id",
    "vi",
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
    media_type,
    pages=TRENDING_PAGES
):

    all_results = []

    endpoint = (
        f"/trending/"
        f"{media_type}/week"
    )


    for page in range(
        1,
        pages + 1
    ):

        try:

            print(
                f"Fetching trending "
                f"{media_type} page "
                f"{page}/{pages}..."
            )


            data = tmdb_get(
                endpoint,
                {
                    "language": "ar-SA",
                    "include_adult": "false",
                    "page": page,
                }
            )


            page_results = data.get(
                "results",
                []
            )


            if not page_results:

                print(
                    f"No more {media_type} "
                    f"results on page {page}."
                )

                break


            all_results.extend(
                page_results
            )


        except Exception as error:

            print(
                f"Trending {media_type} "
                f"page {page} warning:",
                error
            )

            continue


    # -----------------------------------------------------
    # Remove duplicates from TMDB pages
    # -----------------------------------------------------

    unique = {}

    for item in all_results:

        item_id = item.get(
            "id"
        )

        if not item_id:
            continue

        unique[
            str(item_id)
        ] = item


    return list(
        unique.values()
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
    Poster selection rules.
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

        english_poster = find_language(
            "en"
        )

        if english_poster:

            return english_poster


        french_poster = find_language(
            "fr"
        )

        if french_poster:

            return french_poster


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
# GET TRAILER
# =========================================================

def get_trailer(
    media_type,
    item_id
):
    """
    Get the best available YouTube trailer.
    """

    if not item_id:

        return {
            "trailer_key": "",
            "trailer_url": ""
        }


    if media_type == "movie":

        endpoint = (
            f"/movie/"
            f"{item_id}/videos"
        )

    else:

        endpoint = (
            f"/tv/"
            f"{item_id}/videos"
        )


    try:

        data = tmdb_get(
            endpoint,
            {
                "language": "en-US",
                "include_video_language":
                    "en,null"
            }
        )


        videos = data.get(
            "results",
            []
        )


        youtube_videos = [
            video
            for video in videos
            if video.get(
                "site"
            ) == "YouTube"
            and video.get(
                "key"
            )
        ]


        if not youtube_videos:

            return {
                "trailer_key": "",
                "trailer_url": ""
            }


        # -------------------------------------------------
        # 1. Official Trailer
        # -------------------------------------------------

        official_trailers = [
            video
            for video in youtube_videos
            if video.get(
                "type"
            ) == "Trailer"
            and video.get(
                "official"
            ) is True
        ]


        if official_trailers:

            selected = (
                official_trailers[0]
            )

        else:

            # -------------------------------------------------
            # 2. Any Trailer
            # -------------------------------------------------

            trailers = [
                video
                for video in youtube_videos
                if video.get(
                    "type"
                ) == "Trailer"
            ]


            if trailers:

                selected = trailers[0]

            else:

                # -------------------------------------------------
                # 3. Official Teaser
                # -------------------------------------------------

                teasers = [
                    video
                    for video in youtube_videos
                    if video.get(
                        "type"
                    ) == "Teaser"
                    and video.get(
                        "official"
                    ) is True
                ]


                if not teasers:

                    return {
                        "trailer_key": "",
                        "trailer_url": ""
                    }


                selected = teasers[0]


        trailer_key = selected.get(
            "key",
            ""
        )


        if not trailer_key:

            return {
                "trailer_key": "",
                "trailer_url": ""
            }


        trailer_url = (
            "https://www.youtube.com/watch?v="
            + trailer_key
        )


        return {

            "trailer_key":
                trailer_key,

            "trailer_url":
                trailer_url
        }


    except Exception as error:

        print(
            "Trailer API warning:",
            error
        )

        return {
            "trailer_key": "",
            "trailer_url": ""
        }


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

    clean_title = str(
        title or ""
    ).strip()


    if clean_title:

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
    # TRAILER
    # -----------------------------------------------------

    trailer = get_trailer(
        media_type,
        item.get("id")
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

        "overview":
            overview,

        "rating":
            rating,

        "genres":
            genres,

        "poster":
            poster,

        "trailer_key":
            trailer.get(
                "trailer_key",
                ""
            ),

        "trailer_url":
            trailer.get(
                "trailer_url",
                ""
            ),

        "hashtags":
            hashtags,

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


# =========================================================
# LOAD EXISTING MOVIES
# =========================================================

def load_existing_movies():

    if not os.path.exists(
        OUTPUT_FILE
    ):

        return []


    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )


        items = data.get(
            "items",
            []
        )


        if not isinstance(
            items,
            list
        ):

            return []


        return items


    except Exception as error:

        print(
            "WARNING: Could not load "
            "existing movies.json:",
            error
        )

        return []


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
    # LOAD EXISTING LIBRARY
    # -----------------------------------------------------

    existing_items = (
        load_existing_movies()
    )


    print(
        f"Existing library: "
        f"{len(existing_items)} items"
    )


    # -----------------------------------------------------
    # TRENDING MOVIES
    # -----------------------------------------------------

    print(
        "Fetching trending movies..."
    )

    movies = get_trending(
        "movie",
        TRENDING_PAGES
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
        "tv",
        TRENDING_PAGES
    )


    print(
        f"TV received: "
        f"{len(tv)}"
    )


    # -----------------------------------------------------
    # BUILD LIBRARY
    #
    # Existing items are kept.
    # New / refreshed items replace
    # their old versions.
    # -----------------------------------------------------

    library = {}


    # -----------------------------------------------------
    # FIRST: EXISTING ITEMS
    # -----------------------------------------------------

    for item in existing_items:

        if not isinstance(
            item,
            dict
        ):

            continue


        item_id = item.get(
            "id"
        )


        item_type = item.get(
            "type"
        )


        if not item_id or not item_type:

            continue


        key = (
            f"{item_type}-"
            f"{item_id}"
        )


        library[key] = item


    print(
        f"Library before update: "
        f"{len(library)} items"
    )


    # -----------------------------------------------------
    # PROCESS MOVIES
    # -----------------------------------------------------

    new_movies = 0

    updated_movies = 0


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


            if not clean.get(
                "poster"
            ):

                continue


            key = (
                f"فيلم-"
                f"{clean.get('id')}"
            )


            if key in library:

                updated_movies += 1

            else:

                new_movies += 1


            library[key] = clean


        except Exception as error:

            print(
                "Movie processing error:",
                error
            )


    # -----------------------------------------------------
    # PROCESS TV
    # -----------------------------------------------------

    new_tv = 0

    updated_tv = 0


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


            if not clean.get(
                "poster"
            ):

                continue


            key = (
                f"مسلسل-"
                f"{clean.get('id')}"
            )


            if key in library:

                updated_tv += 1

            else:

                new_tv += 1


            library[key] = clean


        except Exception as error:

            print(
                "TV processing error:",
                error
            )


    # -----------------------------------------------------
    # FINAL RESULTS
    # -----------------------------------------------------

    results = list(
        library.values()
    )


    # -----------------------------------------------------
    # SORT
    #
    # Newest updated items first.
    # Older items remain in the library.
    # -----------------------------------------------------

    results.sort(

        key=lambda item:
            item.get(
                "updated_at",
                ""
            ),

        reverse=True

    )


    # -----------------------------------------------------
    # IMPORTANT:
    #
    # NO 30 ITEM LIMIT.
    #
    # The complete accumulated library
    # is saved.
    # -----------------------------------------------------

    data = {

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "items":
            results,
    }


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

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
        f"New movies: {new_movies}"
    )

    print(
        f"Updated movies: {updated_movies}"
    )

    print(
        f"New TV: {new_tv}"
    )

    print(
        f"Updated TV: {updated_tv}"
    )

    print(
        f"TOTAL LIBRARY: "
        f"{len(results)} items"
    )

    print(
        "======================================"
    )


    for item in results[:20]:

        print(
            f"{item.get('detailed_type')}: "
            f"{item.get('title')} | "
            f"{item.get('original_language')} | "
            f"{item.get('rating')} | "
            f"Trailer: "
            f"{'YES' if item.get('trailer_url') else 'NO'}"
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()

import json
import os
from datetime import datetime, timezone

import requests


# =========================================================
# MOVINS — TMDB MOVIE / TV UPDATE ENGINE
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

OUTPUT_FILE = "movies.json"


# =========================================================
# SETTINGS
# =========================================================

# عدد صفحات Trending التي يتم جلبها في كل تشغيل.
# TMDB يسمح حتى 20 صفحة في هذا النوع من الطلبات.
TRENDING_PAGES = 20

# الحد الأقصى النهائي للملفات المحفوظة.
# لا نضع 30 هنا حتى يحتفظ الموقع بأكبر مكتبة ممكنة.
MAX_ITEMS = 10000


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
# TITLE LANGUAGE RULES
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
# HTTP
# =========================================================

def tmdb_get(endpoint, params=None):

    url = f"{BASE_URL}{endpoint}"

    response = requests.get(
        url,
        headers=HEADERS,
        params=params or {},
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# GET TRENDING PAGE
# =========================================================

def get_trending_page(media_type, page):

    endpoint = f"/trending/{media_type}/week"

    params = {
        "language": "ar-SA",
        "include_adult": "false",
        "page": page,
    }

    data = tmdb_get(
        endpoint,
        params,
    )

    return data.get("results", [])


# =========================================================
# GET ALL TRENDING PAGES
# =========================================================

def get_all_trending(media_type):

    all_results = []

    print(
        f"Fetching {media_type} "
        f"pages 1-{TRENDING_PAGES}..."
    )

    for page in range(
        1,
        TRENDING_PAGES + 1
    ):

        try:

            results = get_trending_page(
                media_type,
                page
            )

            print(
                f"{media_type.upper()} "
                f"page {page}: "
                f"{len(results)} items"
            )

            all_results.extend(
                results
            )

        except Exception as error:

            print(
                f"WARNING: failed "
                f"{media_type} page {page}:",
                error
            )

    return all_results


# =========================================================
# LOAD EXISTING DATA
# =========================================================

def load_existing():

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

            data = json.load(file)


        items = data.get(
            "items",
            []
        )


        if isinstance(
            items,
            list
        ):

            return items


    except Exception as error:

        print(
            "WARNING: could not read "
            "existing movies.json:",
            error
        )


    return []


# =========================================================
# GET POSTERS
# =========================================================

def get_posters(
    media_type,
    item_id
):

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
    # ORIGINAL LANGUAGE
    # -----------------------------------------------------

    if (
        original_language
        in KEEP_ORIGINAL_TITLE_LANGUAGES
    ):

        original_poster = find_language(
            original_language
        )

        if original_poster:

            return original_poster


    # -----------------------------------------------------
    # FOREIGN
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
    # NEUTRAL
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
    # ENGLISH
    # -----------------------------------------------------

    english_poster = find_language(
        "en"
    )

    if english_poster:

        return english_poster


    # -----------------------------------------------------
    # ARABIC
    # -----------------------------------------------------

    arabic_poster = find_language(
        "ar"
    )

    if arabic_poster:

        return arabic_poster


    return fallback


# =========================================================
# GET TRAILER
# =========================================================

def get_trailer(
    media_type,
    item_id
):

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


        return {

            "trailer_key":
                trailer_key,

            "trailer_url":
                (
                    "https://www.youtube.com/watch?v="
                    + trailer_key
                )

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
# GET GENRES
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


        if (
            name
            and name not in genres
        ):

            genres.append(
                name
            )


    return genres


# =========================================================
# DETAILED TYPE
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


        if (
            tag
            and tag not in tags
        ):

            tags.append(
                tag
            )


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
    media_type,
    old_item=None
):

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


    year = (
        date[:4]
        if date
        else ""
    )


    original_language = (
        item.get(
            "original_language"
        )
        or ""
    ).lower()


    overview = (
        item.get(
            "overview"
        )
        or ""
    ).strip()


    # -----------------------------------------------------
    # Keep previous overview if TMDB returns empty
    # -----------------------------------------------------

    if (
        not overview
        and old_item
    ):

        overview = str(
            old_item.get(
                "overview"
            )
            or ""
        ).strip()


    if not overview:

        overview = (
            "لا يوجد ملخص "
            "متوفر حاليًا."
        )


    genres = get_genres(
        item,
        media_type
    )


    # Keep previous genres if necessary
    if (
        not genres
        and old_item
        and isinstance(
            old_item.get("genres"),
            list
        )
    ):

        genres = old_item.get(
            "genres"
        )


    detailed_type = (
        get_detailed_type(
            media_type,
            genres
        )
    )


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


    # Keep previous poster if API fails
    if (
        not poster
        and old_item
    ):

        poster = str(
            old_item.get(
                "poster"
            )
            or ""
        )


    # -----------------------------------------------------
    # TRAILER
    # -----------------------------------------------------

    trailer = get_trailer(
        media_type,
        item.get("id")
    )


    # Keep previous trailer
    # if TMDB temporarily returns nothing
    if (
        not trailer.get(
            "trailer_key"
        )
        and old_item
    ):

        trailer = {

            "trailer_key":
                old_item.get(
                    "trailer_key",
                    ""
                ),

            "trailer_url":
                old_item.get(
                    "trailer_url",
                    ""
                )

        }


    hashtags = generate_hashtags(
        title,
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

        "title":
            title
            or (
                old_item.get(
                    "title"
                )
                if old_item
                else "بدون عنوان"
            ),

        "original_title":
            title
            or (
                old_item.get(
                    "original_title"
                )
                if old_item
                else "بدون عنوان"
            ),

        "original_language":
            original_language
            or (
                old_item.get(
                    "original_language",
                    ""
                )
                if old_item
                else ""
            ),

        "year":
            year
            or (
                old_item.get(
                    "year",
                    ""
                )
                if old_item
                else ""
            ),

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


    # =====================================================
    # LOAD OLD DATABASE
    # =====================================================

    existing_items = load_existing()


    print(
        f"Existing items: "
        f"{len(existing_items)}"
    )


    # =====================================================
    # INDEX OLD ITEMS
    # =====================================================

    existing_map = {}


    for item in existing_items:

        try:

            item_type = (
                "movie"
                if item.get("type")
                == "فيلم"
                else "tv"
            )


            item_id = str(
                item.get(
                    "id"
                )
            )


            if item_id:

                key = (
                    f"{item_type}:"
                    f"{item_id}"
                )


                existing_map[key] = item


        except Exception:

            continue


    # =====================================================
    # FETCH MOVIES
    # =====================================================

    movies = get_all_trending(
        "movie"
    )


    print(
        f"Total movie results: "
        f"{len(movies)}"
    )


    # =====================================================
    # FETCH TV
    # =====================================================

    tv = get_all_trending(
        "tv"
    )


    print(
        f"Total TV results: "
        f"{len(tv)}"
    )


    # =====================================================
    # PROCESS
    # =====================================================

    discovered_map = {}


    # -----------------------------------------------------
    # MOVIES
    # -----------------------------------------------------

    for item in movies:

        if not item.get(
            "poster_path"
        ):

            continue


        item_id = str(
            item.get(
                "id"
            )
        )


        if not item_id:

            continue


        key = (
            f"movie:"
            f"{item_id}"
        )


        try:

            clean = clean_item(
                item,
                "movie",
                existing_map.get(key)
            )


            if clean.get(
                "poster"
            ):

                discovered_map[key] = clean


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


        item_id = str(
            item.get(
                "id"
            )
        )


        if not item_id:

            continue


        key = (
            f"tv:"
            f"{item_id}"
        )


        try:

            clean = clean_item(
                item,
                "tv",
                existing_map.get(key)
            )


            if clean.get(
                "poster"
            ):

                discovered_map[key] = clean


        except Exception as error:

            print(
                "TV processing error:",
                error
            )


    # =====================================================
    # MERGE OLD + NEW
    # =====================================================

    merged = {}


    # -----------------------------------------------------
    # OLD FIRST
    # -----------------------------------------------------

    for key, item in existing_map.items():

        merged[key] = item


    # -----------------------------------------------------
    # NEW / UPDATED
    # -----------------------------------------------------

    for key, item in discovered_map.items():

        merged[key] = item


    results = list(
        merged.values()
    )


    # =====================================================
    # SORT
    #
    # Newest updated items first.
    # =====================================================

    results.sort(

        key=lambda item:
            item.get(
                "updated_at",
                ""
            ),

        reverse=True

    )


    # =====================================================
    # MAXIMUM DATABASE
    # =====================================================

    if len(results) > MAX_ITEMS:

        results = results[
            :MAX_ITEMS
        ]


    # =====================================================
    # SAVE
    # =====================================================

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


    # =====================================================
    # LOG
    # =====================================================

    print(
        "======================================"
    )

    print(
        f"Previously stored: "
        f"{len(existing_items)}"
    )

    print(
        f"Discovered/updated now: "
        f"{len(discovered_map)}"
    )

    print(
        f"Total MOVINS database: "
        f"{len(results)}"
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


    print(
        "======================================"
    )

    print(
        "MOVINS TMDB UPDATE FINISHED"
    )

    print(
        "======================================"
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()

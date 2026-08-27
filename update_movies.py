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
# SETTINGS
# =========================================================

# عدد الصفحات التي يتم جلبها من TMDB
# كل صفحة تحتوي تقريبًا على 20 عملًا.
DISCOVER_PAGES = 20

# الحد الأقصى النهائي للأعمال في الموقع
MAX_ITEMS = 400


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
# TITLE LANGUAGE FILTER
#
# IMPORTANT:
# We do NOT reject a movie because of its original language.
#
# Example:
# Japanese movie + English title = ALLOWED
#
# Japanese title = REJECTED
# Korean title = REJECTED
# Chinese title = REJECTED
#
# Arabic / English / French titles = ALLOWED
# =========================================================

def has_allowed_title(title):

    title = str(
        title or ""
    ).strip()

    if not title:
        return False

    arabic = 0
    latin = 0
    other_letters = 0

    for char in title:

        if not char.isalpha():
            continue

        code = ord(char)

        # -------------------------------------------------
        # Arabic
        # -------------------------------------------------

        if (
            0x0600 <= code <= 0x06FF
            or 0x0750 <= code <= 0x077F
            or 0x08A0 <= code <= 0x08FF
        ):

            arabic += 1

        # -------------------------------------------------
        # Latin
        # -------------------------------------------------

        elif (
            0x0041 <= code <= 0x005A
            or 0x0061 <= code <= 0x007A
            or 0x00C0 <= code <= 0x024F
            or 0x1E00 <= code <= 0x1EFF
        ):

            latin += 1

        else:

            other_letters += 1


    allowed_letters = (
        arabic
        + latin
    )


    total_letters = (
        allowed_letters
        + other_letters
    )


    if total_letters == 0:

        return False


    # -----------------------------------------------------
    # Reject titles mainly written in
    # non-Arabic / non-Latin scripts.
    # -----------------------------------------------------

    return (
        allowed_letters > 0
        and
        allowed_letters >= other_letters
    )


# =========================================================
# HTTP HELPER
# =========================================================

def tmdb_get(
    endpoint,
    params=None
):

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
        "language": "ar-SA",
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
# GET MANY DISCOVERED ITEMS
# =========================================================

def get_discover(
    media_type
):

    results = []


    for page in range(
        1,
        DISCOVER_PAGES + 1
    ):

        print(
            f"Fetching {media_type} page {page}/"
            f"{DISCOVER_PAGES}..."
        )


        endpoint = (
            f"/discover/"
            f"{media_type}"
        )


        params = {

            "language":
                "ar-SA",

            "page":
                page,

            "include_adult":
                "false",

            "sort_by":
                "popularity.desc",

            "vote_count.gte":
                5,

        }


        try:

            data = tmdb_get(
                endpoint,
                params
            )


            page_results = data.get(
                "results",
                []
            )


            results.extend(
                page_results
            )


            if not page_results:

                break


        except Exception as error:

            print(
                f"Discover warning "
                f"{media_type} page {page}:",
                error
            )

            break


    return results


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
    # Original language
    # -----------------------------------------------------

    if original_language in KEEP_ORIGINAL_TITLE_LANGUAGES:

        original_poster = find_language(
            original_language
        )


        if original_poster:

            return original_poster


    # -----------------------------------------------------
    # Foreign languages
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
    # Neutral poster
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
    # English fallback
    # -----------------------------------------------------

    english_poster = find_language(
        "en"
    )


    if english_poster:

        return english_poster


    # -----------------------------------------------------
    # Arabic fallback
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

            selected = official_trailers[0]

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
# SELECT DISPLAY TITLE
#
# Priority:
# 1. Arabic translated title
# 2. English title
# 3. French title
# 4. Original title only if allowed
# =========================================================

def get_display_title(
    item,
    media_type
):

    if media_type == "movie":

        arabic_title = (
            item.get(
                "title"
            )
            or ""
        ).strip()


        original_title = (
            item.get(
                "original_title"
            )
            or ""
        ).strip()


    else:

        arabic_title = (
            item.get(
                "name"
            )
            or ""
        ).strip()


        original_title = (
            item.get(
                "original_name"
            )
            or ""
        ).strip()


    # -----------------------------------------------------
    # If Arabic title returned by TMDB is actually Arabic
    # -----------------------------------------------------

    if (
        arabic_title
        and has_allowed_title(
            arabic_title
        )
    ):

        return arabic_title


    # -----------------------------------------------------
    # Original title may be English / French
    # -----------------------------------------------------

    if (
        original_title
        and has_allowed_title(
            original_title
        )
    ):

        return original_title


    return ""


# =========================================================
# CLEAN ITEM
# =========================================================

def clean_item(
    item,
    media_type
):

    title = get_display_title(
        item,
        media_type
    )


    # -----------------------------------------------------
    # IMPORTANT:
    # Reject only if the DISPLAYED title is written in
    # an unwanted script.
    #
    # Original language does NOT matter.
    # -----------------------------------------------------

    if not title:

        return None


    if not has_allowed_title(
        title
    ):

        return None


    if media_type == "movie":

        date = (
            item.get(
                "release_date"
            )
        )

    else:

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


    if not overview:

        overview = (
            "لا يوجد ملخص "
            "متوفر حاليًا."
        )


    genres = get_genres(
        item,
        media_type
    )


    detailed_type = (
        get_detailed_type(
            media_type,
            genres
        )
    )


    # =====================================================
    # RATING
    # =====================================================

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


    # =====================================================
    # POPULARITY
    # =====================================================

    try:

        popularity = float(
            item.get(
                "popularity"
            )
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        popularity = 0.0


    # =====================================================
    # VOTE COUNT
    # =====================================================

    try:

        vote_count = int(
            item.get(
                "vote_count"
            )
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        vote_count = 0


    poster = get_best_poster(
        media_type,
        item
    )


    trailer = get_trailer(
        media_type,
        item.get("id")
    )


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
            title,

        "original_title":
            title,

        "original_language":
            original_language,

        "year":
            year,

        "overview":
            overview,

        "rating":
            rating,

        "popularity":
            popularity,

        "vote_count":
            vote_count,

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
    # TRENDING MOVIES
    # =====================================================

    print(
        "Fetching trending movies..."
    )


    trending_movies = get_trending(
        "movie"
    )


    print(
        f"Trending movies received: "
        f"{len(trending_movies)}"
    )


    # =====================================================
    # TRENDING TV
    # =====================================================

    print(
        "Fetching trending TV..."
    )


    trending_tv = get_trending(
        "tv"
    )


    print(
        f"Trending TV received: "
        f"{len(trending_tv)}"
    )


    # =====================================================
    # DISCOVER MOVIES
    # =====================================================

    print(
        "Fetching popular movies..."
    )


    movies = get_discover(
        "movie"
    )


    print(
        f"Discover movies received: "
        f"{len(movies)}"
    )


    # =====================================================
    # DISCOVER TV
    # =====================================================

    print(
        "Fetching popular TV..."
    )


    tv = get_discover(
        "tv"
    )


    print(
        f"Discover TV received: "
        f"{len(tv)}"
    )


    # =====================================================
    # COMBINE
    #
    # Trending first because these are currently popular.
    # =====================================================

    movie_items = (
        trending_movies
        + movies
    )


    tv_items = (
        trending_tv
        + tv
    )


    results = []


    # =====================================================
    # MOVIES
    # =====================================================

    for item in movie_items:

        if not item.get(
            "poster_path"
        ):

            continue


        try:

            clean = clean_item(
                item,
                "movie"
            )


            if clean and clean.get(
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


    # =====================================================
    # TV
    # =====================================================

    for item in tv_items:

        if not item.get(
            "poster_path"
        ):

            continue


        try:

            clean = clean_item(
                item,
                "tv"
            )


            if clean and clean.get(
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


    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

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


    # =====================================================
    # SORT BY POPULARITY
    #
    # Most popular works appear first.
    # =====================================================

    results.sort(

        key=lambda item:
            (
                float(
                    item.get(
                        "popularity",
                        0
                    )
                    or 0
                )
            ),

        reverse=True

    )


    # =====================================================
    # LIMIT
    # =====================================================

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
        f"MOVINS: "
        f"{len(results)} items saved."
    )


    print(
        "======================================"
    )


    for item in results[:20]:

        print(
            f"{item.get('detailed_type')}: "
            f"{item.get('title')} | "
            f"Popularity: "
            f"{item.get('popularity', 0):.2f} | "
            f"Rating: "
            f"{item.get('rating')} | "
            f"Votes: "
            f"{item.get('vote_count', 0)} | "
            f"Trailer: "
            f"{'YES' if item.get('trailer_url') else 'NO'}"
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()

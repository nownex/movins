import json
import os
from datetime import datetime, timezone

import requests


# =========================================================
# MOVINS — TMDB MOVIE & TV UPDATE ENGINE
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
# GET TRENDING
# =========================================================

def get_trending(media_type):

    url = f"{BASE_URL}/trending/{media_type}/week"

    params = {
        # الملخص باللغة العربية
        "language": "ar-SA",

        # لا نطلب ترجمة العنوان.
        # العنوان الأصلي سنأخذه من original_title/original_name.
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


    # =====================================================
    # PRIORITY GENRES
    # =====================================================

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


    # =====================================================
    # FIND MOST IMPORTANT GENRE
    # =====================================================

    selected = None

    for genre in priority:

        for item in genres:

            if genre in item:

                selected = item

                break

        if selected:
            break


    if selected:

        # تبسيط بعض التصنيفات الطويلة

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
    title,
    media_type,
    genres
):

    hashtags = []


    # =====================================================
    # BASE HASHTAGS
    # =====================================================

    hashtags.append("#MOVINS")

    if media_type == "movie":
        hashtags.append("#أفلام")
        hashtags.append("#فيلم")
    else:
        hashtags.append("#مسلسلات")
        hashtags.append("#مسلسل")


    # =====================================================
    # GENRE HASHTAGS
    # =====================================================

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

        hashtag = genre_hashtags.get(
            genre
        )

        if hashtag and hashtag not in hashtags:

            hashtags.append(
                hashtag
            )


    # =====================================================
    # ENGLISH GENERIC HASHTAGS
    # =====================================================

    hashtags.append("#Movies")
    hashtags.append("#TVShows")


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

    # =====================================================
    # ORIGINAL TITLE
    #
    # مهم جداً:
    #
    # لا نستخدم title / name وحدهما
    # لأن TMDB قد يعيدهما مترجمين حسب اللغة.
    #
    # نستخدم:
    #
    # movie  -> original_title
    # tv     -> original_name
    #
    # وبالتالي:
    #
    # English -> يبقى English
    # Korean  -> يبقى Korean
    # Arabic  -> يبقى Arabic
    # French  -> يبقى French
    #
    # =====================================================

    if media_type == "movie":

        title = (
            item.get("original_title")
            or item.get("title")
            or "بدون عنوان"
        )

        date = item.get(
            "release_date"
        )

    else:

        title = (
            item.get("original_name")
            or item.get("name")
            or "بدون عنوان"
        )

        date = item.get(
            "first_air_date"
        )


    # =====================================================
    # YEAR
    # =====================================================

    year = ""

    if date:

        try:

            year = date[:4]

        except Exception:

            year = ""


    # =====================================================
    # ARABIC OVERVIEW
    #
    # لأن طلب TMDB يستخدم language=ar-SA
    # فإن overview سيكون بالعربية عندما تكون
    # الترجمة متوفرة لدى TMDB.
    #
    # =====================================================

    overview = (
        item.get("overview")
        or ""
    ).strip()


    if not overview:

        overview = (
            "لا يوجد ملخص متوفر حاليًا."
        )


    # =====================================================
    # GENRES
    # =====================================================

    genres = get_genres(
        item,
        media_type
    )


    # =====================================================
    # DETAILED TYPE
    # =====================================================

    detailed_type = get_detailed_type(
        media_type,
        genres
    )


    # =====================================================
    # RATING
    # =====================================================

    try:

        rating = round(
            float(
                item.get(
                    "vote_average",
                    0
                ) or 0
            ),
            1
        )

    except Exception:

        rating = 0


    # =====================================================
    # POSTER
    # =====================================================

    poster = ""

    if item.get("poster_path"):

        poster = (
            IMAGE_BASE
            + item["poster_path"]
        )


    # =====================================================
    # HASHTAGS
    # =====================================================

    hashtags = create_hashtags(
        title,
        media_type,
        genres
    )


    # =====================================================
    # RESULT
    # =====================================================

    return {

        "id":
            item.get("id"),

        # النوع الأساسي
        "type":
            (
                "فيلم"
                if media_type == "movie"
                else "مسلسل"
            ),

        # النوع التفصيلي
        #
        # مثال:
        # فيلم أكشن
        # فيلم كوميديا
        # مسلسل دراما
        # مسلسل أكشن
        #
        "detailed_type":
            detailed_type,

        # جميع التصنيفات
        "genres":
            genres,

        # العنوان الأصلي
        "title":
            title,

        "year":
            year,

        # الملخص العربي
        "overview":
            overview,

        "rating":
            rating,

        "poster":
            poster,

        # هاشتاقات فيسبوك
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
        "MOVINS — Updating TMDB data"
    )

    print(
        "======================================"
    )


    # =====================================================
    # GET MOVIES
    # =====================================================

    print(
        "Getting trending movies..."
    )

    movies = get_trending(
        "movie"
    )


    print(
        f"Movies received: {len(movies)}"
    )


    # =====================================================
    # GET TV
    # =====================================================

    print(
        "Getting trending TV shows..."
    )

    tv = get_trending(
        "tv"
    )


    print(
        f"TV shows received: {len(tv)}"
    )


    # =====================================================
    # BUILD RESULTS
    # =====================================================

    results = []


    # =====================================================
    # MOVIES
    # =====================================================

    for item in movies:

        if not item.get(
            "poster_path"
        ):
            continue


        try:

            cleaned = clean_item(
                item,
                "movie"
            )

            results.append(
                cleaned
            )

        except Exception as error:

            print(
                "Movie error:",
                error
            )


    # =====================================================
    # TV
    # =====================================================

    for item in tv:

        if not item.get(
            "poster_path"
        ):
            continue


        try:

            cleaned = clean_item(
                item,
                "tv"
            )

            results.append(
                cleaned
            )

        except Exception as error:

            print(
                "TV error:",
                error
            )


    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

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


    # =====================================================
    # LIMIT
    # =====================================================

    results = results[:30]


    # =====================================================
    # FINAL DATA
    # =====================================================

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


    # =====================================================
    # SAVE JSON
    # =====================================================

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


    # =====================================================
    # LOG
    # =====================================================

    print(
        "======================================"
    )

    print(
        f"MOVINS: {len(results)} items saved."
    )

    print(
        "======================================"
    )


    # =====================================================
    # SHOW SAMPLE
    # =====================================================

    if results:

        print(
            "Sample:"
        )

        for item in results[:5]:

            print(
                f"- {item['title']} | "
                f"{item['detailed_type']} | "
                f"{item['rating']}"
            )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()

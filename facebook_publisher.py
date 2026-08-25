import json
import os
import requests
from datetime import datetime, timezone


# =========================================================
# NOWNEX / MOVINS — FACEBOOK PUBLISHER
# =========================================================

TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing."
    )


GRAPH_VERSION = "v26.0"

GRAPH_URL = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}/me/photos"
)


# =========================================================
# FILES
# =========================================================

POSTED_FILE = "posted_movies.json"


# =========================================================
# MOVINS WEBSITE
# =========================================================

SITE_URL = "https://nownex.github.io/movins/"


# =========================================================
# LOAD JSON
# =========================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"WARNING: Could not read {filename}: {e}"
        )

        return default


# =========================================================
# SAVE JSON
# =========================================================

def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# POSTED MOVIES
# =========================================================

posted_movies = load_json(
    POSTED_FILE,
    []
)


# =========================================================
# NORMALIZE POSTED IDS
# =========================================================

def normalize_posted_id(item):

    if isinstance(item, dict):

        item_type = str(
            item.get("type", "")
        ).strip().lower()

        item_id = str(
            item.get("id", "")
        ).strip()

        if item_type and item_id:

            return (
                f"{item_type}:{item_id}"
            )

        if item_id:

            return item_id


    return str(item).strip()


posted_keys = set(
    normalize_posted_id(item)
    for item in posted_movies
)


# =========================================================
# MOVIE TYPE
# =========================================================

def get_media_type(item):

    item_type = str(
        item.get("type", "")
    ).strip().lower()


    if item_type in (
        "فيلم",
        "movie",
        "film"
    ):

        return "movie"


    return "tv"


# =========================================================
# MOVIE ID
# =========================================================

def get_movie_id(item):

    return str(
        item.get("id", "")
    ).strip()


# =========================================================
# UNIQUE KEY
# =========================================================

def get_movie_key(item):

    media_type = get_media_type(
        item
    )

    movie_id = get_movie_id(
        item
    )


    if not movie_id:

        return ""


    return (
        f"{media_type}:{movie_id}"
    )


# =========================================================
# IMPORTANT:
# EXACT MOVIE / SERIES URL
#
# Example:
#
# https://nownex.github.io/movins/?movie=tv-123
#
# This is the URL Facebook receives.
# The MOVINS HTML reads this URL and opens
# the exact movie card automatically.
# =========================================================

def build_movie_url(item):

    media_type = get_media_type(
        item
    )

    movie_id = get_movie_id(
        item
    )


    if not movie_id:

        return SITE_URL


    return (
        SITE_URL +
        "?movie=" +
        f"{media_type}-{movie_id}"
    )


# =========================================================
# HASHTAGS
# =========================================================

def build_hashtags(item):

    hashtags = item.get(
        "hashtags",
        ""
    )


    if isinstance(
        hashtags,
        list
    ):

        hashtags = " ".join(
            str(x)
            for x in hashtags
        )


    hashtags = str(
        hashtags
    ).strip()


    if hashtags:

        return hashtags


    return "#MOVINS #أفلام #مسلسلات"


# =========================================================
# GENRES
# =========================================================

def build_genres(item):

    genres = item.get(
        "genres",
        []
    )


    if not isinstance(
        genres,
        list
    ):

        return ""


    clean_genres = []

    for genre in genres:

        genre = str(
            genre
        ).strip()


        if genre:

            clean_genres.append(
                genre
            )


    return " • ".join(
        clean_genres
    )


# =========================================================
# CAPTION
# =========================================================

def build_caption(item):

    title = str(
        item.get(
            "title",
            "بدون عنوان"
        )
    ).strip()


    overview = str(
        item.get(
            "overview",
            "اكتشف تفاصيل هذا العمل على MOVINS."
        )
    ).strip()


    year = str(
        item.get(
            "year",
            ""
        )
    ).strip()


    detailed_type = str(
        item.get(
            "detailed_type",
            item.get(
                "type",
                "عمل"
            )
        )
    ).strip()


    rating = item.get(
        "rating",
        ""
    )


    try:

        rating_text = (
            f"{float(rating):.1f}"
        )

    except Exception:

        rating_text = (
            str(rating)
            if rating
            else ""
        )


    genres = build_genres(
        item
    )


    movie_url = build_movie_url(
        item
    )


    hashtags = build_hashtags(
        item
    )


    lines = []


    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    lines.append(
        f"🎬 {title}"
    )


    lines.append("")


    # -----------------------------------------------------
    # TYPE / YEAR
    # -----------------------------------------------------

    info = []


    if detailed_type:

        info.append(
            detailed_type
        )


    if year:

        info.append(
            year
        )


    if info:

        lines.append(
            " • ".join(info)
        )


    # -----------------------------------------------------
    # RATING
    # -----------------------------------------------------

    if rating_text:

        lines.append(
            f"⭐ التقييم: {rating_text}/10"
        )


    # -----------------------------------------------------
    # GENRES
    # -----------------------------------------------------

    if genres:

        lines.append(

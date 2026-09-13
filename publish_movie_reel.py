import json
import os
import sys
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests


# =========================================================
# MOVINS — AUTOMATIC MOVIE REEL MAKER
# =========================================================

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

GRAPH_VERSION = "v26.0"
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

FACEBOOK_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

SITE_URL = "https://nownex.github.io/movins/"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_DURATION = 12


# =========================================================
# CHECK SECRETS
# =========================================================

if not FACEBOOK_PAGE_TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing."
    )

if not TMDB_API_KEY:
    raise RuntimeError(
        "TMDB_API_KEY is missing."
    )


# =========================================================
# JSON HELPERS
# =========================================================

def load_json(filename, default):

    path = Path(filename)

    if not path.exists():
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as e:

        print(
            f"WARNING: Could not read {filename}: {e}"
        )

        return default


def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# FACEBOOK PAGE
# =========================================================

def get_page_info():

    url = f"{GRAPH_URL}/me"

    params = {
        "fields": "id,name",
        "access_token": FACEBOOK_PAGE_TOKEN
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    if not response.ok:

        raise RuntimeError(
            "Could not get Facebook Page information:\n"
            + response.text
        )

    data = response.json()

    page_id = data.get("id")

    if not page_id:

        raise RuntimeError(
            "Facebook did not return Page ID:\n"
            + json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            )
        )

    print(
        f"Facebook Page: "
        f"{data.get('name', 'Unknown')}"
    )

    print(
        f"Facebook Page ID: {page_id}"
    )

    return page_id


# =========================================================
# MOVIES
# =========================================================

def load_movies():

    data = load_json(
        MOVIES_FILE,
        {}
    )

    if isinstance(data, dict):

        items = data.get(
            "items",
            []
        )

    elif isinstance(data, list):

        items = data

    else:

        items = []

    if not isinstance(items, list):
        return []

    return items


def load_posted():

    data = load_json(
        POSTED_FILE,
        []
    )

    if isinstance(data, dict):

        data = data.get(
            "items",
            []
        )

    if not isinstance(data, list):
        return []

    return data


def movie_id(movie):

    return str(
        movie.get("tmdb_id")
        or movie.get("id")
        or ""
    ).strip()


def movie_type(movie):

    value = str(
        movie.get("media_type")
        or movie.get("type")
        or ""
    ).lower()

    if value in (
        "tv",
        "series",
        "مسلسل",
        "series_tv"
    ):

        return "tv"

    return "movie"


def movie_title(movie):

    return str(
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "MOVINS"
    ).strip()


def movie_year(movie):

    if movie.get("year"):

        return str(
            movie.get("year")
        )

    date_value = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or ""
    )

    return str(date_value)[:4]


def movie_rating(movie):

    try:

        return float(
            movie.get(
                "rating",
                0
            ) or 0
        )

    except Exception:

        return 0.0


def movie_popularity(movie):

    try:

        return float(
            movie.get(
                "popularity",
                0
            ) or 0
        )

    except Exception:

        return 0.0


# =========================================================
# POSTER
# =========================================================

def get_poster_url(movie):

    poster = movie.get(
        "poster"
    )

    if not poster:
        return None

    poster = str(
        poster
    ).strip()

    if poster.startswith(
        "http://"
    ) or poster.startswith(
        "https://"
    ):

        return poster

    if poster.startswith("/"):

        return (
            "https://image.tmdb.org/t/p/w780"
            + poster
        )

    return None


# =========================================================
# SELECT MOVIE
# =========================================================

def choose_movie(
    movies,
    posted
):

    posted_ids = {
        str(
            item.get("id")
        )
        for item in posted
        if isinstance(
            item,
            dict
        )
    }

    candidates = []

    for movie in movies:

        if not isinstance(
            movie,
            dict
        ):
            continue

        mid = movie_id(
            movie
        )

        if not mid:
            continue

        if mid in posted_ids:
            continue

        poster = get_poster_url(
            movie
        )

        if not poster:
            continue

        popularity = movie_popularity(
            movie
        )

        rating = movie_rating(
            movie
        )

        candidates.append(
            (
                popularity,
                rating,
                movie
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1]
        ),
        reverse=True
    )

    return candidates[0][2]


# =========================================================
# DOWNLOAD POSTER
# =========================================================

def download_poster(
    poster_url
):

    print(
        "Downloading movie poster..."
    )

    response = requests.get(
        poster_url,
        timeout=60
    )

    response.raise_for_status()

    content_type = (
        response.headers
        .get(
            "content-type",
            ""
        )
        .lower()
    )

    if "image" not in content_type:

        raise RuntimeError(
            "Poster URL is not an image."
        )

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".jpg"
    )

    temp.write(
        response.content
    )

    temp.close()

    print(
        f"Poster downloaded: "
        f"{len(response.content) / 1024:.1f} KB"
    )

    return temp.name


# =========================================================
# TEXT FILE
# =========================================================

def write_text_file(text):

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".txt",
        mode="w",
        encoding="utf-8"
    )

    temp.write(
        str(text)
    )

    temp.close()

    return temp.name


# =========================================================
# CREATE CINEMATIC REEL
# =========================================================

def create_reel(
    movie,
    poster_path
):

    title = movie_title(
        movie
    )

    year = movie_year(
        movie
    )

    rating = movie_rating(
        movie
    )

    media = movie_type(
        movie
    )

    if media == "tv":
        media_label = "SERIES"
    else:
        media_label = "MOVIE"

    output = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4"
    )

    output.close()

    title_file = write_text_file(
        title
    )

    year_file = write_text_file(
        year
    )

    rating_file = write_text_file(
        f"★ {rating:.1f}/10"
    )

    type_file = write_text_file(
        media_label
    )

    # =====================================================
    # Noto font
    # Supports Arabic and Latin text.
    # =====================================================

    font = (
        "/usr/share/fonts/truetype/noto/"
        "NotoSansArabic-Regular.ttf"
    )

    if not os.path.exists(font):

        font = (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        )

    # =====================================================
    # FILTER
    # =====================================================

    filter_complex = (

        # -------------------------------------------------
        # Background image + cinematic zoom
        # -------------------------------------------------

        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0008,1.12)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=360:"
        "s=1080x1920:"
        "fps=30,"
        "setsar=1,"
        "eq="
        "brightness=-0.08:"
        "contrast=1.08"
        "[bg];"

        # -------------------------------------------------
        # Cinematic dark overlay
        # -------------------------------------------------

        "color="
        "c=black@0.25:"
        "s=1080x1920:"
        "d=12"
        "[shade];"

        "[bg][shade]"
        "overlay=0:0"
        "[v1];"

        # -------------------------------------------------
        # Bottom information panel
        # -------------------------------------------------

        "[v1]"
        "drawbox="
        "x=0:"
        "y=1280:"
        "w=1080:"
        "h=640:"
        "color=black@0.72:"
        "t=fill"
        "[v2];"

        # -------------------------------------------------
        # MOVIE / SERIES
        # -------------------------------------------------

        "[v2]"
        "drawtext="
        f"fontfile='{font}':"
        f"textfile='{type_file}':"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1350:"
        "text_shaping=1:"
        "alpha='if(lt(t,1),t,1)'"
        "[v3];"

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        "[v3]"
        "drawtext="
        f"fontfile='{font}':"
        f"textfile='{title_file}':"
        "fontcolor=white:"
        "fontsize=68:"
        "x=(w-text_w)/2:"
        "y=143

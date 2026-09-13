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
    raise RuntimeError("FACEBOOK_PAGE_TOKEN is missing.")

if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY is missing.")


# =========================================================
# JSON HELPERS
# =========================================================

def load_json(filename, default):
    path = Path(filename)

    if not path.exists():
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as error:
        print(f"WARNING: Could not read {filename}: {error}")
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
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
        f"Facebook Page: {data.get('name', 'Unknown')}"
    )

    print(
        f"Facebook Page ID: {page_id}"
    )

    return page_id


# =========================================================
# MOVIE DATA
# =========================================================

def load_movies():
    data = load_json(
        MOVIES_FILE,
        {}
    )

    if isinstance(data, dict):
        items = data.get("items", [])

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
        data = data.get("items", [])

    if not isinstance(data, list):
        return []

    return data


def get_movie_id(movie):
    return str(
        movie.get("tmdb_id")
        or movie.get("id")
        or ""
    ).strip()


def get_movie_type(movie):
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


def get_movie_title(movie):
    return str(
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "MOVINS"
    ).strip()


def get_movie_year(movie):
    year = movie.get("year")

    if year:
        return str(year)

    date_value = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or ""
    )

    return str(date_value)[:4]


def get_movie_rating(movie):
    try:
        return float(
            movie.get("rating", 0) or 0
        )

    except Exception:
        return 0.0


def get_movie_popularity(movie):
    try:
        return float(
            movie.get("popularity", 0) or 0
        )

    except Exception:
        return 0.0


# =========================================================
# POSTER
# =========================================================

def get_poster_url(movie):
    poster = movie.get("poster")

    if not poster:
        return None

    poster = str(poster).strip()

    if poster.startswith("http://"):
        return poster

    if poster.startswith("https://"):
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

def choose_movie(movies, posted):

    posted_ids = set()

    for item in posted:
        if isinstance(item, dict):
            value = item.get("id")

            if value is not None:
                posted_ids.add(
                    str(value)
                )

    candidates = []

    for movie in movies:

        if not isinstance(movie, dict):
            continue

        movie_id = get_movie_id(movie)

        if not movie_id:
            continue

        if movie_id in posted_ids:
            continue

        poster_url = get_poster_url(movie)

        if not poster_url:
            continue

        popularity = get_movie_popularity(movie)
        rating = get_movie_rating(movie)

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

def download_poster(poster_url):

    print("Downloading movie poster...")

    response = requests.get(
        poster_url,
        timeout=60
    )

    response.raise_for_status()

    content_type = (
        response.headers
        .get("content-type", "")
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
        "Poster downloaded: "
        f"{len(response.content) / 1024:.1f} KB"
    )

    return temp.name


# =========================================================
# TEXT FILE
# =========================================================

def create_text_file(text):

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
# FIND FONT
# =========================================================

def find_font():

    possible_fonts = [

        "/usr/share/fonts/truetype/noto/"
        "NotoSansArabic-Regular.ttf",

        "/usr/share/fonts/opentype/noto/"
        "NotoSansArabic-Regular.ttf",

        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans.ttf"
    ]

    for font in possible_fonts:

        if os.path.exists(font):
            print(
                f"Using font: {font}"
            )

            return font

    raise RuntimeError(
        "No compatible font found."
    )


# =========================================================
# CREATE REEL
# =========================================================

def create_reel(movie, poster_path):

    title = get_movie_title(movie)
    year = get_movie_year(movie)
    rating = get_movie_rating(movie)

    media_type = get_movie_type(movie)

    if media_type == "tv":
        type_text = "SERIES"
    else:
        type_text = "MOVIE"

    font = find_font()

    title_file = create_text_file(
        title
    )

    year_file = create_text_file(
        year
    )

    rating_file = create_text_file(
        f"★ {rating:.1f}/10"
    )

    type_file = create_text_file(
        type_text
    )

    output_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4"
    )

    output_path = output_file.name

    output_file.close()

    # =====================================================
    # IMPORTANT
    # Simple and compatible FFmpeg filter.
    # No unsupported fontweight option.
    # =====================================================

    filter_complex = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0007,1.10)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=360:"
        "s=1080x1920:"
        "fps=30,"
        "setsar=1"
        "[bg];"

        "[bg]"
        "drawbox="
        "x=0:"
        "y=1260:"
        "w=1080:"
        "h=660:"
        "color=black@0.70:"
        "t=fill"
        "[panel];"

        "[panel]"
        "drawtext="
        f"fontfile={font}:"
        f"textfile={type_file}:"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1335"
        "[t1];"

        "[t1]"
        "drawtext="
        f"fontfile={font}:"
        f"textfile={title_file}:"
        "fontcolor=white:"
        "fontsize=68:"
        "x=(w-text_w)/2:"
        "y=1420"
        "[t2];"

        "[t2]"
        "drawtext="
        f"fontfile={font}:"
        f"textfile={year_file}:"
        "fontcolor=white:"
        "fontsize=40:"
        "x=(w-text_w)/2:"
        "y=1535"
        "[t3];"

        "[t3]"
        "drawtext="
        f"fontfile={font}:"
        f"textfile={rating_file}:"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1610"
        "[t4];"

        "[t4]"
        "drawtext="
        f"fontfile={font}:"
        "text=MOVINS:"
        "fontcolor=white:"
        "fontsize=38:"
        "x=(w-text_w)/2:"
        "y=1740"
        "[t5];"

        "[t5]"
        "drawtext="
        f"fontfile={font

import os
import json
import time
import math
import wave
import struct
import shutil
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


# =========================================================
# MOVINS — CINEMATIC REEL PUBLISHER
# =========================================================

GRAPH_VERSION = "v26.0"

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

WORK_DIR = Path("reel_work")

POSTER_FILE = WORK_DIR / "poster.jpg"
DESIGN_FILE = WORK_DIR / "design.jpg"
AUDIO_FILE = WORK_DIR / "cinematic_music.wav"
VIDEO_FILE = WORK_DIR / "movins_reel.mp4"

WIDTH = 1080
HEIGHT = 1920

DURATION = 12
FPS = 30
SAMPLE_RATE = 44100

FACEBOOK_PAGE_TOKEN = os.environ.get(
    "FACEBOOK_PAGE_TOKEN"
)

TMDB_API_KEY = os.environ.get(
    "TMDB_API_KEY"
)


# =========================================================
# CHECK SECRETS
# =========================================================

if not FACEBOOK_PAGE_TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing."
    )

if not TMDB_API_KEY:
    print(
        "WARNING: TMDB_API_KEY is missing.",
        flush=True
    )


# =========================================================
# LOG
# =========================================================

def log(text=""):
    print(
        str(text),
        flush=True
    )


# =========================================================
# RUN COMMAND
# =========================================================

def run_command(command):

    log("")
    log("RUNNING:")
    log(
        " ".join(
            str(x)
            for x in command
        )
    )
    log("")

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    if result.stdout:
        print(
            result.stdout,
            flush=True
        )

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed with exit code "
            + str(result.returncode)
        )


# =========================================================
# LOAD JSON
# =========================================================

def load_json(
    path,
    default
):

    if not os.path.exists(path):
        return default

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        log(
            "JSON warning: "
            + str(e)
        )

        return default


# =========================================================
# SAVE JSON
# =========================================================

def save_json(
    path,
    data
):

    with open(
        path,
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
# CLEAN WORK DIRECTORY
# =========================================================

def clean_work():

    if WORK_DIR.exists():

        for item in WORK_DIR.iterdir():

            try:

                if item.is_file():
                    item.unlink()

                elif item.is_dir():
                    shutil.rmtree(item)

            except Exception:
                pass

    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# =========================================================
# LOAD MOVIES
# =========================================================

def load_movies():

    data = load_json(
        MOVIES_FILE,
        {"items": []}
    )

    if isinstance(
        data,
        dict
    ):

        items = data.get(
            "items",
            []
        )

    elif isinstance(
        data,
        list
    ):

        items = data

    else:

        items = []

    if not isinstance(
        items,
        list
    ):

        items = []

    return items


# =========================================================
# LOAD POSTED HISTORY
# =========================================================

def load_posted():

    data = load_json(
        POSTED_FILE,
        []
    )

    if isinstance(
        data,
        list
    ):

        return data

    if isinstance(
        data,
        dict
    ):

        return data.get(
            "items",
            []
        )

    return []


# =========================================================
# GET POSTED IDS
# =========================================================

def posted_ids(
    posted
):

    result = set()

    for item in posted:

        if isinstance(
            item,
            dict
        ):

            value = (
                item.get("id")
                or item.get("tmdb_id")
                or item.get("movie_id")
            )

        else:

            value = item

        if value is not None:

            result.add(
                str(value)
            )

    return result


# =========================================================
# MOVIE ID
# =========================================================

def movie_id(
    movie
):

    value = (
        movie.get("id")
        or movie.get("tmdb_id")
    )

    if value is None:
        return None

    return str(value)


# =========================================================
# MEDIA TYPE
# =========================================================

def movie_prefix(
    movie
):

    value = (
        movie.get("detailed_type")
        or movie.get("type")
        or movie.get("media_type")
        or ""
    )

    text = str(
        value
    ).lower()

    if (
        "مسلسل" in text
        or "tv" in text
        or "series" in text
        or "show" in text
    ):

        return "tv"

    return "movie"


# =========================================================
# DISPLAY TYPE
# =========================================================

def movie_type(
    movie
):

    if movie_prefix(movie) == "tv":
        return "TV SERIES"

    return "MOVIE"


# =========================================================
# ARABIC DETECTION
# =========================================================

def contains_arabic(
    text
):

    if not text:
        return False

    for char in str(text):

        if (
            "\u0600" <= char <= "\u06ff"
            or "\u0750" <= char <= "\u077f"
            or "\u08a0" <= char <= "\u08ff"
        ):

            return True

    return False


# =========================================================
# TMDB REQUEST
#
# IMPORTANT:
# TMDB_API_KEY contains the TMDB v4
# Read Access Token.
#
# Therefore we use:
#
# Authorization: Bearer TOKEN
# =========================================================

def tmdb_get(
    endpoint,
    params=None
):

    if not TMDB_API_KEY:

        log(
            "TMDB_API_KEY is missing."
        )

        return None

    request_params = {}

    if params:

        request_params.update(
            params
        )

    headers = {
        "Authorization":
            "Bearer "
            + TMDB_API_KEY,

        "accept":
            "application/json"
    }

    try:

        response = requests.get(
            endpoint,
            params=request_params,
            headers=headers,
            timeout=20
        )

        log(
            "TMDB status: "
            + str(
                response.status_code
            )
        )

        if not response.ok:

            log(
                "TMDB request failed:"
            )

            log(
                response.text[:1000]
            )

            return None

        return response.json()

    except Exception as e:

        log(
            "TMDB request error: "
            + str(e)
        )

        return None


# =========================================================
# GET TMDB DETAILS
# =========================================================

def get_tmdb_details(
    mid,
    media_type
):

    if not mid:

        return None

    if media_type == "tv":

        endpoint = (
            "https://api.themoviedb.org/3/tv/"
            + str(mid)
        )

    else:

        endpoint = (
            "https://api.themoviedb.org/3/movie/"
            + str(mid)
        )

    log("")
    log(
        "======================================"
    )

    log(
        "TMDB TITLE LOOKUP"
    )

    log(
        "TMDB ID: "
        + str(mid)
    )

    log(
        "Media type: "
        + str(media_type)
    )

    log(
        "Endpoint:"
    )

    log(
        endpoint
    )

    log(
        "======================================"
    )

    data = tmdb_get(
        endpoint,
        {
            "language": "en-US"
        }
    )

    if data:

        log(
            "TMDB details received successfully."
        )

        return data

    return None


# =========================================================
# GET ENGLISH TITLE FROM TMDB
# =========================================================

def get_english_tmdb_title(
    mid,
    media_type
):

    if not mid:

        return None

    data = get_tmdb_details(
        mid,
        media_type
    )

    if not data:

        log(
            "TMDB returned no details."
        )

        return None

    log("")
    log(
        "TMDB title fields:"
    )

    log(
        json.dumps(
            {
                "name":
                    data.get("name"),

                "title":
                    data.get("title"),

                "original_name":
                    data.get(
                        "original_name"
                    ),

                "original_title":
                    data.get(
                        "original_title"
                    )
            },
            ensure_ascii=False
        )
    )

    if media_type == "tv":

        fields = [
            "name",
            "original_name"
        ]

    else:

        fields = [
            "title",
            "original_title"
        ]

    for field in fields:

        value = data.get(
            field
        )

        if not value:
            continue

        value = str(
            value
        ).strip()

        if not value:
            continue

        if not contains_arabic(
            value
        ):

            log("")
            log(
                "ENGLISH TITLE FOUND:"
            )

            log(
                value
            )

            return value

    log(
        "TMDB did not return an English title."
    )

    return None


# =========================================================
# MOVIE TITLE
#
# TMDB FIRST
# =========================================================

def movie_title(
    movie
):

    mid = movie_id(
        movie
    )

    media_type = movie_prefix(
        movie
    )

    log("")
    log(
        "Finding English title..."
    )

    log(
        "TMDB ID: "
        + str(mid)
    )

    log(
        "Media type: "
        + media_type
    )

    # =====================================================
    # 1. TMDB
    # =====================================================

    if mid and TMDB_API_KEY:

        tmdb_title = (
            get_english_tmdb_title(
                mid,
                media_type
            )
        )

        if tmdb_title:

            log(
                "USING TMDB TITLE:"
            )

            log(
                tmdb_title
            )

            return tmdb_title

    # =====================================================
    # 2. LOCAL TITLE
    # =====================================================

    candidates = [
        movie.get("title"),
        movie.get("name"),
        movie.get("original_title"),
        movie.get("original_name")
    ]

    for value in candidates:

        if not value:
            continue

        value = str(
            value
        ).strip()

        if (
            value
            and not contains_arabic(
                value
            )
        ):

            log(
                "USING LOCAL TITLE:"
            )

            log(
                value
            )

            return value

    # =====================================================
    # 3. FALLBACK
    # =====================================================

    log(
        "WARNING: No English title found."
    )

    return "MOVINS FEATURE"


# =========================================================
# YEAR
# =========================================================

def movie_year(
    movie
):

    value = movie.get(
        "year"
    )

    if value:

        return str(
            value
        )

    date = (
        movie.get("release_date")
        or movie.get("first_air_date")
    )

    if date:

        return str(
            date
        )[:4]

    return ""


# =========================================================
# RATING
# =========================================================

def movie_rating(
    movie
):

    value = (
        movie.get("rating")
        or movie.get("vote_average")
    )

    if value is None:

        return ""

    try:

        return "{:.1f}".format(
            float(value)
        )

    except Exception:

        return str(
            value
        )


# =========================================================
# POSTER URL
# =========================================================

def poster_url(
    movie
):

    return (
        movie.get("poster")
        or movie.get("poster_url")
        or movie.get("image")
    )


# =========================================================
# SELECT MOVIE
# =========================================================

def choose_movie(
    movies,
    already_posted
):

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

        if mid in already_posted:
            continue

        if not poster_url(
            movie
        ):

            continue

        try:

            popularity = float(
                movie.get(
                    "popularity",
                    0
                )
                or 0
            )

        except Exception:

            popularity = 0

        try:

            rating = float(
                movie.get(
                    "rating",
                    0
                )
                or 0
            )

        except Exception:

            rating = 0

        try:

            votes = float(
                movie.get(
                    "vote_count",
                    0
                )
                or 0
            )

        except Exception:

            votes = 0

        score = (
            popularity
            + rating * 2
            + math.log10(
                votes + 1
            )
        )

        candidates.append(
            (
                score,
                movie
            )
        )

    if not candidates:

        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[0][1]


# =========================================================
# FONT
# =========================================================

def find_font():

    fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]

    for font in fonts:

        if os.path.exists(
            font
        ):

            return font

    raise RuntimeError(
        "No suitable font found."
    )


# =========================================================
# DOWNLOAD POSTER
# =========================================================

def download_poster(
    movie
):

    url = poster_url(
        movie
    )

    if not url:

        raise RuntimeError(
            "Poster URL missing."
        )

    log("")
    log(
        "Downloading poster..."
    )

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    with open(
        POSTER_FILE,
        "wb"
    ) as f:

        f.write(
            response.content
        )

    log(
        "Poster downloaded: "
        + str(
            POSTER_FILE.stat().st_size
        )
        + " bytes"
    )


# =========================================================
# PREPARE POSTER
# =========================================================

def prepare_poster():

    image = Image.open(
        POSTER_FILE
    ).convert(
        "RGB"
    )

    source_ratio = (
        image.width
        / image.height
    )

    target_ratio = (
        WIDTH
        / HEIGHT
    )

    if source_ratio > target_ratio:

        new_height = HEIGHT

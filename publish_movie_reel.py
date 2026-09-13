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
from PIL import Image, ImageDraw, ImageFont, ImageFilter


# =========================================================
# MOVINS — CINEMATIC REEL PUBLISHER
# =========================================================

GRAPH_VERSION = "v26.0"

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

WORK_DIR = Path("reel_work")
WORK_DIR.mkdir(exist_ok=True)

POSTER_FILE = WORK_DIR / "poster.jpg"
DESIGN_FILE = WORK_DIR / "design.png"
AUDIO_FILE = WORK_DIR / "cinematic_music.wav"
VIDEO_FILE = WORK_DIR / "movins_reel.mp4"

WIDTH = 1080
HEIGHT = 1920
DURATION = 12
FPS = 30

FACEBOOK_PAGE_TOKEN = os.environ.get(
    "FACEBOOK_PAGE_TOKEN"
)

TMDB_API_KEY = os.environ.get(
    "TMDB_API_KEY"
)

if not FACEBOOK_PAGE_TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing."
    )


# =========================================================
# LOG
# =========================================================

def log(text):
    print(text, flush=True)


# =========================================================
# RUN COMMAND
# =========================================================

def run_command(command):

    log("")
    log("RUNNING:")
    log(" ".join(str(x) for x in command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    print(result.stdout, flush=True)

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed with exit code "
            + str(result.returncode)
        )


# =========================================================
# JSON
# =========================================================

def load_json(path, default):

    if not os.path.exists(path):
        return default

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return default


def save_json(path, data):

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
        items = []

    return items


# =========================================================
# POSTED HISTORY
# =========================================================

def load_posted():

    data = load_json(
        POSTED_FILE,
        []
    )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        return data.get(
            "items",
            []
        )

    return []


def posted_ids(posted):

    result = set()

    for item in posted:

        if isinstance(item, dict):

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
# MOVIE HELPERS
# =========================================================

def movie_id(movie):

    value = (
        movie.get("id")
        or movie.get("tmdb_id")
    )

    if value is None:
        return None

    return str(value)


def contains_arabic(text):

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
# GET ENGLISH TITLE FROM TMDB
# =========================================================

def get_english_tmdb_title(mid, media_type):

    if not TMDB_API_KEY:
        return None

    try:

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

        response = requests.get(
            endpoint,
            params={
                "api_key": TMDB_API_KEY,
                "language": "en-US"
            },
            timeout=20
        )

        if not response.ok:
            return None

        data = response.json()

        title = (
            data.get("title")
            or data.get("name")
            or data.get("original_title")
            or data.get("original_name")
        )

        if not title:
            return None

        title = str(title).strip()

        if contains_arabic(title):
            return None

        return title

    except Exception as e:

        log(
            "TMDB English title lookup failed: "
            + str(e)
        )

        return None


def movie_title(movie):

    mid = movie_id(movie)

    media_type = movie_prefix(
        movie
    )

    # First preference:
    # English original title
    candidates = [
        movie.get("original_title"),
        movie.get("original_name")
    ]

    for value in candidates:

        if value:

            value = str(value).strip()

            if (
                not contains_arabic(value)
                and value
            ):

                return value

    # Second preference:
    # Ask TMDB for English title
    if mid:

        tmdb_title = (
            get_english_tmdb_title(
                mid,
                media_type
            )
        )

        if tmdb_title:
            return tmdb_title

    # Third preference:
    # Local title only if it is not Arabic
    local_title = (
        movie.get("title")
        or movie.get("name")
        or ""
    )

    local_title = str(
        local_title
    ).strip()

    if (
        local_title
        and not contains_arabic(local_title)
    ):

        return local_title

    # Final safe fallback
    return "MOVINS FEATURE"


def movie_year(movie):

    value = movie.get("year")

    if value:
        return str(value)

    date = (
        movie.get("release_date")
        or movie.get("first_air_date")
    )

    if date:
        return str(date)[:4]

    return ""


def movie_rating(movie):

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

        return str(value)


def movie_type(movie):

    value = (
        movie.get("detailed_type")
        or movie.get("type")
        or ""
    )

    text = str(value).lower()

    if (
        "مسلسل" in text
        or "tv" in text
        or "series" in text
    ):

        return "TV SERIES"

    return "MOVIE"


def movie_prefix(movie):

    value = (
        movie.get("detailed_type")
        or movie.get("type")
        or ""
    )

    text = str(value).lower()

    if (
        "مسلسل" in text
        or "tv" in text
        or "series" in text
    ):

        return "tv"

    return "movie"


# =========================================================
# SELECT MOVIE
# =========================================================

def choose_movie(
    movies,
    already_posted
):

    candidates = []

    for movie in movies:

        if not isinstance(movie, dict):
            continue

        mid = movie_id(movie)

        if not mid:
            continue

        if mid in already_posted:
            continue

        poster = (
            movie.get("poster")
            or movie.get("poster_url")
            or movie.get("image")
        )

        if not poster:
            continue

        try:

            popularity = float(
                movie.get(
                    "popularity",
                    0
                ) or 0
            )

        except Exception:

            popularity = 0

        try:

            rating = float(
                movie.get(
                    "rating",
                    0
                ) or 0
            )

        except Exception:

            rating = 0

        try:

            votes = float(
                movie.get(
                    "vote_count",
                    0
                ) or 0
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
        key=lambda x: x[0],
        reverse=True
    )

    return candidates[0][1]


# =========================================================
# ENGLISH FONT
# =========================================================

def find_english_font():

    fonts = [

        "/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans-Bold.ttf",

        "/usr/share/fonts/truetype/"
        "liberation2/LiberationSans-Regular.ttf",

    ]

    for path in fonts:

        if os.path.exists(path):

            log(
                "English font: "
                + path
            )

            return path

    raise RuntimeError(
        "English font not found."
    )


# =========================================================
# DOWNLOAD POSTER
# =========================================================

def download_poster(movie):

    url = (
        movie.get("poster")
        or movie.get("poster_url")
        or movie.get("image")
    )

    if not url:

        raise RuntimeError(
            "Poster URL missing."
        )

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
    ).convert("RGB")

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

        new_width = int(
            new_height
            * source_ratio
        )

    else:

        new_width = WIDTH

        new_height = int(
            new_width
            / source_ratio
        )

    image = image.resize(
        (
            new_width,
            new_height
        ),
        Image.Resampling.LANCZOS
    )

    left = (
        new_width
        - WIDTH
    ) // 2

    top = (
        new_height
        - HEIGHT
    ) // 2

    image = image.crop(
        (
            left,
            top,
            left + WIDTH,
            top + HEIGHT
        )
    )

    return image


# =========================================================
# CENTER ENGLISH TEXT
# =========================================================

def centered_text(
    draw,
    text,
    font,
    y,
    fill,
    stroke=0
):

    text = str(text)

    box = draw.textbbox(
        (0, 0),
        text,
        font=font,
        stroke_width=stroke
    )

    text_width = (
        box[2]
        - box[0]
    )

    x = (
        WIDTH
        - text_width
    ) / 2

    draw.text(
        (
            x,
            y
        ),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke,
        stroke_fill=(0, 0, 0, 230)
    )


# =========================================================
# CREATE DESIGN
# =========================================================

def create_design(movie):

    font_path = find_english_font()

    image = prepare_poster().convert(
        "RGBA"
    )

    # -----------------------------------------------------
    # CINEMATIC DARK OVERLAY
    # -----------------------------------------------------

    dark = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 45)
    )

    image = Image.alpha_composite(
        image,
        dark
    )

    # -----------------------------------------------------
    # BOTTOM PANEL
    # -----------------------------------------------------

    panel = Image.new(
        "RGBA",
        (
            WIDTH,
            700
        ),
        (0, 0, 0, 0)
    )

    panel_draw = ImageDraw.Draw(
        panel
    )

    panel_draw.rounded_rectangle(
        (
            35,
            35,
            WIDTH - 35,
            665
        ),
        radius=42,
        fill=(8, 10, 17, 230),
        outline=(255, 255, 255, 35),
        width=2
    )

    image.alpha_composite(
        panel,
        (
            0,
            1140
        )
    )

    draw = ImageDraw.Draw(
        image
    )

    # -----------------------------------------------------
    # FONTS
    # -----------------------------------------------------

    brand_font = ImageFont.truetype(
        font_path,
        62
    )

    category_font = ImageFont.truetype(
        font_path,
        40
    )

    title = movie_title(
        movie
    )

    title_size = 70

    if len(title) > 28:
        title_size = 58

    if len(title) > 40:
        title_size = 48

    title_font = ImageFont.truetype(
        font_path,
        title_size
    )

    info_font = ImageFont.truetype(
        font_path,
        43
    )

    cta_font = ImageFont.truetype(
        font_path,
        42
    )

    site_font = ImageFont.truetype(
        font_path,
        34
    )

    # -----------------------------------------------------
    # TOP BRAND
    # -----------------------------------------------------

    centered_text(
        draw,
        "MOVINS",
        brand_font,
        75,
        (255, 255, 255, 255),
        2
    )

    centered_text(
        draw,
        "MOVIES & SERIES",
        category_font,
        155,
        (235, 235, 235, 255),
        1
    )

    # -----------------------------------------------------
    # TYPE
    # -----------------------------------------------------

    centered_text(
        draw,
        movie_type(movie),
        category_font,
        1205,
        (210, 210, 215, 255),
        1
    )

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    centered_text(
        draw,
        title,
        title_font,
        1295,
        (255, 255, 255, 255),
        2
    )

    # -----------------------------------------------------
    # YEAR + RATING
    # -----------------------------------------------------

    year = movie_year(
        movie
    )

    rating = movie_rating(
        movie
    )

    info = []

    if year:
        info.append(year)

    if rating:
        info.append(
            "RATING "
            + rating
            + " / 10"
        )

    if info:

        centered_text(
            draw,
            "  •  ".join(info),
            info_font,
            1415,
            (225, 225, 230, 255),
            1
        )

    # -----------------------------------------------------
    # CTA
    # -----------------------------------------------------

    centered_text(
        draw,
        "WATCH DETAILS ON MOVINS",
        cta_font,
        1535,
        (245, 190, 65, 255),
        1
    )

    # -----------------------------------------------------
    # WEBSITE
    # -----------------------------------------------------

    centered_text(
        draw,
        "nownex.github.io/movins",
        site_font,
        1625,
        (220, 220, 225, 255),
        1
    )

    # -----------------------------------------------------
    # GOLD LINE
    # -----------------------------------------------------

    draw.line(
        (
            270,
            1710,
            810,
            1710
        ),
        fill=(245, 190, 65, 180),
        width=3
    )

    image.convert(
        "RGB"
    ).save(
        DESIGN_FILE,
        "PNG",
        optimize=True
    )

    log(
        "English cinematic design created."
    )


# =========================================================
# CINEMATIC MUSIC
# =========================================================

def piano_note(
    frequency,
    t,
    duration
):

    if t < 0 or t > duration:
        return 0.0

    attack = min(
        1.0,
        t / 0.025
    )

    release = min(
        1.0,
        (
            duration - t
        ) / 0.35
    )

    envelope = (
        attack
        * release
    )

    value = 0.0

    value += (
        math.sin(
            2
            * math.pi
            * frequency
            * t
        )
        * 0.50
    )

    value += (
        math.sin(
            2
            * math.pi
            * frequency
            * 2
            * t
        )
        * 0.20
    )

    value += (
        math.sin(
            2
            * math.pi
            * frequency
            * 3
            * t
        )
        * 0.08
    )

    value += (
        math.sin(
            2
            * math.pi
            * frequency
            * 4
            * t
        )
        * 0.035
    )

    decay = math.exp(
        -2.7 * t
    )

    return (
        value
        * envelope
        * decay
    )


def create_music():

    log(
        "Creating cinematic music..."
    )

    sample_rate = 44100

    total = int(
        sample_rate
        * DURATION
    )

    progression = [

        [261.63, 329.63, 392.00],

        [220.00, 277.18, 329.63],

        [174.61, 220.00, 261.63],

        [196.00, 246.94, 293.66]

    ]

    melody = [

        523.25,
        493.88,
        440.00,
        392.00,
        440.00,
        493.88,
        523.25,
        587.33

    ]

    frames = []

    for i in range(total):

        t = (
            i
            / sample_rate
        )

        # -------------------------------------------------
        # FADE
        # -------------------------------------------------

        fade_in = min(
            1.0,
            t / 1.2
        )

        fade_out = min(
            1.0,
            (
                DURATION - t
            ) / 1.4
        )

        master = min(
            fade_in,
            fade_out
        )

        # -------------------------------------------------
        # PAD
       

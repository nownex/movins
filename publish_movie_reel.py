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
# CENTER TEXT
# =========================================================

def centered_text(
    draw,
    text,
    font,
    y,
    fill,
    stroke=0
):

    text = str(
        text
    )

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
        stroke_fill=(0, 0, 0)
    )


# =========================================================
# CREATE DESIGN
# =========================================================

def create_design(
    movie
):

    font_path = find_font()

    image = prepare_poster().convert(
        "RGBA"
    )

    # =====================================================
    # DARK OVERLAY
    # =====================================================

    overlay = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 65)
    )

    image = Image.alpha_composite(
        image,
        overlay
    )

    draw = ImageDraw.Draw(
        image
    )

    # =====================================================
    # INFORMATION CARD
    # =====================================================

    draw.rounded_rectangle(
        (
            35,
            1110,
            WIDTH - 35,
            1815
        ),
        radius=45,
        fill=(5, 8, 14, 238),
        outline=(255, 255, 255, 55),
        width=2
    )

    # =====================================================
    # FONTS
    # =====================================================

    brand_font = ImageFont.truetype(
        font_path,
        66
    )

    category_font = ImageFont.truetype(
        font_path,
        38
    )

    title = movie_title(
        movie
    )

    title_size = 70

    if len(title) > 28:
        title_size = 58

    if len(title) > 40:
        title_size = 48

    if len(title) > 55:
        title_size = 42

    title_font = ImageFont.truetype(
        font_path,
        title_size
    )

    info_font = ImageFont.truetype(
        font_path,
        42
    )

    cta_font = ImageFont.truetype(
        font_path,
        40
    )

    site_font = ImageFont.truetype(
        font_path,
        32
    )

    # =====================================================
    # BRAND
    # =====================================================

    centered_text(
        draw,
        "MOVINS",
        brand_font,
        70,
        (255, 255, 255),
        2
    )

    # =====================================================
    # SUBTITLE
    # =====================================================

    centered_text(
        draw,
        "MOVIES & SERIES",
        category_font,
        155,
        (235, 235, 235),
        1
    )

    # =====================================================
    # TYPE
    # =====================================================

    centered_text(
        draw,
        movie_type(movie),
        category_font,
        1175,
        (205, 205, 215),
        1
    )

    # =====================================================
    # REAL TITLE
    # =====================================================

    centered_text(
        draw,
        title,
        title_font,
        1270,
        (255, 255, 255),
        2
    )

    # =====================================================
    # YEAR + RATING
    # =====================================================

    year = movie_year(
        movie
    )

    rating = movie_rating(
        movie
    )

    info = []

    if year:

        info.append(
            year
        )

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
            1400,
            (225, 225, 230),
            1
        )

    # =====================================================
    # CTA
    # =====================================================

    centered_text(
        draw,
        "WATCH DETAILS ON MOVINS",
        cta_font,
        1525,
        (245, 190, 65),
        1
    )

    # =====================================================
    # WEBSITE
    # =====================================================

    centered_text(
        draw,
        "nownex.github.io/movins",
        site_font,
        1615,
        (220, 220, 225),
        1
    )

    # =====================================================
    # GOLD LINE
    # =====================================================

    draw.line(
        (
            270,
            1710,
            810,
            1710
        ),
        fill=(245, 190, 65),
        width=3
    )

    # =====================================================
    # SAVE
    # =====================================================

    image.convert(
        "RGB"
    ).save(
        DESIGN_FILE,
        "JPEG",
        quality=95
    )

    log(
        "Design created: "
        + str(
            DESIGN_FILE
        )
    )


# =========================================================
# CREATE CINEMATIC MUSIC
# =========================================================

def create_music():

    log("")
    log(
        "Creating cinematic music..."
    )

    sample_rate = SAMPLE_RATE

    total_samples = int(
        sample_rate
        * DURATION
    )

    chords = [
        [
            261.63,
            329.63,
            392.00
        ],
        [
            220.00,
            277.18,
            329.63
        ],
        [
            174.61,
            220.00,
            261.63
        ],
        [
            196.00,
            246.94,
            293.66
        ]
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

    for i in range(
        total_samples
    ):

        t = (
            i
            / sample_rate
        )

        fade_in = min(
            1.0,
            t / 1.2
        )

        fade_out = min(
            1.0,
            (DURATION - t) / 1.8
        )

        envelope = (
            fade_in
            * fade_out
        )

        chord_index = int(
            t / 3
        )

        if chord_index >= len(
            chords
        ):

            chord_index = (
                len(chords)
                - 1
            )

        chord = chords[
            chord_index
        ]

        value = 0.0

        # Pad
        for frequency in chord:

            value += (
                math.sin(
                    2
                    * math.pi
                    * frequency
                    * t
                )
                * 0.045
            )

        # Melody
        note_index = (
            int(
                t * 1.5
            )
            % len(melody)
        )

        note_frequency = melody[
            note_index
        ]

        note_position = (
            t * 1.5
        ) % 1.0

        note_envelope = math.exp(
            -3.0
            * note_position
        )

        value += (
            math.sin(
                2
                * math.pi
                * note_frequency
                * t
            )
            * 0.10
            * note_envelope
        )

        # Bass
        bass_frequency = (
            chord[0]
            / 2
        )

        value += (
            math.sin(
                2
                * math.pi
                * bass_frequency
                * t
            )
            * 0.055
        )

        value *= envelope

        value = max(
            -0.75,
            min(
                0.75,
                value
            )
        )

        sample = int(
            value
            * 32767
        )

        frames.append(
            struct.pack(
                "<h",
                sample
            )
        )

    with wave.open(
        str(AUDIO_FILE),
        "wb"
    ) as wav:

        wav.setnchannels(
            1
        )

        wav.setsampwidth(
            2
        )

        wav.setframerate(
            sample_rate
        )

        wav.writeframes(
            b"".join(frames)
        )

    log(
        "Music created."
    )


# =========================================================
# CREATE VIDEO
# =========================================================

def create_video():

    log("")
    log(
        "Creating cinematic Reel..."
    )

    filter_complex = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0008,1.10)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d="
        + str(
            DURATION * FPS
        )
        + ":"
        "s=1080x1920:"
        "fps="
        + str(FPS)
        + "[v]"
    )

    command = [
        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        str(DESIGN_FILE),

        "-i",
        str(AUDIO_FILE),

        "-filter_complex",
        filter_complex,

        "-map",
        "[v]",

        "-map",
        "1:a",

        "-t",
        str(DURATION),

        "-r",
        str(FPS),

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "21",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-ar",
        "44100",

        "-movflags",
        "+faststart",

        str(VIDEO_FILE)
    ]

    run_command(
        command
    )

    if not VIDEO_FILE.exists():

        raise RuntimeError(
            "Video file was not created."
        )

    size = (
        VIDEO_FILE.stat().st_size
    )

    log(
        "Reel video created: "
        + str(size)
        + " bytes"
    )


# =========================================================
# FACEBOOK PAGE
# =========================================================

def get_page_info():

    log("")
    log(
        "Checking Facebook Page..."
    )

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/me"
    )

    response = requests.get(
        url,
        params={
            "fields":
                "id,name",

            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=30
    )

    try:

        data = response.json()

    except Exception:

        data = {
            "raw":
                response.text
        }

    log(
        "Facebook /me response:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook Page check failed."
        )

    page_id = data.get(
        "id"
    )

    page_name = data.get(
        "name"
    )

    if not page_id:

        raise RuntimeError(
            "Facebook Page ID was not returned."
        )

    log(
        "Facebook Page: "
        + str(page_name)
    )

    log(
        "Facebook Page ID: "
        + str(page_id)
    )

    return str(
        page_id
    )


# =========================================================
# FACEBOOK START
# =========================================================

def facebook_start(
    page_id
):

    log("")
    log(
        "Starting Facebook Reel upload..."
    )

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/"
        + page_id
        + "/video_reels"
    )

    response = requests.post(
        url,
        params={
            "upload_phase":
                "start",

            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=30
    )

    try:

        data = response.json()

    except Exception:

        data = {
            "raw":
                response.text
        }

    log(
        "Facebook START response:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook START failed."
        )

    video_id = data.get(
        "video_id"
    )

    upload_url = data.get(
        "upload_url"
    )

    if not video_id:

        raise RuntimeError(
            "Facebook did not return video_id."
        )

    if not upload_url:

        upload_url = (
            "https://rupload.facebook.com/"
            "video-upload/"
            + GRAPH_VERSION
            + "/"
            + str(video_id)
        )

    return (
        str(video_id),
        str(upload_url)
    )


# =========================================================
# FACEBOOK UPLOAD
# =========================================================

def facebook_upload(
    video_id,
    upload_url
):

    log("")
    log(
        "Uploading video binary..."
    )

    file_size = (
        VIDEO_FILE.stat().st_size
    )

    log(
        "Video size: "
        + str(file_size)
        + " bytes"
    )

    with open(
        VIDEO_FILE,
        "rb"
    ) as video_file:

        response = requests.post(
            upload_url,
            headers={
                "Authorization":
                    "OAuth "
                    + FACEBOOK_PAGE_TOKEN,

                "offset":
                    "0",

                "file_size":
                    str(file_size),

                "Content-Type":
                    "application/octet-stream"
            },
            data=video_file,
            timeout=240
        )

    try:

        data = response.json()

    except Exception:

        data = {
            "raw":
                response.text
        }

    log(
        "Facebook UPLOAD response:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook binary upload failed."
        )

    if data.get(
        "success"
    ) is False:

        raise RuntimeError(
            "Facebook upload returned success=false."
        )

    return data


# =========================================================
# FACEBOOK STATUS
# =========================================================

def facebook_status(
    video_id
):

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/"
        + str(video_id)
    )

    response = requests.get(
        url,
        params={
            "fields":
                "status",

            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=30
    )

    try:

        data = response.json()

    except Exception:

        data = {
            "raw":
                response.text
        }

    if not response.ok:

        log(
            "Facebook STATUS error:"
        )

        log(
            json.dumps(
                data,
                ensure_ascii=False
            )
        )

        return None

    log(
        "Facebook STATUS:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    return data


# =========================================================
# FINISH + PUBLISH
# =========================================================

def facebook_publish(
    page_id,
    video_id,
    movie
):

    title = movie_title(
        movie
    )

    mid = movie_id(
        movie
    )

    movins_url = (
        "https://nownex.github.io/movins/"
        "?movie="
        + movie_prefix(movie)
        + "-"
        + str(mid)
    )

    description = (
        "🎬 "
        + title
        + "\n\n"
        + "Discover this movie or series "
        + "on MOVINS.\n\n"
        + movins_url
        + "\n\n"
        + "#MOVINS #Movies #Series #Film"
    )

    log("")
    log(
        "======================================"
    )

    log(
        "FINISHING AND PUBLISHING REEL"
    )

    log(
        "Title: "
        + title
    )

    log(
        "======================================"
    )

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/"
        + page_id
        + "/video_reels"
    )

    response = requests.post(
        url,
        params={
            "upload_phase":
                "finish",

            "video_id":
                str(video_id),

            "video_state":
                "PUBLISHED",

            "description":
                description,

            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=60
    )

    try:

        data = response.json()

    except Exception:

        data = {
            "raw":
                response.text
        }

    log(
        "Facebook FINISH response:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook FINISH/PUBLISH failed."
        )

    if data.get(
        "success"
    ) is False:

        raise RuntimeError(
            "Facebook FINISH returned success=false."
        )

    return data


# =========================================================
# WAIT AFTER FINISH
# =========================================================

def wait_for_publish(
    video_id
):

    log("")
    log(
        "Waiting for Facebook processing..."
    )

    max_attempts = 60

    for attempt in range(
        1,
        max_attempts + 1
    ):

        time.sleep(5)

        log("")
        log(
            "Status check "
            + str(attempt)
            + "/"
            + str(max_attempts)
        )

        data = facebook_status(
            video_id
        )

        if not data:
            continue

        status = data.get(
            "status",
            {}
        )

        if not isinstance(
            status,
            dict
        ):

            continue

        video_status = str(
            status.get(
                "video_status",
                ""
            )
        ).lower()

        processing_phase = status.get(
            "processing_phase",
            {}
        )

        publishing_phase = status.get(
            "publishing_phase",
            {}
        )

        copyright_phase = status.get(
            "copyright_check_status",
            {}
        )

        log(
            "video_status = "
            + video_status
        )

        log(
            "processing_phase = "
            + str(
                processing_phase
            )
        )

        log(
            "publishing_phase = "
            + str(
                publishing_phase
            )
        )

        log(
            "copyright_check = "
            + str(
                copyright_phase
            )
        )

        # =================================================
        # VIDEO ERROR
        # =================================================

        if video_status in (
            "error",
            "failed"
        ):

            raise RuntimeError(
                "Facebook reported video_status="
                + video_status
            )

        # =================================================
        # PROCESSING ERROR
        # =================================================

        if isinstance(
            processing_phase,
            dict
        ):

            processing_status = str(
                processing_phase.get(
                    "status",
                    ""
                )
            ).lower()

            if processing_status in (
                "error",
                "failed"
            ):

                raise RuntimeError(
                    "Facebook processing failed."
                )

        # =================================================
        # PUBLISHING ERROR
        # =================================================

        if isinstance(
            publishing_phase,
            dict
        ):

            publishing_status = str(
                publishing_phase.get(
                    "status",
                    ""
                )
            ).lower()

            if publishing_status in (
                "error",
                "failed"
            ):

                raise RuntimeError(
                    "Facebook publishing failed."
                )

        # =================================================
        # PUBLISHED
        # =================================================

        if isinstance(
            publishing_phase,
            dict
        ):

            publishing_status = str(
                publishing_phase.get(
                    "status",
                    ""
                )
            ).lower()

            if publishing_status in (
                "published",
                "complete",
                "completed"
            ):

                log("")
                log(
                    "Facebook Reel publishing confirmed."
                )

                return True

        # =================================================
        # VIDEO STATUS SUCCESS
        # =================================================

        if video_status in (
            "published",
            "complete",
            "completed"
        ):

            log("")
            log(
                "Facebook Reel publishing confirmed."
            )

            return True

    raise RuntimeError(
        "Facebook did not confirm Reel "
        "publishing within 5 minutes."
    )


# =========================================================
# SAVE POSTED HISTORY
# =========================================================

def save_posted(
    posted,
    movie,
    video_id,
    publish_response
):

    mid = movie_id(
        movie
    )

    title = movie_title(
        movie
    )

    record = {
        "id":
            mid,

        "tmdb_id":
            mid,

        "title":
            title,

        "type":
            movie_type(
                movie
            ),

        "video_id":
            str(video_id),

        "published_at":
            int(time.time()),

        "movins_url":
            (
                "https://nownex.github.io/movins/"
                "?movie="
                + movie_prefix(movie)
                + "-"
                + str(mid)
            )
    }

    if isinstance(
        publish_response,
        dict
    ):

        if publish_response.get(
            "id"
        ):

            record[
                "facebook_id"
            ] = str(
                publish_response.get(
                    "id"
                )
            )

        if publish_response.get(
            "success"
        ) is not None:

            record[
                "facebook_success"
            ] = publish_response.get(
                "success"
            )

    posted.append(
        record
    )

    save_json(
        POSTED_FILE,
        posted
    )

    log("")
    log(
        "Reel history updated."
    )


# =========================================================
# MAIN
# =========================================================

def main():

    log("")
    log(
        "======================================"
    )

    log(
        "MOVINS CINEMATIC REEL PUBLISHER"
    )

    log(
        "======================================"
    )

    # =====================================================
    # CLEAN
    # =====================================================

    clean_work()

    # =====================================================
    # LOAD
    # =====================================================

    movies = load_movies()

    posted = load_posted()

    already_posted = posted_ids(
        posted
    )

    log("")
    log(
        "Movies available: "
        + str(
            len(movies)
        )
    )

    log(
        "Already posted Reels: "
        + str(
            len(already_posted)
        )
    )

    # =====================================================
    # SELECT
    # =====================================================

    movie = choose_movie(
        movies,
        already_posted
    )

    if not movie:

        log("")
        log(
            "No eligible movie found."
        )

        return

    mid = movie_id(
        movie
    )

    # =====================================================
    # GET TITLE BEFORE DESIGN
    # =====================================================

    title = movie_title(
        movie
    )

    log("")
    log(
        "======================================"
    )

    log(
        "SELECTED MOVIE"
    )

    log(
        "Title: "
        + title
    )

    log(
        "TMDB ID: "
        + str(mid)
    )

    log(
        "Type: "
        + movie_type(movie)
    )

    log(
        "Year: "
        + movie_year(movie)
    )

    log(
        "Rating: "
        + movie_rating(movie)
    )

    log(
        "======================================"
    )

    # =====================================================
    # POSTER
    # =====================================================

    download_poster(
        movie
    )

    # =====================================================
    # DESIGN
    # =====================================================

    create_design(
        movie
    )

    # =====================================================
    # MUSIC
    # =====================================================

    create_music()

    # =====================================================
    # VIDEO
    # =====================================================

    create_video()

    # =====================================================
    # FACEBOOK PAGE
    # =====================================================

    page_id = get_page_info()

    # =====================================================
    # START
    # =====================================================

    video_id, upload_url = (
        facebook_start(
            page_id
        )
    )

    log(
        "Facebook video_id: "
        + str(video_id)
    )

    # =====================================================
    # UPLOAD
    # =====================================================

    facebook_upload(
        video_id,
        upload_url
    )

    log("")
    log(
        "Facebook upload completed."
    )

    # =====================================================
    # FINISH + PUBLISH
    # =====================================================

    publish_response = (
        facebook_publish(
            page_id,
            video_id,
            movie
        )
    )

    log("")
    log(
        "Facebook FINISH request accepted."
    )

    # =====================================================
    # WAIT
    # =====================================================

    wait_for_publish(
        video_id
    )

    # =====================================================
    # SAVE HISTORY
    # =====================================================

    save_posted(
        posted,
        movie,
        video_id,
        publish_response
    )

    # =====================================================
    # SUCCESS
    # =====================================================

    log("")
    log(
        "======================================"
    )

    log(
        "MOVINS REEL PUBLISHED SUCCESSFULLY"
    )

    log(
        "======================================"
    )

    log(
        "Movie: "
        + title
    )

    log(
        "Facebook video_id: "
        + str(video_id)
    )

    log(
        "MOVINS URL:"
    )

    log(
        "https://nownex.github.io/movins/"
        "?movie="
        + movie_prefix(movie)
        + "-"
        + str(mid)
    )

    log(
        "======================================"
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()

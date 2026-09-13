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

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None


# =========================================================
# MOVINS — CINEMATIC REEL PUBLISHER
# =========================================================

GRAPH_VERSION = "v26.0"

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

WORK_DIR = Path("reel_work")
WORK_DIR.mkdir(exist_ok=True)

VIDEO_FILE = WORK_DIR / "movins_reel.mp4"
AUDIO_FILE = WORK_DIR / "movins_music.wav"
POSTER_FILE = WORK_DIR / "poster.jpg"
TEXT_FILE = WORK_DIR / "reel_text.png"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

REEL_DURATION = 12

FACEBOOK_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")

if not FACEBOOK_PAGE_TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing."
    )


# =========================================================
# BASIC HELPERS
# =========================================================

def log(message):
    print(message, flush=True)


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

    return result


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
# CLEAN OLD FILES
# =========================================================

def clean_work_directory():
    for item in WORK_DIR.iterdir():

        try:
            if item.is_file():
                item.unlink()

            elif item.is_dir():
                shutil.rmtree(item)

        except Exception as e:
            log(
                "Could not remove "
                + str(item)
                + ": "
                + str(e)
            )


# =========================================================
# LOAD MOVIES
# =========================================================

def load_movies():
    data = load_json(
        MOVIES_FILE,
        {"items": []}
    )

    if isinstance(data, list):
        movies = data

    elif isinstance(data, dict):
        movies = data.get(
            "items",
            []
        )

    else:
        movies = []

    if not isinstance(movies, list):
        movies = []

    return movies


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


def get_posted_ids(posted):
    result = set()

    for item in posted:

        if isinstance(item, dict):

            value = (
                item.get("id")
                or item.get("movie_id")
                or item.get("tmdb_id")
            )

            if value is not None:
                result.add(
                    str(value)
                )

        else:
            result.add(
                str(item)
            )

    return result


# =========================================================
# MOVIE DATA
# =========================================================

def get_movie_id(movie):
    value = (
        movie.get("id")
        or movie.get("tmdb_id")
    )

    if value is None:
        return None

    return str(value)


def get_movie_title(movie):

    title = (
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
    )

    if not title:
        title = "MOVINS"

    return str(title).strip()


def get_movie_year(movie):

    year = movie.get("year")

    if year:
        return str(year)

    release_date = (
        movie.get("release_date")
        or movie.get("first_air_date")
    )

    if release_date:
        return str(
            release_date
        )[:4]

    return ""


def get_movie_rating(movie):

    rating = (
        movie.get("rating")
        or movie.get("vote_average")
    )

    if rating is None:
        return ""

    try:
        return "{:.1f}".format(
            float(rating)
        )
    except Exception:
        return str(rating)


def get_movie_type(movie):

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
        return "مسلسل"

    return "فيلم"


# =========================================================
# SELECT MOVIE
# =========================================================

def choose_movie(movies, posted_ids):

    candidates = []

    for movie in movies:

        if not isinstance(movie, dict):
            continue

        movie_id = get_movie_id(movie)

        if not movie_id:
            continue

        if movie_id in posted_ids:
            continue

        poster = (
            movie.get("poster")
            or movie.get("poster_url")
            or movie.get("image")
        )

        if not poster:
            continue

        popularity = movie.get(
            "popularity",
            0
        )

        rating = movie.get(
            "rating",
            0
        )

        vote_count = movie.get(
            "vote_count",
            0
        )

        try:
            popularity = float(
                popularity or 0
            )
        except Exception:
            popularity = 0

        try:
            rating = float(
                rating or 0
            )
        except Exception:
            rating = 0

        try:
            vote_count = float(
                vote_count or 0
            )
        except Exception:
            vote_count = 0

        score = (
            popularity * 1.0
            + rating * 3.0
            + math.log10(
                vote_count + 1
            ) * 2.0
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
# FONT SEARCH
# =========================================================

def find_font():

    possible = [

        "/usr/share/fonts/truetype/noto/"
        "NotoNaskhArabic-Regular.ttf",

        "/usr/share/fonts/truetype/noto/"
        "NotoNaskhArabicUI-Regular.ttf",

        "/usr/share/fonts/truetype/noto/"
        "NotoSansArabic-Regular.ttf",

        "/usr/share/fonts/truetype/noto/"
        "NotoSansArabicUI-Regular.ttf",

        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans.ttf",

    ]

    for path in possible:

        if os.path.exists(path):
            log(
                "Font found: "
                + path
            )
            return path

    for root, dirs, files in os.walk(
        "/usr/share/fonts"
    ):

        for filename in files:

            lower = filename.lower()

            if (
                lower.endswith(".ttf")
                and (
                    "arabic" in lower
                    or "naskh" in lower
                )
            ):

                path = os.path.join(
                    root,
                    filename
                )

                log(
                    "Arabic font found: "
                    + path
                )

                return path

    log(
        "Arabic font not found. "
        "Using DejaVu Sans."
    )

    return (
        "/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans.ttf"
    )


# =========================================================
# ARABIC TEXT SHAPING
# =========================================================

def shape_text(text):

    text = str(text)

    if (
        arabic_reshaper is not None
        and get_display is not None
    ):

        try:

            reshaped = (
                arabic_reshaper.reshape(
                    text
                )
            )

            return get_display(
                reshaped
            )

        except Exception:
            pass

    return text


# =========================================================
# CENTER TEXT
# =========================================================

def draw_centered(
    draw,
    text,
    font,
    y,
    fill,
    canvas_width
):

    shaped = shape_text(text)

    bbox = draw.textbbox(
        (0, 0),
        shaped,
        font=font
    )

    width = (
        bbox[2]
        - bbox[0]
    )

    x = (
        canvas_width
        - width
    ) / 2

    draw.text(
        (x, y),
        shaped,
        font=font,
        fill=fill,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 180)
    )


# =========================================================
# DOWNLOAD POSTER
# =========================================================

def download_poster(movie):

    poster_url = (
        movie.get("poster")
        or movie.get("poster_url")
        or movie.get("image")
    )

    if not poster_url:
        raise RuntimeError(
            "Movie has no poster."
        )

    log(
        "Downloading movie poster..."
    )

    response = requests.get(
        poster_url,
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

    size = os.path.getsize(
        POSTER_FILE
    )

    log(
        "Poster downloaded: "
        + str(size)
        + " bytes"
    )


# =========================================================
# CREATE CINEMATIC BACKGROUND
# =========================================================

def create_background():

    image = Image.open(
        POSTER_FILE
    ).convert("RGB")

    # Cover 1080x1920
    source_ratio = (
        image.width
        / image.height
    )

    target_ratio = (
        VIDEO_WIDTH
        / VIDEO_HEIGHT
    )

    if source_ratio > target_ratio:

        new_height = VIDEO_HEIGHT

        new_width = int(
            new_height
            * source_ratio
        )

    else:

        new_width = VIDEO_WIDTH

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
        image.width
        - VIDEO_WIDTH
    ) // 2

    top = (
        image.height
        - VIDEO_HEIGHT
    ) // 2

    image = image.crop(
        (
            left,
            top,
            left + VIDEO_WIDTH,
            top + VIDEO_HEIGHT
        )
    )

    # Dark cinematic treatment
    image = image.filter(
        ImageFilter.GaussianBlur(
            radius=0.6
        )
    )

    overlay = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 80)
    )

    image = Image.alpha_composite(
        image.convert("RGBA"),
        overlay
    )

    # Gradient-like dark lower section
    gradient = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0)
    )

    gd = ImageDraw.Draw(
        gradient
    )

    for y in range(
        VIDEO_HEIGHT // 2,
        VIDEO_HEIGHT
    ):

        progress = (
            y
            - VIDEO_HEIGHT // 2
        ) / (
            VIDEO_HEIGHT // 2
        )

        alpha = int(
            20
            + progress * 170
        )

        gd.line(
            (
                0,
                y,
                VIDEO_WIDTH,
                y
            ),
            fill=(
                0,
                0,
                0,
                alpha
            )
        )

    image = Image.alpha_composite(
        image,
        gradient
    )

    return image


# =========================================================
# CREATE TEXT CARD
# =========================================================

def create_text_card(movie):

    font_path = find_font()

    image = create_background()

    draw = ImageDraw.Draw(
        image
    )

    title = get_movie_title(
        movie
    )

    year = get_movie_year(
        movie
    )

    rating = get_movie_rating(
        movie
    )

    movie_type = get_movie_type(
        movie
    )

    # Fonts
    logo_font = ImageFont.truetype(
        font_path,
        58
    )

    small_font = ImageFont.truetype(
        font_path,
        46
    )

    title_font = ImageFont.truetype(
        font_path,
        72
    )

    info_font = ImageFont.truetype(
        font_path,
        45
    )

    movins_font = ImageFont.truetype(
        font_path,
        42
    )

    # -----------------------------------------------------
    # TOP BRAND
    # -----------------------------------------------------

    draw_centered(
        draw,
        "MOVINS",
        logo_font,
        90,
        (255, 255, 255, 255),
        VIDEO_WIDTH
    )

    draw_centered(
        draw,
        "أفلام ومسلسلات",
        small_font,
        165,
        (225, 225, 225, 255),
        VIDEO_WIDTH
    )

    # -----------------------------------------------------
    # DARK CARD
    # -----------------------------------------------------

    card_top = 1180
    card_bottom = 1790

    card = Image.new(
        "RGBA",
        (
            VIDEO_WIDTH,
            card_bottom - card_top
        ),
        (0, 0, 0, 0)
    )

    card_draw = ImageDraw.Draw(
        card
    )

    card_draw.rounded_rectangle(
        (
            45,
            20,
            VIDEO_WIDTH - 45,
            card.height - 20
        ),
        radius=38,
        fill=(8, 10, 16, 225),
        outline=(255, 255, 255, 35),
        width=2
    )

    image.alpha_composite(
        card,
        (
            0,
            card_top
        )
    )

    draw = ImageDraw.Draw(
        image
    )

    # -----------------------------------------------------
    # TYPE
    # -----------------------------------------------------

    draw_centered(
        draw,
        movie_type,
        small_font,
        1240,
        (220, 220, 220, 255),
        VIDEO_WIDTH
    )

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    # If title is long, reduce font size
    title_font_size = 72

    if len(title) > 24:
        title_font_size = 60

    if len(title) > 35:
        title_font_size = 50

    title_font = ImageFont.truetype(
        font_path,
        title_font_size
    )

    shaped_title = shape_text(
        title
    )

    bbox = draw.textbbox(
        (0, 0),
        shaped_title,
        font=title_font
    )

    title_width = (
        bbox[2]
        - bbox[0]
    )

    title_x = (
        VIDEO_WIDTH
        - title_width
    ) / 2

    draw.text(
        (
            title_x,
            1320
        ),
        shaped_title,
        font=title_font,
        fill=(255, 255, 255, 255),
        stroke_width=3,
        stroke_fill=(0, 0, 0, 255)
    )

    # -----------------------------------------------------
    # YEAR + RATING
    # -----------------------------------------------------

    info_parts = []

    if year:
        info_parts.append(
            year
        )

    if rating:
        info_parts.append(
            "⭐ " + rating + " / 10"
        )

    info_text = "   •   ".join(
        info_parts
    )

    if info_text:

        draw_centered(
            draw,
            info_text,
            info_font,
            1450,
            (235, 235, 235, 255),
            VIDEO_WIDTH
        )

    # -----------------------------------------------------
    # CALL TO ACTION
    # -----------------------------------------------------

    draw_centered(
        draw,
        "شاهد التفاصيل على MOVINS",
        info_font,
        1580,
        (245, 195, 70, 255),
        VIDEO_WIDTH
    )

    # -----------------------------------------------------
    # WEBSITE
    # -----------------------------------------------------

    draw_centered(
        draw,
        "nownex.github.io/movins",
        movins_font,
        1680,
        (220, 220, 220, 255),
        VIDEO_WIDTH
    )

    image.convert(
        "RGB"
    ).save(
        TEXT_FILE,
        "PNG",
        optimize=True
    )

    log(
        "Arabic text image created."
    )


# =========================================================
# CREATE ORIGINAL MUSIC
# =========================================================

def create_original_music():

    log(
        "Creating original cinematic music..."
    )

    sample_rate = 44100

    total_samples = int(
        sample_rate
        * REEL_DURATION
    )

    # Cinematic chord progression
    chords = [
        [220.00, 277.18, 329.63],
        [196.00, 246.94, 293.66],
        [174.61, 220.00, 261.63],
        [196.00, 246.94, 329.63],
    ]

    frames = []

    for i in range(
        total_samples
    ):

        t = (
            i
            / sample_rate
        )

        chord_index = int(
            t / 3.0
        ) % len(chords)

        chord = chords[
            chord_index
        ]

        # Soft fade in/out
        fade_in = min(
            1.0,
            t / 1.2
        )

        fade_out = min(
            1.0,
            (
                REEL_DURATION - t
            ) / 1.5
        )

        envelope = min(
            fade_in,
            fade_out
        )

        # Main chord
        value = 0.0

        for frequency in chord:

            value += (
                math.sin(
                    2
                    * math.pi
                    * frequency
                    * t
                )
                * 0.10
            )

            # soft harmonic
            value += (
                math.sin(
                    2
                    * math.pi
                    * frequency
                    * 2
                    * t
                )
                * 0.025
            )

        # Slow atmospheric pad
        value += (
            math.sin(
                2
                * math.pi
                * 110
                * t
            )
            * 0.035
        )

        # Gentle pulse
        pulse = (
            math.sin(
                2
                * math.pi
                * 1.5
                * t
            )
            + 1
        ) / 2

        value += (
            pulse
            * math.sin(
                2
                * math.pi
                * 55
                * t
            )
            * 0.025
        )

        value *= envelope

        # Stereo width
        left = value
        right = value * 0.96

        left_int = int(
            max(
                -1.0,
                min(
                    1.0,
                    left
                )
            )
            * 32767
        )

        right_int = int(
            max(
                -1.0,
                min(
                    1.0,
                    right
                )
            )
            * 32767
        )

        frames.append(
            struct.pack(
                "<hh",
                left_int,
                right_int
            )
        )

    with wave.open(
        str(AUDIO_FILE),
        "wb"
    ) as wav:

        wav.setnchannels(2)

        wav.setsampwidth(2)

        wav.setframerate(
            sample_rate
        )

        wav.writeframes(
            b"".join(frames)
        )

    log(
        "Original music created."
    )


# =========================================================
# CREATE VIDEO WITH FFMPEG
# =========================================================

def create_video():

    log(
        "Creating cinematic MOVINS Reel..."
    )

    # 12 seconds, 1080x1920
    #
    # The image itself contains Arabic text.
    # This avoids FFmpeg drawtext Arabic problems.

    filter_complex = (
        "[0:v]"
        "scale="
        + str(VIDEO_WIDTH)
        + ":"
        + str(VIDEO_HEIGHT)
        + ","
        "zoompan="
        "z='min(zoom+0.0008,1.10)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=1:"
        "s="
        + str(VIDEO_WIDTH)
        + "x"
        + str(VIDEO_HEIGHT)
        + ":"
        "fps=30"
        "[v]"
    )

    command = [
        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        str(TEXT_FILE),

        "-i",
        str(AUDIO_FILE),

        "-filter_complex",
        filter_complex,

        "-map",
        "[v]",

        "-map",
        "1:a",

        "-t",
        str(REEL_DURATION),

        "-r",
        "30",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "21",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

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

    size = VIDEO_FILE.stat().st_size

    log(
        "Reel created successfully: "
        + str(size)
        + " bytes"
    )


# =========================================================
# FACEBOOK PAGE
# =========================================================

def get_page_info():

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/me"
    )

    response = requests.get(
        url,
        params={
            "fields": "id,name",
            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=30
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook /me failed: "
            + response.text
        )

    data = response.json()

    page_id = data.get("id")
    page_name = data.get("name")

    if not page_id:

        raise RuntimeError(
            "Facebook Page ID was not found."
        )

    log(
        "Facebook Page: "
        + str(page_name)
    )

    log(
        "Facebook Page ID: "
        + str(page_id)
    )

    return page_id, page_name


# =========================================================
# FACEBOOK REEL UPLOAD
# =========================================================

def publish_reel(
    page_id,
    movie,
    caption
):

    video_size = (
        VIDEO_FILE.stat().st_size
    )

    log(
        "Uploading Reel to Facebook..."
    )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    start_url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/"
        + str(page_id)
        + "/video_reels"
    )

    start_response = requests.post(
        start_url,
        data={
            "upload_phase": "start",
            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=60
    )

    if not start_response.ok:

        raise RuntimeError(
            "Facebook Reel start failed:\n"
            + start_response.text
        )

    start_data = (
        start_response.json()
    )

    upload_url = (
        start_data.get(
            "upload_url"
        )
    )

    video_id = (
        start_data.get(
            "video_id"
        )
        or start_data.get(
            "id"
        )
    )

    if not upload_url:

        raise RuntimeError(
            "Facebook did not return upload_url."
        )

    log(
        "Facebook upload session started."
    )

    # -----------------------------------------------------
    # UPLOAD
    # -----------------------------------------------------

    with open(
        VIDEO_FILE,
        "rb"
    ) as video:

        upload_response = requests.post(
            upload_url,
            headers={
                "Authorization":
                    "OAuth "
                    + FACEBOOK_PAGE_TOKEN,

                "offset": "0",

                "file_size":
                    str(video_size)
            },
            data=video,
            timeout=300
        )

    if not upload_response.ok:

        raise RuntimeError(
            "Facebook Reel upload failed:\n"
            + upload_response.text
        )

    log(
        "Video uploaded successfully."
    )

    # -----------------------------------------------------
    # FINISH / PUBLISH
    # -----------------------------------------------------

    finish_data = {
        "upload_phase": "finish",
        "video_state": "PUBLISHED",
        "access_token":
            FACEBOOK_PAGE_TOKEN,
        "description":
            caption
    }

    if video_id:
        finish_data[
            "video_id"
        ] = video_id

    finish_response = requests.post(
        start_url,
        data=finish_data,
        timeout=120
    )

    if not finish_response.ok:

        raise RuntimeError(
            "Facebook Reel publish failed:\n"
            + finish_response.text
        )

    result = (
        finish_response.json()
    )

    log(
        "Facebook Reel published."
    )

    log(
        "Facebook response: "
        + json.dumps(
            result,
            ensure_ascii=False
        )
    )

    return result


# =========================================================
# CAPTION
# =========================================================

def build_caption(movie):

    title = get_movie_title(
        movie
    )

    year = get_movie_year(
        movie
    )

    rating = get_movie_rating(
        movie
    )

    movie_type = get_movie_type(
        movie
    )

    movie_id = get_movie_id(
        movie
    )

    site_url = (
        "https://nownex.github.io/movins/"
        "?movie="
        + movie_type_prefix(movie)
        + "-"
        + str(movie_id)
    )

    lines = []

    lines.append(
        "🎬 " + title
    )

    if year:
        lines.append(
            "📅 " + year
        )

    if rating:
        lines.append(
            "⭐ " + rating + " / 10"
        )

    lines.append("")

    lines.append(
        "🍿 اكتشف تفاصيل الفيلم على MOVINS"
    )

    lines.append(
        site_url
    )

    lines.append("")

    lines.append(
        "#MOVINS #Movies #Film #Series"
    )

    return "\n".join(
        lines
    )


def movie_type_prefix(movie):

    value = (
        movie.get("type")
        or movie.get("detailed_type")
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
# SAVE POSTED MOVIE
# =========================================================

def save_posted_movie(
    posted,
    movie,
    facebook_result
):

    movie_id = get_movie_id(
        movie
    )

    entry = {
        "id": movie_id,
        "tmdb_id": movie_id,
        "title": get_movie_title(
            movie
        ),
        "year": get_movie_year(
            movie
        ),
        "type": get_movie_type(
            movie
        ),
        "rating": get_movie_rating(
            movie
        ),
        "facebook_result":
            facebook_result,
        "posted_at":
            int(time.time())
    }

    posted.append(
        entry
    )

    save_json(
        POSTED_FILE,
        posted
    )

    log(
        "Reel history saved."
    )


# =========================================================
# MAIN
# =========================================================

def main():

    log("")
    log("======================================")
    log("MOVINS — CINEMATIC REEL PUBLISHER")
    log("======================================")

    clean_work_directory()

    movies = load_movies()

    posted = load_posted()

    posted_ids = get_posted_ids(
        posted
    )

    log(
        "Movies available: "
        + str(len(movies))
    )

    log(
        "Already posted Reels: "
        + str(len(posted_ids))
    )

    movie = choose_movie(
        movies,
        posted_ids
    )

    if not movie:

        log(
            "No eligible movie found."
        )

        return

    movie_id = get_movie_id(
        movie
    )

    title = get_movie_title(
        movie
    )

    log("")
    log(
        "Selected movie: "
        + title
    )

    log(
        "TMDB ID: "
        + str(movie_id)
    )

    # -----------------------------------------------------
    # POSTER
    # -----------------------------------------------------

    download_poster(
        movie
    )

    # -----------------------------------------------------
    # ARABIC TEXT
    # -----------------------------------------------------

    create_text_card(
        movie
    )

    # -----------------------------------------------------
    # ORIGINAL MUSIC
    # -----------------------------------------------------

    create_original_music()

    # -----------------------------------------------------
    # VIDEO
    # -----------------------------------------------------

    create_video()

    # -----------------------------------------------------
    # FACEBOOK
    # -----------------------------------------------------

    page_id, page_name = (
        get_page_info()
    )

    caption = build_caption(
        movie
    )

    log("")
    log(
        "Caption:"
    )
    log(
        caption
    )

    facebook_result = publish_reel(
        page_id,
        movie,
        caption
    )

    # -----------------------------------------------------
    # SAVE ONLY AFTER SUCCESS
    # -----------------------------------------------------

    save_posted_movie(
        posted,
        movie,
        facebook_result
    )

    log("")
    log("======================================")
    log("MOVINS REEL SUCCESS")
    log("======================================")


if __name__ == "__main__":
    main()
